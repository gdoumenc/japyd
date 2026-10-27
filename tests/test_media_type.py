import pytest
from flask import Flask
from flask_pydantic import validate

from japyd import JsonApiApp, JsonApiQueryModel, SingleBodyModel, TopLevel

app = Flask(__name__)
JsonApiApp(app)


@app.post("/items")
@validate(exclude_none=True)
def create_item(body: SingleBodyModel, query: JsonApiQueryModel):
    return query.one(body.data)


@pytest.fixture()
def client():
    return app.test_client()


BODY = '{"data": {"type": "item", "id": "1"}}'
EXTENSION = 'ext="https://jsonapi.org/ext/atomic"'
PROFILE = 'profile="https://example.com/profile"'


@pytest.mark.parametrize(
    "content_type",
    ["application/vnd.api+json", f"application/vnd.api+json; {PROFILE}", "application/json"],
)
def test_supported_content_type(client, content_type):
    response = client.post("/items", data=BODY, content_type=content_type)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "content_type",
    ["application/vnd.api+json; charset=utf-8", f"application/vnd.api+json; {EXTENSION}"],
)
def test_unsupported_content_type(client, content_type):
    response = client.post("/items", data=BODY, content_type=content_type)
    assert response.status_code == 415
    top = TopLevel.model_validate(response.json)
    assert top.errors and top.errors[0].status == "415"


@pytest.mark.parametrize(
    "accept, content_type",
    [
        ("application/vnd.api+json", "application/vnd.api+json"),
        (f"application/vnd.api+json; {PROFILE}", "application/vnd.api+json"),
        (f"application/vnd.api+json; {EXTENSION}, application/vnd.api+json", "application/vnd.api+json"),
        ("application/json", "application/json"),
        ("*/*", "application/json"),
    ],
)
def test_supported_accept(client, accept, content_type):
    response = client.post("/items", data=BODY, content_type="application/vnd.api+json", headers={"Accept": accept})
    assert response.status_code == 200
    assert response.headers["Content-Type"] == content_type


@pytest.mark.parametrize(
    "accept",
    [
        f"application/vnd.api+json; {EXTENSION}",
        "application/vnd.api+json; version=1",
        # A wildcard does not prevent the 406, as all the JSON:API media type instances are unsupported
        f"application/vnd.api+json; {EXTENSION}, */*",
    ],
)
def test_not_acceptable(client, accept):
    response = client.post("/items", data=BODY, content_type="application/vnd.api+json", headers={"Accept": accept})
    assert response.status_code == 406
    assert response.headers["Content-Type"] == "application/vnd.api+json"
    top = TopLevel.model_validate(response.json)
    assert top.errors and top.errors[0].status == "406"
