import typing as t
from typing import Annotated

import pytest
from flask import Flask
from flask_pydantic import validate
from pydantic import field_serializer

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
    products: list[Product]
    items: Annotated[list[Product], 'as_attribute']  # This attribute will be an 'attribute' in JSON:API
    status: str  # This attribute will be classical 'attribute'

    @field_serializer('items')
    def serialize_items(self, items):
        return [item.price for item in items]


app = Flask(__name__)


@app.route("/orders/<order_id>")
@validate(exclude_none=True)
def get_order(order_id, query: JsonApiQueryModel):
    product = Product(id="1", price=100.0)
    order = Order(id=order_id, customer_id="123", products=[product], items=[product], status="open")
    return query.one_or_none(order)


@pytest.fixture()
def client():
    return app.test_client()


def test_include(client):
    response = client.get("/orders/3?include=products, items")
    top = TopLevel.model_validate(response.json)
    assert top.data.id == "3"
    assert top.data.attributes['status'] == 'open'
    assert 'products' in top.data.relationships
    assert 'products' not in top.data.attributes
    assert 'items' not in top.data.relationships
    assert 'items' in top.data.attributes
    assert 100.0 in top.data.attributes['items']

