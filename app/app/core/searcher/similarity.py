import re

from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Union, Tuple, Dict
from app.models import Item, Collection
from app.core.searcher.clauses.base import get_vectors_from_ofs, get_queries_from_ofs
from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.core.types import SearchResult, SearchConfig, SortingModifier, SearchItem
from app.resources.database import m
from app.utils.base import get_fields_hash
from app.utils.json_filter_query import build_query_string_and_params
from app.utils.logging import log


class SimilarityEngine(object):
    def __init__(self, db: Session, collection: Collection, embeddings_calculator=None):
        self.collection = collection
        self.db = db
        self.embeddings_calculator = embeddings_calculator or OpenAiEmbeddingsCalculator(
            model=collection.default_embeddings_model)

    def filter_out_ingested_items(
            self, items: List[Item]
    ) -> List[Item]:
        hashes_in_db = [item.description_hash for item in items]

        changed_items = []
        for item in items:
            if item.get_hash() not in hashes_in_db:
                changed_items.append(item)

        return changed_items

    def get_average_vector_of_vectors(self, vectors):
        return [
            sum([vector[i] for vector in vectors]) / len(vectors)
            for i in range(len(vectors[0]))
        ]

    def get_weighted_vectors(self, query_vectors: List[Tuple[List[int], float]]):
        weighted_vectors = []
        for vector, weight in query_vectors:
            weighted_vectors.append([i * weight for i in vector])

        return weighted_vectors

    def search(self, config: SearchConfig, exclude: List[str], context: dict) -> List[SearchItem]:
        if not config.similar:
            return []

        vectors: List[Tuple[List[int], float]] = []
        vectors.extend(get_vectors_from_ofs(self.db, self, config.similar.of, context))

        queries: List[Tuple[str, float]] = []
        queries.extend(get_queries_from_ofs(self.db, self, config.similar.of, context))

        if len(vectors) == 0 and len(queries) == 0:
            return []

        return self.get_similar(
            query_vectors=vectors,
            exclude_external_item_ids=exclude,
            queries=queries,
            limit=config.limit,
            offset=config.offset,
            sort=config.similar.sort,
            filters=config.filter,
            score_threshold=config.similar.score_threshold,
            distance_function=config.similar.distance_function,
            randomize=config.randomize,
            export=config.export,
            context=context
        )

    def sort_similar_items(self, similar_items, sort, limit, offset):
        if not similar_items:
            return []

        max_similarity = max(item.similarity for item in similar_items)
        min_similarity = min(item.similarity for item in similar_items)
        max_score = max(item.score for item in similar_items)
        min_score = min(item.score for item in similar_items)

        # Calculate ranges to avoid division by zero
        similarity_range = max_similarity - min_similarity if max_similarity != min_similarity else 1
        score_range = max_score - min_score if max_score != min_score else 1

        # Normalize similarity and score, then calculate final combined score
        for similar_item in similar_items:
            # Option 1: Min-Max Normalization with Cap
            normalized_similarity = (similar_item.similarity - min_similarity) / similarity_range
            normalized_similarity = min(normalized_similarity, 0.95)  # Cap to reduce the impact of outliers

            # Option 2: Logarithmic Normalization
            # normalized_similarity = math.log1p(similar_item.similarity - min_similarity) / math.log1p(similarity_range)

            normalized_score = (similar_item.score - min_score) / score_range

            # Combined score with normalized similarity and score weighted
            similar_item.score = (normalized_similarity * (1 - sort.weight) +
                                  normalized_score * sort.weight)

        # Sort by combined score in descending order and paginate
        sorted_items = sorted(similar_items, key=lambda x: x.score, reverse=True)
        paginated_items = sorted_items[offset:offset + limit]

        return paginated_items

    def get_similar(
            self,
            query_vectors: List[Tuple[List[int], float]] = None,
            exclude_external_item_ids: List[Union[int, str]] = None,
            queries: List[Tuple[str, float]] = None,
            limit: int = 10,
            offset: int = 0,
            filters: Union[dict, None] = None,
            sort: SortingModifier = None,
            score_threshold: float = None,
            distance_function: str = "cosine",
            randomize: bool = False,
            export: Union[str, List[str]] = None,
            context: dict = None
    ):
        if queries:
            distance_function = queries[0][2] or "trigram"

        all_where_clauses: List[str] = []
        all_where_params: Dict[str, any] = {}

        if filters:
            filters_query, filter_params = build_query_string_and_params("fields", filters)
            all_where_clauses.append(filters_query)
            all_where_params.update(filter_params)

        if exclude_external_item_ids:
            all_where_clauses.append("not item.external_id = any(:exclude_ids)")
            all_where_params.update({
                "exclude_ids": exclude_external_item_ids
            })

        all_where_clauses.append("item.collection_id = :collection_id")
        all_where_params.update({
            "collection_id": self.collection.id
        })

        query_params = {
            "limit": limit,
            "offset": offset,
            "score_threshold": score_threshold
        }

        if score_threshold:
            score_threshold_query = "similarity_table.similarity > :score_threshold"
            query_params["score_threshold"] = score_threshold
        else:
            score_threshold_query = None

        query_params.update(all_where_params)

        distance_query = None

        if distance_function in ["cosine", "inner_product", "l1", "l2"]:
            if not query_vectors:
                raise ValueError(f"No query vectors provided for vector {distance_function} similarity search")

            query_vectors = self.get_weighted_vectors(query_vectors)

            query_vector = self.get_average_vector_of_vectors(query_vectors)

            query_params.update({
                "vector": "[%s]" % (",".join(map(str, query_vector)))
            })

            if len(query_vector) == 1536:
                vector_field = "vectors_1536"
                all_where_clauses.append("item.vectors_1536 is not null")
            elif len(query_vector) == 3072:
                vector_field = "vectors_3072"
                all_where_clauses.append("item.vectors_3072 is not null")
            else:
                raise ValueError("Query vector must be of length 1536 or 3072")

            if distance_function == "cosine":
                distance_query = f"1 - (item.{vector_field} <=> :vector) as similarity"
            elif distance_function == "inner_product":
                distance_query = f"(item.{vector_field} <#> :vector) * -1 as similarity"
            elif distance_function == "l1":
                distance_query = f"(item.{vector_field} <+> :vector) as similarity"
            elif distance_function == "l2":
                distance_query = f"1 - (item.{vector_field} <-> :vector) as similarity"
        elif distance_function == "trigram":
            distance_query = "({all_query}) as similarity".format(
                all_query="+".join([
                    f"similarity(description, :query_{i})" for i in range(len(queries))
                ])
            )
            query_params.update({
                f"query_{i}": query for i, (query, _, _) in enumerate(queries)
            })
        else:
            if not queries:
                raise ValueError("No queries provided for trigram similarity")
            else:
                print(queries)

                weighted_components = []
                for i, (query, weight, component_distance_function) in enumerate(queries):
                    components = component_distance_function.split('+')

                    component_queries = []

                    for component in components:
                        if "trigram" in component:
                            # Handle trigram component with weight
                            trigram_query = f"similarity(description, :query_{i}) * {weight}"
                            component_queries.append(trigram_query)
                            query_params[f"query_{i}"] = query

                        elif "tsvector" in component:
                            # Identify the language inside the parentheses, e.g., 'tsvector(greek)'
                            language_match = re.search(r'tsvector\((\w+)\)', component)
                            if language_match:
                                language = language_match.group(1)
                                tsvector_query = (
                                    f"ts_rank_cd(to_tsvector('{language}', item.description), "
                                    f"to_tsquery('{language}', :query_{i})) * {weight}"
                                )
                                component_queries.append(tsvector_query)

                                query_tokens = query.strip().split(" ")
                                query_tokens = [i for i in query_tokens if i]

                                query_params[f"query_{i}"] = "|".join(query_tokens)

                    # Join component queries for this item using '+' operator
                    combined_component_query = " + ".join(component_queries)
                    weighted_components.append(f"({combined_component_query})")
                # Combine all queries across different `queries` entries
                distance_query = " + ".join(weighted_components)
                distance_query = f"({distance_query}) as similarity"

        if randomize:
            order_by = "random()"
        else:
            order_by = "similarity_table.similarity desc"

        if sort:
            pagination_query = "limit :topn"
            query_params["topn"] = sort.topn
        else:
            pagination_query = "limit :limit offset :offset"
            query_params["topn"] = limit
            query_params["offset"] = offset

        query = text("""
           select id,external_id,similarity,scores from (
               select item.id,item.external_id,item.fields,item.scores, {distance_query} from item {where_clauses}
               ) as similarity_table {score_threshold_query} order by {order_by} {pagination_query}
        """.format(
            where_clauses=f"where {' and '.join(all_where_clauses)}" if all_where_clauses else "",
            order_by=order_by,
            topn=sort.topn if sort else limit,
            distance_query=distance_query,
            pagination_query=pagination_query,
            score_threshold_query=f"where {score_threshold_query}" if score_threshold_query else "",
        )).params(query_params)

        log("info", "similarity items query: %s, %s" % (query, query_params))

        similar_items = self.db.execute(query).fetchall()

        similar_items = [SimilarItem(
            id=item.id,
            similarity=item.similarity,
            score=sort and item.scores.get(sort.score_name) or 0,
        ) for item in similar_items]

        if sort and similar_items:
            similar_items = self.sort_similar_items(
                similar_items,
                sort,
                limit,
                offset
            )

        items = Item.objects(self.db).filter(Item.id.in_([item.id for item in similar_items])).all()
        items_per_id = {item.id: item for item in items}

        recommendations = []
        for similar_item in similar_items:
            item = items_per_id[similar_item.id]

            if export is None:
                exported_value = item.fields
            else:
                if isinstance(export, str):
                    exported_value = item.fields.get(export)
                else:
                    exported_value = {
                        field: item.fields.get(field) for field in export
                    }

            recommendations.append(SearchItem(
                id=item.external_id,
                fields=item.fields,
                similarity=similar_item.similarity,
                score=similar_item.score,
                exported=exported_value
            ))

        return recommendations

    def get_query_vector_from_fields(self, fields) -> List[int]:
        description_hash = get_fields_hash(fields)
        matching_item = m.Item.objects(self.db).filter(m.Item.description_hash == description_hash).first()
        if matching_item:
            return matching_item.vector

        return self.embeddings_calculator.get_embeddings_from_fields(fields)

    def get_query_vector_from_prompt(self, prompt: str) -> List[int]:
        return self.embeddings_calculator.get_embeddings_from_string(prompt)

    def get_embeddings_of_items(self, items, skip_ingested=True):
        if skip_ingested:
            changed_items = self.filter_out_ingested_items(items)
        else:
            changed_items = items

        changed_item_embeddings = self.embeddings_calculator.get_embeddings_from_items(changed_items)

        unchanged_items = [item for item in items if item not in changed_items]

        all_embeddings = {}

        for item, vector in zip(changed_items, changed_item_embeddings):
            item.vector = vector
            all_embeddings[item.id] = vector

        for item in unchanged_items:
            all_embeddings[item.id] = item.vector

        return all_embeddings


class SimilarItem(object):
    def __init__(self, id, similarity, score=None):
        self.id = id
        self.similarity = similarity
        self.score = score
