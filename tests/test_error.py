import logging

import pytest
from flask import Flask
from flask_pydantic import validate
from werkzeug.exceptions import HTTPException, UnprocessableEntity

from japyd import JsonApiApp, JsonApiBaseModel, ResourceTypeError, SingleBodyModel, TopLevel

app = Flask(__name__)
JsonApiApp(app)


@app.route("/")
@validate(exclude_none=True)
def get():
    raise UnprocessableEntity("exception test")


@app.route("/error")
@validate(exclude_none=True)
def get_error():
    return "error", 405


@app.route("/exception")
@validate(exclude_none=True)
def get_exception():
    raise NotImplementedError("abstract")


@app.route("/make_error")
@validate(exclude_none=True)
def make_error():
    return TopLevel.error(code=422, title="title", detail="detail")


@app.route("/json")
def get_json():
    return {"data": None}


class Author(JsonApiBaseModel):
    jsonapi_type = "author"
    id: str = ""
    name: str


@app.route("/authors", methods=["POST"])
@validate(exclude_none=True)
def post_author(body: SingleBodyModel):
    assert body.data is not None
    return Author.from_resource(body.data).model_dump()


@pytest.fixture()
def client():
    return app.test_client()


def test_exception(client):
    response = client.get("/")
    assert response.status_code == 422
    assert "application/vnd.api+json" in response.headers["Content-Type"]
    top = TopLevel.model_validate(response.json)

    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].title == "Unprocessable Entity"
    assert top.errors[0].detail == "exception test"

    response = client.get("/error")
    assert response.status_code == 405
    assert "application/vnd.api+json" not in response.headers["Content-Type"]
    assert response.text == "error"
    assert response.json is None


def test_unhandled_exception_hidden_and_logged(client, caplog):
    with caplog.at_level(logging.ERROR):
        response = client.get("/exception")
    assert response.status_code == 500
    assert "application/vnd.api+json" in response.headers["Content-Type"]
    top = TopLevel.model_validate(response.json)

    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].title == "Internal Server Error"
    assert "abstract" not in response.text
    assert any(r.exc_info and isinstance(r.exc_info[1], NotImplementedError) for r in caplog.records)


def test_unhandled_exception_exposed(client):
    app.config["JSONAPI_EXPOSE_ERRORS"] = True
    try:
        response = client.get("/exception")
    finally:
        app.config["JSONAPI_EXPOSE_ERRORS"] = False
    assert response.status_code == 500
    top = TopLevel.model_validate(response.json)
    assert top.errors
    assert top.errors[0].title == "NotImplementedError"
    assert top.errors[0].detail == "abstract"


def test_content_type_with_several_accepted_types(client):
    response = client.get("/json", headers={"Accept": "application/vnd.api+json, text/html;q=0.9"})
    assert response.headers["Content-Type"] == "application/vnd.api+json"

    response = client.get("/json", headers={"Accept": "*/*"})
    assert response.headers["Content-Type"] == "application/json"


def test_error(client):
    response = client.get("/make_error")
    assert response.status_code == 422
    assert "application/vnd.api+json" in response.headers["Content-Type"]
    top = TopLevel.model_validate(response.json)
    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].title == "title"



def test_wrong_resource_type_conflict(client):
    response = client.post("/authors", json={"data": {"type": "author", "attributes": {"name": "Ursula"}}})
    assert response.status_code == 200

    response = client.post("/authors", json={"data": {"type": "book", "attributes": {"name": "Ursula"}}})
    assert response.status_code == 409
    top = TopLevel.model_validate(response.json)
    assert top.errors
    assert top.errors[0].title == "Conflict"
    assert top.errors[0].detail == "The resource type must be author, not book."


def test_resource_type_error_is_a_value_error():
    assert issubclass(ResourceTypeError, ValueError)
