import typing as t
from unittest import mock

import pytest
from flask import Flask
from flask_pydantic import validate

from japyd import (
    JapydClient,
    JsonApiBaseModel,
    JsonApiQueryModel,
    MultiResourcesTopLevel,
    SingleResourceTopLevel,
)


class Order(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "order"

    id: str


app = Flask(__name__)


@app.route("/orders")
@validate(exclude_none=True)
def get_order(query: JsonApiQueryModel):
    order = Order(id="3")
    data = [order.as_resource([], query)] if query.match(order) else []
    return query.paginate(data)


@app.route("/orders/<order_id>")
@validate(exclude_none=True)
def get_order_id(order_id, query: JsonApiQueryModel):
    order = Order(id=order_id)
    return query.one_or_none(order)


@pytest.fixture()
def client():
    return JapydClient("/")


def mocked_requests_get(*args, **kwargs):
    with app.test_client() as client:
        return client.get(*args[1:], query_string=kwargs)


@mock.patch("requests.get", side_effect=mocked_requests_get)
def test_request(client):
    response = client("get", "/orders")
    top = MultiResourcesTopLevel.model_validate(response.json)
    assert len(top.data) == 1

    response = client("get", "/orders", filter="equals(id,'3')")
    top = MultiResourcesTopLevel.model_validate(response.json)
    assert len(top.data) == 1

    response = client("get", "/orders", filter="equals(id,3)")
    top = MultiResourcesTopLevel.model_validate(response.json)
    assert len(top.data) == 0

    response = client("get", "/orders/3")
    top = SingleResourceTopLevel.model_validate(response.json)
    assert top.data is not None
    assert top.data.id == "3"
