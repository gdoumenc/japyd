import pytest
from flask import Flask
from flask_pydantic import validate
from werkzeug.exceptions import UnprocessableEntity

from japyd import JsonApiApp, JsonApiQueryModel, TopLevel

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

    response = client.get("/exception")
    assert response.status_code == 500
    assert "application/vnd.api+json" in response.headers["Content-Type"]
    top = TopLevel.model_validate(response.json)

    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].title == "NotImplementedError"
    assert top.errors[0].detail == "abstract"


def test_error(client):
    response = client.get("/make_error")
    assert response.status_code == 422
    assert "application/vnd.api+json" in response.headers["Content-Type"]
    top = TopLevel.model_validate(response.json)
    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].title == "title"
