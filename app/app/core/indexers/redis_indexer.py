import numpy as np
from redis.commands.search.query import Query
from redis.commands.search.field import TagField, VectorField, TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

from app.core.indexers.indexer import Indexer
from app.core.indexers.types import IndexerResultItem
from app.resources.database import m
from app.resources.rdb import get_redis
from app.utils.base import chunks, clear, listify
from app.utils.logging import log


class RedisIndexer(Indexer):
    def __init__(self, db, collection, index_embeddings=True):
        super(RedisIndexer, self).__init__(db, collection)

        self.index_name = "collection_%s" % collection.id
        self.doc_name_prefix = "d:%s:" % collection.id
        self.index_embeddings = index_embeddings

        self.client = get_redis()

    def normalize_field(self, field_name):
        return field_name.replace(" ", "_").replace("-", "_").replace(".", "_").lower()

    def get_vectors_size(self):
        if not self.index_embeddings:
            return 0

        if self.collection.default_embeddings_model == "text-embedding-3-large":
            return 3072
        elif self.collection.default_embeddings_model == "text-embedding-3-small":
            return 1536
        else:
            return 0

    async def recreate_index(self):
        try:
            await self.client.ft(self.index_name).dropindex()
        except:
            pass

        fields = (
            m.ItemsField.objects(self.db)
            .filter(m.ItemsField.collection_id == self.collection.id)
            .all()
        )

        index_fields = [
            TextField("description"),
            TagField("_external_id"),
        ]

        vectors_size = self.get_vectors_size()
        if vectors_size:
            index_fields.append(
                VectorField(
                    "embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": vectors_size,
                        "DISTANCE_METRIC": "COSINE",
                    },
                )
            )

        for field in fields:
            if field.field_name.startswith("_"):
                continue

            if field.type == "string":
                index_fields.append(
                    TagField(self.normalize_field(field.field_name), separator=",")
                )
            elif field.type == "number":
                index_fields.append(
                    NumericField(self.normalize_field(field.field_name))
                )

        await self.client.ft(self.index_name).create_index(
            index_fields, definition=IndexDefinition(prefix=[self.doc_name_prefix])
        )

    async def recreate(self):
        await self.recreate_index()
        await self.index_items()

    async def index_exists(self):
        try:
            await self.client.ft(self.index_name).info()
            return True
        except Exception as e:
            return False

    @classmethod
    async def cleanup_all(cls, db):
        client = get_redis()

        existing_collections = m.Collection.objects(db).filter().all()
        redis_indexer_collections = [
            collection
            for collection in existing_collections
            if collection.config.indexer == "redis"
        ]

        collection_prefixes = tuple(["d:%s:" % collection.id for collection in redis_indexer_collections])

        cursor = 0
        keys_to_delete = set()
        while True:
            cursor, partial_keys = await client.scan(
                cursor=cursor, match=f"d:*", count=500
            )
            for key in partial_keys:
                key = key.decode("utf-8")
                if not key.startswith(collection_prefixes):
                    keys_to_delete.add(key)

            if cursor == 0:
                break

        if keys_to_delete:
            log("info", f"RedisIndexer[Deleting {len(keys_to_delete)} gone collection items from redis]")
            for chunk in chunks(list(keys_to_delete), 100):
                await client.delete(*chunk)
        else:
            log("info", "RedisIndexer[No collection items to delete from redis]")

    async def cleanup(self):
        if not await self.index_exists():
            await self.recreate()
            return

        existing_db_item_ids = [
            item.id
            for item in m.Item.objects(self.db)
            .select(m.Item.id)
            .filter(m.Item.collection_id == self.collection.id)
            .all()
        ]

        existing_db_item_ids = set(
            [f"{self.doc_name_prefix}{item_id}" for item_id in existing_db_item_ids]
        )

        cursor = 0

        existing_redis_item_ids = set()

        while True:
            cursor, partial_keys = await self.client.scan(
                cursor=cursor, match=f"{self.doc_name_prefix}*", count=100
            )
            for key in partial_keys:
                existing_redis_item_ids.add(key.decode("utf-8"))

            if cursor == 0:
                break

        keys_to_delete = existing_redis_item_ids - existing_db_item_ids
        keys_to_index = existing_db_item_ids - existing_redis_item_ids
        log("info",
            "RedisIndexer[redis count: %s, db count: %s]" % (len(existing_redis_item_ids), len(existing_db_item_ids)))

        log(
            "info",
            "RedisIndexer[Deleting %s gone items from redis]" % len(keys_to_delete),
        )
        log(
            "info",
            "RedisIndexer[Indexing %s missing items to redis]" % len(keys_to_index),
        )

        for chunk in chunks(list(keys_to_delete), 100):
            await self.client.delete(*chunk)

        if keys_to_index:
            await self.index_items(
                item_ids=[int(key.split(":")[-1]) for key in keys_to_index]
            )

    async def index_items(self, item_ids=None):
        if not item_ids:
            item_ids = [
                item.id
                for item in m.Item.objects(self.db)
                .select(m.Item.id)
                .filter(m.Item.collection_id == self.collection.id)
                .all()
            ]

        items_query = m.Item.objects(self.db).filter(
            m.Item.collection_id == self.collection.id
        )

        for ids in chunks(item_ids, 5000):
            items = items_query.filter(m.Item.id.in_(ids)).all()

            vectors_size = self.get_vectors_size()

            pipe = self.client.pipeline()

            indexed_count = 0
            for i, item in enumerate(items):
                mapping = {
                    "description": item.description,
                    "_external_id": item.external_id,
                }

                if vectors_size:
                    vector = getattr(item, "vectors_%s" % vectors_size, None)

                    if vector is not None:
                        mapping["embedding"] = np.array(
                            list(vector), dtype=np.float32
                        ).tobytes()
                    else:
                        mapping["embedding"] = np.zeros(
                            vectors_size, dtype=np.float32
                        ).tobytes()

                for name, value in item.fields.items():
                    if name.startswith("_"):
                        continue

                    if isinstance(value, list):
                        value = ",".join(str(value))

                    if isinstance(value, bool):
                        if value:
                            value = 1
                        else:
                            value = 0

                    mapping[self.normalize_field(name)] = value

                indexed_count += 1
                pipe.hset(f"{self.doc_name_prefix}{item.id}", mapping=mapping)

            log(
                "info",
                "RedisIndexer[Indexed %s items of collection %s]"
                % (indexed_count, self.collection.name),
            )

            await pipe.execute()

    async def search(
            self,
            filters=None,
            text_search_query=None,
            text_search_similarity_function=None,
            vector=None,
            limit=10,
            offset=0,
            exclude_external_ids=None,
            raw_query=None,
    ):
        filters_query = ""

        if not raw_query:

            if filters:
                filters_query += " " + self.convert_filters_to_redisearch_filters(
                    filters
                )

            if text_search_query:
                text_search_query = f"""(@description:"{text_search_query}")"""
                filters_query += " " + text_search_query

            if exclude_external_ids:
                exclude_query = " ".join(
                    [
                        f"-@_external_id:{external_id}"
                        for external_id in exclude_external_ids
                    ]
                )
                filters_query += " " + exclude_query

            if not filters_query:
                filters_query = "*"

            if not text_search_similarity_function:
                text_search_similarity_function = "TFIDF.DOCNORM"
        else:
            filters_query = raw_query

        full_query_string = """({filters_query}){vector_search}""".format(
            filters_query=filters_query,
            score_function=text_search_similarity_function,
            vector_search="=>[KNN 3 @embedding $vec as vector_score]" if vector else "",
        )

        log("info", f"RedisIndexer[searching with query: {full_query_string}]")

        if vector:
            query = (
                Query(raw_query or full_query_string)
                .return_field("vector_score")
                .return_field("description")
                .scorer(text_search_similarity_function)
                .sort_by("vector_score")
                .with_scores()
                .dialect(2)
                .paging(offset, limit)
            )

        else:
            query = (
                Query(raw_query or full_query_string)
                .return_field("description")
                .scorer(text_search_similarity_function)
                .with_scores()
                .dialect(2)
                .paging(offset, limit)
            )

        results = await self.client.ft(self.index_name).search(
            query,
            query_params=clear(
                {
                    "vec": np.array(vector, dtype=np.float32).tobytes()
                    if vector
                    else None
                }
            ),
        )

        log("info", f"RedisIndexer[search results: {results}]")

        return [
            IndexerResultItem(
                id=result.id.split(":")[-1],
                similarity=(1 - float(result.vector_score)) if vector else result.score,
                description=result.description,
            )
            for result in results.docs
        ]

    def convert_filters_to_redisearch_filters(self, filters):
        return self._build_query(filters)

    def _build_query(self, filters):
        if isinstance(filters, dict):
            conditions = []
            for key, value in filters.items():
                if key in ["$and", "and"]:
                    sub_conditions = [
                        self._build_query(sub_filter) for sub_filter in value
                    ]
                    conditions.append("({})".format(" ".join(sub_conditions)))
                elif key in ["$or", "or"]:
                    sub_conditions = [
                        self._build_query(sub_filter) for sub_filter in value
                    ]
                    conditions.append("({})".format(" | ".join(sub_conditions)))
                elif key in ["$not", "not"]:
                    sub_condition = self._build_query(value)
                    conditions.append("-({})".format(sub_condition))
                else:
                    # Key is a field name
                    field_query = self._build_field_query(key, value)
                    conditions.append(field_query)
            return " ".join(filter(None, conditions))
        else:
            return ""

    def _build_field_query(self, field, value):
        field = self.normalize_field(field)

        if isinstance(value, dict):
            if "gte" in value or "lte" in value:
                min_value = value.get("gte", "-inf")
                max_value = value.get("lte", "+inf")
                query = f"@{field}:[{min_value} {max_value}]"
                return query
            elif "eq" in value:
                eq_value = value["eq"]
                query = f"@{field}:[{eq_value} {eq_value}]"
                return query
            elif "contains" in value:
                contains_value = value["contains"]
                query = "@%s:{%s}" % (field, "|".join(listify(contains_value)))
                return query
            elif "in" in value:
                in_values = value["in"]
                sub_queries = [f"@{field}:{val}" for val in in_values]
                return f"({'|'.join(sub_queries)})"
            else:
                return ""
        else:
            query = "@%s:{%s}" % (field, value)
            return query
