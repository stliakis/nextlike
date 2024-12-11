import numpy as np
from redis.commands.search.query import Query
from redis.commands.search.field import TagField, VectorField, TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from app.core.indexers.indexer import Indexer
from app.core.indexers.stemmer.generic import stem
from app.core.indexers.types import IndexerResultItem
from app.resources.database import m
from app.resources.rdb import get_redis
from app.utils.base import chunks, clear, listify, query_per_chunk
from app.utils.logging import log


class RedisIndexer(Indexer):
    def __init__(self, db, collection, index_embeddings=True):
        super(RedisIndexer, self).__init__(db, collection)

        self.index_name = "collection_%s" % collection.id
        self.doc_name_prefix = "d:%s:" % collection.id
        self.index_embeddings = index_embeddings
        self.embeddings_calculator = collection.get_embeddings_calculator()

        self.client = get_redis()
        

    def normalize_field(self, field_name):
        return field_name.replace(" ", "_").replace("-", "_").replace(".", "_").lower()

    async def create_index(self):
        fields = (
            m.ItemsField.objects(self.db)
            .filter(m.ItemsField.collection_id == self.collection.id)
            .all()
        )

        index_fields = [
            TextField("description", no_stem=True),
            TagField("_external_id"),
        ]

        vectors_size = (
            self.embeddings_calculator.get_size() if self.embeddings_calculator else 0
        )
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

    async def drop_index(self):
        try:
            await self.client.ft(self.index_name).dropindex()
        except:
            pass

    async def recreate(self):
        log(
            "info",
            "RedisIndexer[Recreating index for collection %s]" % self.collection.name,
        )
        await self.drop_index()
        await self.create_index()
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

        collection_prefixes = tuple(
            ["d:%s:" % collection.id for collection in redis_indexer_collections]
        )

        cursor = 0
        keys_to_delete = set()
        keys_to_update = set()
        while True:
            cursor, partial_keys = await client.scan(
                cursor=cursor, match=f"d:*", count=500
            )

            # pipe = client.pipeline()
            # for key in partial_keys:
            #     pipe.hget(key, "_hash")
            #
            # result = await pipe.execute()
            # redis_hashes = {key.decode("utf-8"): value for key, value in zip(partial_keys, result)}
            #
            # item_ids = [int(key.split(":")[-1]) for key in redis_hashes.keys()]
            #
            # db_hashes = {
            #     item.id: item.get_hash()
            #     for item in m.Item.objects(db)
            #     .filter(m.Item.id.in_(item_ids))
            #     .all()
            # }
            #
            # for item_id, redis_hash in redis_hashes.items():
            #     redis_item_id = int(item_id.split(":")[-1])
            #
            #     print("redis_item_id", redis_item_id, db_hashes.get(redis_item_id))
            #
            #     db_hash = db_hashes.get(int(item_id.split(":")[-1]))
            #     if db_hash != redis_hash:
            #         keys_to_update.add(item_id)
            #
            # print("hashes", len(keys_to_update))

            for key in partial_keys:
                key = key.decode("utf-8")
                if not key.startswith(collection_prefixes):
                    keys_to_delete.add(key)

            if cursor == 0:
                break

        # if keys_to_update:
        #     await self.index_items()

        if keys_to_delete:
            log(
                "info",
                f"RedisIndexer[Deleting {len(keys_to_delete)} gone collection items from redis]",
            )
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
        log(
            "info",
            "RedisIndexer[redis count: %s, db count: %s]"
            % (len(existing_redis_item_ids), len(existing_db_item_ids)),
        )

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
            items = (
                m.Item.objects(self.db)
                .filter(
                    m.Item.id.in_([int(key.split(":")[-1]) for key in keys_to_index])
                )
                .all()
            )

            await self.index_items(items)

    async def index_items(self, items=None):
        async def index(chunk_of_items):
            vectors_size = (
                self.embeddings_calculator.get_size()
                if self.embeddings_calculator
                else 0
            )

            pipe = self.client.pipeline()

            indexed_count = 0

            stemmer = self.collection.config.stemmer

            for i, item in enumerate(chunk_of_items):

                stemmed_description = stem(stemmer, item.description)

                # log("info", f"RedisIndexer[stemmed_description: {item.description}->{stemmed_description}]")

                mapping = {
                    "description": "%s - %s" % (stemmed_description, item.description),
                    "_hash": item.get_hash(),
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
                        value = ",".join(map(str, value))

                    if isinstance(value, bool):
                        if value:
                            value = 1
                        else:
                            value = 0

                    mapping[self.normalize_field(name)] = str(value)

                indexed_count += 1
                pipe.hset(f"{self.doc_name_prefix}{item.id}", mapping=mapping)

            log(
                "info",
                "RedisIndexer[Indexed %s items of collection %s]"
                % (indexed_count, self.collection.name),
            )

            await pipe.execute()

        if not items:
            query = query_per_chunk(
                m.Item.objects(self.db).filter(
                    m.Item.collection_id == self.collection.id
                ),
                500,
            )
            for chunk in query:
                await index(chunk)
        else:
            await index(items)

    async def search(
        self,
        filters=None,
        text_search_query=None,
        text_search_similarity_function="BM25",
        score_threshold=0,
        vector=None,
        limit=10,
        offset=0,
        exclude_external_ids=None,
        raw_query=None,
    ):
        filters_query = []

        if not raw_query:

            if filters:
                filters_query.append(
                    self.convert_filters_to_redisearch_filters(filters)
                )

            if text_search_query:
                text_search_query = stem(
                    self.collection.config.stemmer, text_search_query
                )

                log(
                    "info",
                    f"RedisIndexer[searching with text_search_query: {text_search_query}]",
                )

                all_filter_queries = []

                fuzzy_search = True

                all_queries = []
                if " " in text_search_query:
                    words = text_search_query.split()
                    fuzzy_words = []

                    for word in words:
                        if len(word) <= 4:
                            fuzzy_distance = 0
                        elif len(word) <= 8:
                            fuzzy_distance = 1
                        else:
                            fuzzy_distance = 2

                        fuzzy_word = (
                            f"{'%' * fuzzy_distance}{word}{'%' * fuzzy_distance}"
                        )
                        fuzzy_words.append(fuzzy_word)

                    word_prefixes = [f"{word}*" for word in words]

                    all_queries.extend(
                        [
                            (f"@description:({' '.join(fuzzy_words)})~2", 1),
                            (f"@description:({text_search_query})", 5),
                            (f"@description:({' '.join(word_prefixes)})", 0.1),
                        ]
                    )

                else:
                    if len(text_search_query) <= 4:
                        fuzzy_distance = 0
                    elif len(text_search_query) <= 7:
                        fuzzy_distance = 1
                    else:
                        fuzzy_distance = 2

                    all_queries.extend(
                        [
                            (
                                f"@description:{'%' * fuzzy_distance}{text_search_query}{'%' * fuzzy_distance}",
                                1,
                            ),
                            (f"@description:({text_search_query})", 5),
                            (f"@description:{text_search_query}*", 0.1),
                        ]
                    )

                for query, weight in all_queries:
                    all_filter_queries.append(
                        "((%s) => { $weight: %s })" % (query, weight)
                    )

                filters_query.append("(%s)" % " | ".join(all_filter_queries))

            if exclude_external_ids:
                exclude_query = " ".join(
                    [
                        f"-@_external_id:{external_id}"
                        for external_id in exclude_external_ids
                    ]
                )
                filters_query.append(exclude_query)

            if not filters_query:
                filters_query = ["*"]

            if not text_search_similarity_function:
                text_search_similarity_function = "BM25"
        else:
            filters_query = [raw_query]

        full_query_string = """({filters_query}){vector_search}""".format(
            filters_query=" ".join(filters_query),
            score_function=text_search_similarity_function,
            vector_search=(
                f"=>[KNN {limit} @embedding $vec as vector_score]" if vector else ""
            ),
        )

        log(
            "info",
            f"RedisIndexer[index={self.index_name}, searching with query: ({full_query_string}), {vector} ]",
        )

        if vector:
            query = (
                Query(raw_query or full_query_string)
                .return_field("vector_score")
                .return_field("description")
                .scorer(text_search_similarity_function)
                .sort_by("vector_score")
                .with_scores()
                .dialect(4)
                .paging(offset, limit)
            )
        else:
            query = (
                Query(raw_query or full_query_string)
                .return_field("description")
                .scorer(text_search_similarity_function)
                .with_scores()
                .dialect(4)
                .paging(offset, limit)
            )

        results = await self.client.ft(self.index_name).search(
            query,
            query_params=clear(
                {
                    "vec": (
                        np.array(vector, dtype=np.float32).tobytes() if vector else None
                    )
                }
            ),
        )

        log("info", f"RedisIndexer[search results: {results}]")

        items = []
        for doc in results.docs:
            if vector:
                similarity = 1 - float(doc.vector_score)
            else:
                similarity = doc.score

            if score_threshold is not None and similarity < score_threshold:
                continue

            items.append(
                IndexerResultItem(
                    id=doc.id.split(":")[-1],
                    similarity=similarity,
                    description=doc.description,
                )
            )

        return items

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
