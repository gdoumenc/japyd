# japyd

> *"JSON:API, Pydantically simple."*

Automate JSON:API relationships with Pydantic. No manual mapping, just clean code.

[![Tests](https://github.com/gdoumenc/japyd/actions/workflows/tests.yml/badge.svg)](https://github.com/gdoumenc/japyd/actions/workflows/tests.yml)
[![Codecov](https://codecov.io/gh/gdoumenc/japyd/branch/main/graph/badge.svg)](https://codecov.io/gh/gdoumenc/japyd)
[![PyPI](https://img.shields.io/pypi/v/japyd)](https://pypi.org/project/japyd/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/gdoumenc/japyd/refs/heads/master/pyproject.toml)](https://pypi.org/project/japyd/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/gdoumenc/japyd/graphs/commit-activity)
[![Open Source](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/gdoumenc/japyd)

## Description

To automate and standardize the definition of `relationships` in our JSON:API implementation, we leveraged Pydantic’s
data model.
This approach allowed us to dynamically infer relationships between resources without manually declaring them for each
object type.

The principle is as follows:

- A Pydantic model represents a resource (e.g., JSON:API Resource Object).
- If an attribute of this model is itself a Pydantic object (or a list of Pydantic objects), it is automatically
- interpreted as a `relationship` in the JSON:API response.
- If the attribute is a primitive type (string, integer, boolean, or event dict etc.), it is treated as a standard
  `attribute`.

## Usage

### Serialization

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

### Filtering

The complete filtering syntax of [JsonApiDotNetCore](https://www.jsonapi.net/) is supported


## References

*japyd* (JsonApi PYDantic) is a coherent and powerful composition of :

1. Pydantic and its Flask extension [Flask-Pydantic](https://github.com/pallets-eco/flask-pydantic)
1. Filtering syntax defined in the dotnet implementation [JsonApiDotNetCore](https://www.jsonapi.net/).
1. Simple relationship extraction and other structure manipulations.

## 🚀 Looking for Contributors!

We’re actively seeking developers, testers, and open-source enthusiasts to help us build and improve japyd.
Whether you’re passionate about data validation, API design, or just want to contribute to an innovative open-source
project, your help is welcome! Check out our contribution guidelines and open issues to get started. Let’s shape the
future of Python APIs together! 💻✨
