from math import ceil

from app.utils.elastic import BaseQueryBuilder
from pydantic import BaseModel

from app.utils.base import dictify


class Page(object):
    def __init__(self, items, total, page, per_page):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.total_pages = ceil(float(total) / per_page)


class Pagination(object):
    class PydanticModel(BaseModel):
        total: int
        per_page: int
        page: int
        total_pages: int

    def __init__(self, query, per_page=15, page=1):
        self.query = query
        self.per_page = per_page
        self.page = max(page, 1)
        self.offset = (self.page - 1) * self.per_page

    def paginate(self):

        if isinstance(self.query, BaseQueryBuilder):
            self.query.limit(self.per_page).offset(self.offset)
            items = self.query.results.rows_source
            count = self.query.results.count()
        else:
            items = self.query.limit(self.per_page).offset(self.offset)
            count = self.query.count()

        return Page(
            items=items,
            total=count,
            per_page=self.per_page,
            page=self.page
        )


class PaginationParams(object):
    def __init__(self, per_page=15, page=1):
        self.per_page = per_page
        self.page = page


class ApiList(object):
    query = None

    def __init__(self, query=None, page=1, per_page=15, pagination_params=None):
        print(pagination_params.page)
        self.query = query or self.query
        if pagination_params:
            self.page = pagination_params.page
            self.per_page = pagination_params.per_page
        else:
            self.page = page
            self.per_page = per_page

    def paginate(self):
        return Pagination(
            query=self.query,
            page=self.page,
            per_page=self.per_page
        ).paginate()

    def transform_rows(self, rows):
        return rows

    def to_dict(self):
        page = self.paginate()

        rows = self.transform_rows(page.items)

        return {
            "rows": [dictify(row) for row in rows],
            "pagination": {
                "total": page.total,
                "per_page": page.per_page,
                "page": page.page,
                "total_pages": page.total_pages
            }
        }
