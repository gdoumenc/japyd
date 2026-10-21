# japyd

> *"JSON:API, Pydantically simple."*

Automate JSON:API relationships with Pydantic. No manual mapping, just clean code.

[![Tests](https://github.com/gdoumenc/japyd/actions/workflows/tests.yml/badge.svg)](https://github.com/gdoumenc/japyd/actions/workflows/tests.yml)
[![Codecov](https://codecov.io/gh/gdoumenc/japyd/branch/main/graph/badge.svg)](https://codecov.io/gh/gdoumenc/japyd)
[![PyPI](https://img.shields.io/pypi/v/japyd)](https://pypi.org/project/japyd/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/gdoumenc/japyd/refs/heads/main/pyproject.toml)](https://pypi.org/project/japyd/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/gdoumenc/japyd/graphs/commit-activity)
[![Open Source](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/gdoumenc/japyd)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**japyd** (JSON:API + PYDantic) is a Python library to build [JSON:API](https://jsonapi.org/) servers with Flask and
Pydantic: Pydantic models become JSON:API resources with relationships and included resources, and query parameters
(`filter`, `sort`, `page`, `fields`, `include`) are parsed with the [JsonApiDotNetCore](https://www.jsonapi.net/)
filter syntax.

## Installation

```bash
pip install japyd
```

Requires Python 3.11+, Flask and Pydantic 2.

## Japyd: Core Value Propositions

**Japyd** is a Python toolkit designed to simplify the interaction with JSON:API, a specification for building APIs in JSON.
It provides a set of utilities to facilitate the creation, manipulation, and validation of JSON:API resources and requests.

### Build JSON:API Relational Structures from Pydantic Models

**Native Pydantic Integration:** Automatically generates JSON:API-compliant resources and relationships from Pydantic models, eliminating boilerplate.  
**Relationship Management:** Supports to-one, to-many, and included resources, fully compliant with the JSON:API specification.  
**Smart Serialization:** Converts Pydantic objects into valid JSON:API documents, handling attributes, relationships, and metadata seamlessly.  

### Parse JSON:API Query Parameters (Dotnet-style Syntax)

**Advanced Query Parsing:** Supports JSON:API.NET-style query parameters, including filtering, sorting, pagination, sparse fieldsets, and inclusion.  
**Built-in Validation:** Ensures query parameters are syntactically correct and consistent.  

- Filtering: filter=and(equals(name,'Guillaume'),greaterThan(age,18))
- Sorting: sort=-created,title
- Pagination: page[number]=1&page[size]=10
- Sparse Fieldsets: fields[articles]=title,author
- Inclusion: include=author,comments

### Flask Extension for JSON:API Response Formatting

**Ready-to-use Flask Integration:** Provides a Flask extension to automatically encapsulate responses in JSON:API format, including:

- Resources (data, relationships, attributes)
- Pagination (links, page metadata)
- Errors (standardized JSON:API error objects)

**Simplified Endpoints**: Reduces manual response formatting, ensuring compliance with JSON:API standards.

## Relationship decomposition

To automate and standardize the definition of `relationships` in our JSON:API implementation, we leveraged Pydantic’s
data model.  
This approach allowed us to dynamically infer relationships between resources without manually declaring them for each
object type.  

The principle is as follows:

- A Pydantic model represents a resource (e.g., JSON:API Resource Object).
- If an attribute of this model is itself a Pydantic object (or a list of Pydantic objects), it is automatically
  interpreted as a `relationship` in the JSON:API response.
- If the attribute is a primitive type (string, integer, boolean, or event dict etc.), it is treated as a standard
  `attribute`.

### Usage

#### Serialization

Define your data models in Pydantic, let *japyd* automatically handle serialization—including relationships and included
resources—and expose a standard-compliant JSON:API with Flask in just a few lines of code.

```python
import typing as t

import pytest
from flask import Flask
from flask_pydantic import validate

from japyd import JsonApiBaseModel
from japyd import JsonApiQueryModel
from japyd import TopLevel


class Product(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "product"

    id: str
    price: float


class Order(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "order"

    id: str
    customer_id: str
    items: list[Product]  # This field will be 'relationship' in JSON:API
    status: str  # This field will be classical 'attribute'


app = Flask(__name__)


@app.route("/orders/<order_id>")
@validate(exclude_none=True)
def get_order(order_id, query: JsonApiQueryModel):
    order = Order(id=order_id, customer_id="123", items=[Product(id="1", price=100.0)], status="open")
    return query.one_or_none(order)


@pytest.fixture()
def client():
    return app.test_client()


def test_request(client):
    response = client.get("/orders/3?include=items")
    top = TopLevel.model_validate(response.json)
    assert top.data.id == "3"
    assert top.data.attributes['status'] == 'open'
    assert len(top.data.relationships['items'].data) == 1
    assert top.included[0].type == "product"
```

You can bypass this behavior by annotationg the field as follow:

```python
    items: Annotated[list[Product], 'as_attribute']  # This field will be now an 'attribute' in JSON:API
```

#### Deserialization

Deserialization of JSON:API resource objects into flat dictionaries is handled by the `flatten_resource` function. This function extracts resource attributes along with the `id` and `type` fields, and can optionally flatten nested relationships using a pattern parameter.

```python
from japyd import TopLevel, flatten_resource, extract_relationship

# Example: flatten a resource with nested relationships
response = client.get("/orders/3?include=items")
top = TopLevel.model_validate(response.json)

# Flatten the resource to a dictionary
flattened = flatten_resource(top.data)
# Result: {"type": "order", "id": "3", "customer_id": "123", "status": "open"}

# Flatten with nested relationships using pattern
flattened_with_items = flatten_resource(
    top.data, 
    toplevel=top, 
    pattern="items"
)
# Result: {"type": "order", "id": "3", "customer_id": "123", "status": "open", 
#          "items": [{"type": "product", "id": "1", "price": 100.0}]}
```

#### Filtering

Filters use the [JsonApiDotNetCore filter syntax](https://www.jsonapi.net/usage/reading/filtering.html).
They are parsed by `JsonApiQueryModel` and evaluated on Pydantic models with `query.match(model)`:

```python
@app.route("/orders")
@validate(exclude_none=True)
def get_orders(query: JsonApiQueryModel):
    orders = [order for order in load_orders() if query.match(order)]
    return query.paginate(orders)
```

```http
GET /orders?filter=and(equals(status,'open'),has(items,greaterThan(price,50)))
```

| Operator | Example | Meaning |
| --- | --- | --- |
| `equals` | `equals(status,'open')`, `equals(comment,null)` | equality, `null` for missing value |
| `lessThan`, `lessOrEqual`, `greaterThan`, `greaterOrEqual` | `greaterThan(price,10)` | ordering |
| `contains`, `startsWith`, `endsWith` | `startsWith(name,'Bri')` | string matching |
| `containsIgnoreCase`, `startsWithIgnoreCase`, `endsWithIgnoreCase` | `containsIgnoreCase(name,'bri')` | case insensitive (japyd extension) |
| `any` | `any(status,'open','closed')` | value is one of the list |
| `has` | `has(items)`, `has(items,greaterThan(price,50))` | to-many relationship is not empty, or has an item matching the filter |
| `not`, `and`, `or` | `or(equals(a,1),not(equals(b,2)))` | logical composition, `and`/`or` take 2 or more filters |

Values:

- strings are quoted with `'`, a quote inside a string is doubled: `'O''Connor'`
- numbers, `true`, `false` and `null` are written unquoted
- an unquoted name is another attribute of the model: `lessThan(quantity,stock)`

Attributes:

- a dotted path follows to-one relationships and dict (JSON) attributes: `equals(customer.country,'FR')`,
  `equals(tenant_data.gmp+,true)` (in a URL, `+` must be encoded as `%2B`)
- to-many relationships are filtered with `has`
- as in SQL, a `null` value never matches an ordering or string operator

Errors:

- a syntax error returns `422 Unprocessable Entity`
- an unknown attribute or incompatible types return `400 Bad Request` (`FilterError` when calling `model.match`
  directly)

Not supported yet: `count()`, `isType()` and filter scoping on relationships (`filter[items]=...`).

## References

*japyd* (JsonApi PYDantic) is a coherent and powerful composition of :

1. Pydantic and its Flask extension [Flask-Pydantic](https://github.com/pallets-eco/flask-pydantic)
1. Filtering syntax defined in the dotnet implementation [JsonApiDotNetCore](https://www.jsonapi.net/).
1. Simple relationship extraction and other structure manipulations.

## 🚀 Looking for Contributors

We’re actively seeking developers, testers, and open-source enthusiasts to help us build and improve japyd.
Whether you’re passionate about data validation, API design, or just want to contribute to an innovative open-source
project, your help is welcome! Check out our contribution guidelines and open issues to get started. Let’s shape the
future of Python APIs together! 💻✨
