import pytest
from flask import Flask
from flask_pydantic import validate
from werkzeug.exceptions import UnprocessableEntity

from japyd import JsonApiApp, JsonApiQueryModel, TopLevel

app = Flask(__name__)
JsonApiApp(app)


@app.route("/")
@validate(exclude_none=True)
def get(query: JsonApiQueryModel):
    raise UnprocessableEntity("error test")


@pytest.fixture()
def client():
    return app.test_client()


def test_request(client):
    response = client.get("/")
    assert response.status_code == 422
    top = TopLevel.model_validate(response.json)
    
    assert top.errors
    assert len(top.errors) == 1
    assert top.errors[0].detail == "error test"
