import typing as t

import pytest
from flask import Flask
from flask_pydantic import validate

from japyd import JapydClient, JsonApiBaseModel, JsonApiQueryModel, TopLevel


class Order(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "order"

    id: str


app = Flask(__name__)


@app.route("/orders")
@validate(exclude_none=True)
def get_order(order_id, query: JsonApiQueryModel):
    order = Order(id=order_id)
    return query.one_or_none(order)


@app.route("/orders/<order_id>")
@validate(exclude_none=True)
def get_order_id(order_id, query: JsonApiQueryModel):
    order = Order(id=order_id)
    return query.one_or_none(order)


@pytest.fixture()
def client():
    return JapydClient("/")


# @pytest.mark.wip
# def test_request(client):
#     response = client.get("/orders/3")
#     top = TopLevel.model_validate(response.json)
#     assert top.data.id == "3"
