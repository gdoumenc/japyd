---
name: japyd
description: Build or modify JSON:API endpoints with the japyd library (Flask + Pydantic 2, JsonApiDotNetCore filter syntax). Use when the code imports japyd, or when writing Flask views returning JSON:API documents with JsonApiBaseModel, JsonApiQueryModel, SingleBodyModel or TopLevel.
---

# japyd

japyd turns Pydantic models into JSON:API resources and parses the query parameters (`filter`, `sort`, `page`,
`fields`, `include`) with the JsonApiDotNetCore syntax. Full reference: the japyd README and `llms.txt`.

## Setup

```python
from typing import ClassVar

from flask import Flask, url_for
from flask_pydantic import validate

from japyd import JsonApiApp, JsonApiBaseModel, JsonApiQueryModel, SingleBodyModel

app = Flask(__name__)
JsonApiApp(app)  # JSON:API error documents and content type, register it once


class Author(JsonApiBaseModel):
    jsonapi_type: ClassVar[str] = "author"  # always a ClassVar
    id: str = ""
    name: str


class Book(JsonApiBaseModel):
    jsonapi_type: ClassVar[str] = "book"
    id: str
    title: str
    author: Author | None = None  # a model field is a relationship
```

## Choose the response

| Endpoint | Return | Status |
| --- | --- | --- |
| `GET /books` | `query.paginate(query.select(books))` | 200, `data: []` when empty |
| `GET /books/1` | `query.one(book)` | 200, 404 if `book` is `None` |
| `GET /books/1/author` (to-one) | `query.one_or_none(book.author)` | 200, `data: null` if `None` |
| `POST /books` | `query.created(book, location=url_for(...))` | 201 with `Location` |
| `PATCH`, `DELETE` without body | `query.no_content()` | 204 |
| Custom error | `TopLevel.error(code=409, title="Conflict", detail="...")` | the given code |

Never use `one_or_none` for a resource fetched by id: a missing resource is a 404. Never return 204 for a `GET`.

```python
@app.get("/books/<book_id>")
@validate(exclude_none=True)  # always exclude_none=True on japyd views
def get_book(book_id: str, query: JsonApiQueryModel):
    return query.one(db.get_book(book_id))


@app.post("/authors")
@validate(exclude_none=True)
def create_author(body: SingleBodyModel, query: JsonApiQueryModel):
    author = Author.from_resource(body.data)  # 409 Conflict on a wrong type
    author.id = db.save(author)
    return query.created(author, location=url_for("get_author", author_id=author.id))
```

When the database paginates, pass the page and the total: `query.paginate(rows, full_list=False, total=count)`,
with `query.pagination.number` and `query.pagination.size` (default 20) for the offset and limit.

## Models

- A field typed `Model`, `list[Model]` or `Model | ResourceIdentifier | None` is a relationship, even when `None`
  (`data: null` for a to-one, `data: []` for a to-many). Every other field is an attribute.
- Keep a model field as an attribute with `Annotated[list[Item], "as_attribute"]`.
- Override the `links` property for resource links (its `self` link is the default `Location` of `created`), and
  `jsonapi_id` to compute the id.
- Read a request body with `SingleBodyModel` / `MultiBodyModel`; a creation resource has `id == ""` and may have a
  `lid`. `Model.from_resource(resource)` validates the attributes.

## Query parameters

- `include=author,lines.product`: only relationship paths, anything else returns 400.
- `fields[book]=title,price`, `sort=-published,title`, `page[number]=2&page[size]=10`.
- `filter=and(greaterThan(published,'1950-01-01'),equals(author.name,'Frank Herbert'))`. Operators: `equals`,
  `lessThan`, `lessOrEqual`, `greaterThan`, `greaterOrEqual`, `contains`, `startsWith`, `endsWith`, the
  `...IgnoreCase` variants, `any(attr,'a','b')`, `has(to_many)`, `has(to_many,filter)`, `not`, `and`, `or`.
  Strings are quoted with `'` (doubled to escape), `null`, `true`, `false` and numbers are unquoted, an unquoted name
  is another attribute. Dotted paths follow to-one relationships and dict attributes; use `has` for to-many.
- `flattenPaths=author,lines.product|page?` (japyd extension, `query.flatten` in Python) merges relationships into
  the attributes. `flatten` is its deprecated name: do not use it in new code.
- `query.select(models)` filters and sorts in Python; with a database, translate `query.filters` instead.

## Errors

- Filter syntax errors return 422, an unknown attribute or an incompatible type returns 400.
  Outside a view, `model.match(...)` raises `FilterError`.
- Raise werkzeug exceptions (`NotFound`, `Conflict`...) in views: `JsonApiApp` turns them into error documents.
- Unhandled exceptions give a generic 500, detailed only with `app.debug` or `JSONAPI_EXPOSE_ERRORS = True`.
- Clients must send `Content-Type: application/vnd.api+json` without parameter (or only `profile`):
  `; charset=utf-8` or `; ext=...` returns 415, and an `Accept` with only such JSON:API media types returns 406.
- An error document never contains `data`: do not build a `TopLevel` with both resources and `errors`.

## Reading documents

`TopLevel.model_validate(json)`, `flatten_resource(top, pattern="author")` to get plain dicts,
`extract_relationship(top, "lines.product")` to get included resources, `JapydClient(url)("get", "/books")` as client.
A relationship can be `data: null` (empty to-one), `data: []` (empty to-many) or have only `links`: check
`relationship.has_data` before reading `relationship.data`, extracting it otherwise raises `AttributeError`.
