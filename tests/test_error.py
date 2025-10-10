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


@pytest.fixture()
def client():
    return app.test_client()


def test_exception(client):
    response = client.get("/")
    assert response.status_code == 422
    top = TopLevel.model_validate(response.json)

    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].title == "Unprocessable Entity"
    assert top.errors[0].detail == "exception test"

    response = client.get("/error")
    assert response.status_code == 405
    top = TopLevel.model_validate(response.json)

    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].title == "error"
    assert top.errors[0].detail == "error"

    response = client.get("/exception")
    assert response.status_code == 500
    top = TopLevel.model_validate(response.json)

    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].title == "NotImplementedError"
    assert top.errors[0].detail == "abstract"
