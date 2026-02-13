import json
import typing as t
from unittest import mock

from flask import Flask
from flask_pydantic import validate

from japyd import (
    JapydClient,
    JsonApiApp,
    JsonApiBaseModel,
    JsonApiQueryModel,
    MultiResourcesTopLevel,
    Resource,
    SingleResourceTopLevel,
)


class Order(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "order"

    id: str


app = Flask(__name__)
JsonApiApp(app)


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


def mocked_requests_get(*args, **kwargs):
    with app.test_client() as client:
        value = client.get(*args[1:], **kwargs)

        class Response:
            def json(self):
                return json.loads(value.data)

        return Response()


@mock.patch("requests.request", side_effect=mocked_requests_get)
def test_request(request):
    client = JapydClient("/")

    headers = {"Accept": "application/vnd.api+json"}

    response = client("get", "/orders", headers=headers)
    top = MultiResourcesTopLevel.model_validate(response)
    assert isinstance(top.data, list)
    assert len(top.data) == 1

    response = client("get", "/orders", query_string={"filter":"equals(id,'3')"})
    top = MultiResourcesTopLevel.model_validate(response)
    assert isinstance(top.data, list)
    assert len(top.data) == 1

    response = client("get", "/orders", query_string={"filter": "equals(id,3)"})
    top = MultiResourcesTopLevel.model_validate(response)
    assert isinstance(top.data, list)
    assert len(top.data) == 0

    response = client("get", "/orders", id=3)
    top = SingleResourceTopLevel.model_validate(response)
    assert isinstance(top.data, Resource)
    assert top.data is not None
    assert top.data.id == "3"

    res = top.data.flatten()
    assert isinstance(res, dict)
    assert res["id"] == "3"
    assert len(res) == 2
