import typing as t

import pytest
from flask import Flask
from flask_pydantic import validate

from japyd import JsonApiBaseModel, JsonApiQueryModel, Resource, TopLevel


class Product(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "product"

    id: str
    price: float


class Order(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "order"

    id: str
    customer_id: str
    items: list[Product]  # This attribute will be 'relationship' in JSON:API
    status: str  # This attribute will be classical 'attribute'


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

    assert isinstance(top.data, Resource)

    assert top.data.id == "3"
    assert top.data.attributes["status"] == "open"

    assert top.data.relationships is not None
    assert top.included is not None
    assert isinstance(top.data.relationships["items"].data, list)

    assert len(top.data.relationships["items"].data) == 1
    assert top.included[0].type == "product"
