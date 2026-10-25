# japyd

> *JSON:API, Pydantically simple.*

[![Tests](https://github.com/gdoumenc/japyd/actions/workflows/tests.yml/badge.svg)](https://github.com/gdoumenc/japyd/actions/workflows/tests.yml)
[![Codecov](https://codecov.io/gh/gdoumenc/japyd/branch/main/graph/badge.svg)](https://codecov.io/gh/gdoumenc/japyd)
[![PyPI](https://img.shields.io/pypi/v/japyd)](https://pypi.org/project/japyd/)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/gdoumenc/japyd/refs/heads/main/pyproject.toml)](https://pypi.org/project/japyd/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**japyd** turns your Pydantic models into a [JSON:API](https://jsonapi.org/) server with Flask.
Write plain models, return them from your views, and get relationships, included resources, filtering, sorting,
sparse fieldsets, pagination and standard errors for free.

```http
GET /books?filter=and(greaterThan(published,'1950-01-01'),equals(author.name,'Frank Herbert'))&sort=-price&include=author
```

One line in your view handles that query. You don't write a serializer, a schema or a filter parser.

## Why japyd

- **Your Pydantic models are the API.** A field holding another model becomes a relationship, everything else is an
  attribute.
- **A real query language.** Filters use the [JsonApiDotNetCore](https://www.jsonapi.net/usage/reading/filtering.html)
  syntax: `and`, `or`, `not`, `has`, comparisons, string matching, dotted paths through relationships and JSON fields.
- **Spec compliant by default.** `include`, `fields`, `sort`, `page`, `meta.count` and JSON:API error documents.
- **Small and typed.** Four modules on top of Flask and Pydantic 2, fully type hinted.

## Quick start

```bash
pip install japyd
```

Save this as `app.py`:

```python
from datetime import date
from typing import ClassVar

from flask import Flask
from flask_pydantic import validate

from japyd import JsonApiApp, JsonApiBaseModel, JsonApiQueryModel


class Author(JsonApiBaseModel):
    jsonapi_type: ClassVar[str] = "author"
    id: str
    name: str


class Book(JsonApiBaseModel):
    jsonapi_type: ClassVar[str] = "book"
    id: str
    title: str
    published: date
    price: float
    author: Author  # a model field becomes a relationship


tolkien = Author(id="1", name="J.R.R. Tolkien")
herbert = Author(id="2", name="Frank Herbert")
BOOKS = [
    Book(id="1", title="The Hobbit", published=date(1937, 9, 21), price=9.5, author=tolkien),
    Book(id="2", title="The Lord of the Rings", published=date(1954, 7, 29), price=25.0, author=tolkien),
    Book(id="3", title="Dune", published=date(1965, 8, 1), price=12.0, author=herbert),
]

app = Flask(__name__)
JsonApiApp(app)  # JSON:API errors and content type


@app.get("/books")
@validate(exclude_none=True)
def list_books(query: JsonApiQueryModel):
    return query.paginate(query.select(BOOKS))  # filter, sort, paginate


@app.get("/books/<book_id>")
@validate(exclude_none=True)
def get_book(book_id: str, query: JsonApiQueryModel):
    return query.one_or_none(next((b for b in BOOKS if b.id == book_id), None))
```

Run it:

```bash
flask --app app run
curl "http://localhost:5000/books/1?include=author"
```

```json
{
  "data": {
    "type": "book",
    "id": "1",
    "attributes": { "title": "The Hobbit", "published": "1937-09-21", "price": 9.5 },
    "relationships": { "author": { "data": { "type": "author", "id": "1" } } }
  },
  "meta": { "count": 1 },
  "included": [
    { "type": "author", "id": "1", "attributes": { "name": "J.R.R. Tolkien" } }
  ]
}
```

### Now play with it

All of these work against the app above:

| Try | What you get |
| --- | --- |
| `/books?filter=greaterThan(published,'1950-01-01')` | books published after 1950, the date string is converted to a `date` |
| `/books?filter=equals(author.name,'Frank Herbert')` | filtering through a relationship |
| `/books?filter=or(startsWith(title,'The'),lessThan(price,10))` | logical composition |
| `/books?sort=-price` | most expensive first |
| `/books?fields[book]=title,price` | only these attributes |
| `/books?page[size]=2` | first page of 2, with `has_next` and the total `count` in `meta` |
| `/books?flatten=author` | the author merged into the book attributes (japyd extension) |
| `/books?filter=equals(titl,'Dune')` | `400` JSON:API error: `Unknown attribute titl` |
| `/books?filter=equals(title,Dune` | `422` JSON:API error: wrong filter syntax |

## Guide

### Models

Subclass `JsonApiBaseModel`, set the `jsonapi_type` and an `id` field:

```python
from typing import Annotated, ClassVar

from japyd import JsonApiBaseModel, ResourceIdentifier


class Order(JsonApiBaseModel):
    jsonapi_type: ClassVar[str] = "order"

    id: str
    status: str                                          # attribute
    data: dict                                           # attribute, filterable by key: equals(data.channel,'web')
    customer: Customer                                   # to-one relationship
    lines: list[Line]                                    # to-many relationship
    tenant: Tenant | ResourceIdentifier | None = None    # relationship, the resource may be not loaded
    items: Annotated[list[Item], "as_attribute"]         # kept as an attribute
```

- A related resource is put in `included` only when requested: `?include=customer,lines.product`.
- Override the `links` property to add resource links, or `jsonapi_id` to compute the id.

### Responses

`JsonApiQueryModel` is parsed from the query string by
[Flask-Pydantic](https://github.com/pallets-eco/flask-pydantic) and builds the response:

| Method | Returns |
| --- | --- |
| `query.one(model)` | a single resource, `404` if `None` |
| `query.one_or_none(model)` | a single resource or `data: null` |
| `query.paginate(models)` | a page of resources with pagination metadata |
| `query.select(models)` | the models matching the filters, sorted |
| `query.match(model)` / `query.sort_values(models)` | filtering or sorting only |
| `query.no_content()` | an empty `204` response |

When the database already paginates, give the page and the total count:

```python
rows = db.fetch(limit=query.pagination.size, offset=(query.pagination.number - 1) * query.pagination.size)
return query.paginate(rows, full_list=False, total=db.count())
```

### Query parameters

| Parameter | Example | |
| --- | --- | --- |
| `include` | `include=author,comments.user` | related resources to add in `included` |
| `fields` | `fields[book]=title,price` | sparse fieldsets, per type |
| `filter` | `filter=equals(status,'open')` | see [Filtering](#filtering), several `filter` are combined with `and` |
| `sort` | `sort=-published,title` | `-` for descending, null values first |
| `page` | `page[number]=2&page[size]=10` | default size 20, values must be at least 1 |
| `flatten` | `flatten=author,lines.product\|page?` | japyd extension: merges relationships in the attributes |

With `flatten`, the flattened relationships are included automatically and removed from `included`, as they are
already in the attributes. `|` flattens several relationships at the same level, `?` makes one optional.

### Filtering

| Operator | Example | Meaning |
| --- | --- | --- |
| `equals` | `equals(status,'open')`, `equals(comment,null)` | equality, `null` for a missing value |
| `lessThan`, `lessOrEqual`, `greaterThan`, `greaterOrEqual` | `greaterThan(price,10)` | ordering |
| `contains`, `startsWith`, `endsWith` | `startsWith(name,'Bri')` | string matching |
| `containsIgnoreCase`, `startsWithIgnoreCase`, `endsWithIgnoreCase` | `containsIgnoreCase(name,'bri')` | case insensitive (japyd extension) |
| `any` | `any(status,'open','closed')` | value is one of the list |
| `has` | `has(lines)`, `has(lines,greaterThan(quantity,5))` | to-many relationship is not empty, or has a matching item |
| `not`, `and`, `or` | `or(equals(a,1),not(equals(b,2)))` | logical composition, `and` / `or` take 2 or more filters |

Values:

- strings are quoted with `'`, a quote inside is doubled: `'O''Connor'`
- numbers (`12`, `-1.5`, `1e5`), `true`, `false` and `null` are unquoted
- an unquoted name is another attribute: `lessThan(quantity,stock)`
- a quoted value is converted to the attribute type for equality, `any` and ordering operators:
  `greaterThan(created,'2024-01-01')` on a date, `equals(price,'12.50')` on a `Decimal`

Attributes:

- a dotted path follows to-one relationships and dict (JSON) attributes: `equals(customer.country,'FR')`,
  `equals(tenant_data.gmp+,true)` (in a URL, `+` must be encoded as `%2B`)
- to-many relationships are filtered with `has`
- as in SQL, `null` never matches an ordering or string operator

Errors: a syntax error returns `422`, an unknown attribute or incompatible types return `400`
(`FilterError` when calling `model.match` directly). Filters are limited to 32 nested operators.

Not supported yet: `count()`, `isType()` and filter scoping on relationships (`filter[lines]=...`).

### Request bodies

```python
from japyd import SingleBodyModel


@app.post("/authors")
@validate(exclude_none=True)
def create_author(body: SingleBodyModel, query: JsonApiQueryModel):
    author = Author.from_resource(body.data)  # validates the attributes, 409 Conflict on a wrong type
    author.id = save(author)
    return query.one(author), 201
```

`SingleBodyModel` and `MultiBodyModel` parse JSON:API request documents. A resource without `id` (creation) has
`id == ""` and may use `lid`. `body.attributes` gives the attributes directly.

### Errors

`JsonApiApp(app)` turns every exception into a JSON:API error document:

```json
{ "errors": [{ "id": "404", "status": "404", "title": "Not Found", "detail": "..." }] }
```

- HTTP exceptions keep their status, title and description.
- A `ResourceTypeError` (a body resource of the wrong type in `from_resource`) returns `409 Conflict`.
- Unhandled exceptions are logged and returned as a generic `500`. Their type and message are exposed only in debug mode
  or with `app.config["JSONAPI_EXPOSE_ERRORS"] = True`.
- An application handler registered on `Exception` before `JsonApiApp` is still called, and its response is wrapped.
- The response content type is `application/vnd.api+json` when the client accepts it.

Return your own error with `TopLevel.error(code=409, title="Conflict", detail="Already exists")`.

### Reading JSON:API documents

japyd also reads JSON:API documents, from a test client, another service or the bundled client:

```python
from japyd import JapydClient, TopLevel, extract_relationship, flatten_resource

top = TopLevel.model_validate(client.get("/books/3?include=author").json)

flatten_resource(top, pattern="author")
# {'type': 'book', 'id': '3', 'title': 'Dune', 'published': '1965-08-01', 'price': 12.0,
#  'author': {'type': 'author', 'id': '2', 'name': 'Frank Herbert'}}

extract_relationship(top, "author").attributes
# {'name': 'Frank Herbert'}

books = JapydClient("http://localhost:5000")("get", "/books", params={"sort": "-price"})
```

Relationship paths can be nested (`lines.product`), and an empty to-one relationship (`"data": null`) gives `None`.

## Contributing

Contributions are welcome: issues, ideas, documentation and pull requests.
See [CONTRIBUTING.md](CONTRIBUTING.md), then:

```bash
pdm install -G dev
pdm run tests   # ruff + mypy + pytest
```

## License

MIT
