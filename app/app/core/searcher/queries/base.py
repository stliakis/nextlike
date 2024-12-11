from typing import Tuple, List


class BaseQuery(object):
    def get_vectors(self) -> List[Tuple[List[int], float]]:
        raise []

    def get_text_queries(self):
        return []

    def get_items(self):
        return []

    def get_filter_queries(self):
        return []
