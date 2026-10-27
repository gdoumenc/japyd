import typing as t
from typing import Annotated

import pytest
from flask import Flask
from flask_pydantic import validate
from pydantic import field_serializer

from japyd import JsonApiApp, JsonApiBaseModel, JsonApiQueryModel, Resource, TopLevel


class Product(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "product"

    id: str
    price: float


class Customer(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "customer"

    id: str
    products: list[Product] = []


class Order(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "order"

    id: str
    customer_id: str
    products: list[Product]
    items: Annotated[list[Product], "as_attribute"]  # This attribute will be an 'attribute' in JSON:API
    status: str  # This attribute will be classical 'attribute'
    customer: Customer | None = None
    others: list[Product] | None = None

    @field_serializer("items")
    def serialize_items(self, items):
        return [item.price for item in items]


app = Flask(__name__)
JsonApiApp(app)


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
    response = client.get("/orders/3?include=products")
    top = TopLevel.model_validate(response.json)
    assert isinstance(top.data, Resource)
    assert top.data.id == "3"
    assert top.data.attributes["status"] == "open"
    assert top.data.relationships is not None
    assert "products" in top.data.relationships
    assert "products" not in top.data.attributes
    assert "items" not in top.data.relationships
    assert "items" in top.data.attributes
    assert 100.0 in top.data.attributes["items"]


def test_empty_relationships(client):
    response = client.get("/orders/3")
    data = response.json["data"]
    assert data["relationships"]["customer"] == {"data": None}
    assert data["relationships"]["others"] == {"data": []}
    assert "customer" not in data["attributes"]
    assert "others" not in data["attributes"]


@pytest.mark.parametrize("include", ["products", "customer", "customer.products", "products,customer.products"])
def test_include_valid(client, include):
    response = client.get(f"/orders/3?include={include}")
    assert response.status_code == 200


@pytest.mark.parametrize("include", ["unknown", "items", "status", "customer.unknown", "products.price"])
def test_include_unknown(client, include):
    response = client.get(f"/orders/3?include={include}")
    assert response.status_code == 400
    assert include.split(".")[-1] in response.json["errors"][0]["detail"]
