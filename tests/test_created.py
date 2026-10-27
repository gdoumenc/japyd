import typing as t

import pytest
from flask import Flask, url_for
from flask_pydantic import validate
from pydantic import AnyUrl

from japyd import JsonApiApp, JsonApiBaseModel, JsonApiQueryModel, Link, SingleBodyModel, TopLevel


class Author(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "author"

    id: str = ""
    name: str


class LinkedAuthor(Author):
    @property
    def links(self) -> dict[str, AnyUrl | Link | None] | None:
        return {"self": Link(href=f"http://localhost/authors/{self.id}")}


app = Flask(__name__)
JsonApiApp(app)


@app.get("/authors/<author_id>")
@validate(exclude_none=True)
def get_author(author_id: str, query: JsonApiQueryModel):
    return query.one(Author(id=author_id, name="Ursula"))


@app.post("/authors")
@validate(exclude_none=True)
def create_author(body: SingleBodyModel, query: JsonApiQueryModel):
    author = Author.from_resource(body.data)
    author.id = "42"
    return query.created(author, location=url_for("get_author", author_id=author.id))


@app.post("/linked_authors")
@validate(exclude_none=True)
def create_linked_author(body: SingleBodyModel, query: JsonApiQueryModel):
    author = LinkedAuthor.from_resource(body.data)
    author.id = "43"
    return query.created(author)


@app.post("/unlocated_authors")
@validate(exclude_none=True)
def create_unlocated_author(body: SingleBodyModel, query: JsonApiQueryModel):
    author = Author.from_resource(body.data)
    author.id = "44"
    return query.created(author)


@pytest.fixture()
def client():
    return app.test_client()


BODY = {"data": {"type": "author", "attributes": {"name": "Ursula"}}}


def test_created_with_location(client):
    response = client.post("/authors", json=BODY)
    assert response.status_code == 201
    assert response.headers["Location"] == "/authors/42"
    top = TopLevel.model_validate(response.json)
    assert top.data is not None and not isinstance(top.data, list)
    assert top.data.id == "42"
    assert top.data.attributes["name"] == "Ursula"


def test_created_location_from_self_link(client):
    response = client.post("/linked_authors", json=BODY)
    assert response.status_code == 201
    assert response.headers["Location"] == "http://localhost/authors/43"


def test_created_without_location(client):
    response = client.post("/unlocated_authors", json=BODY)
    assert response.status_code == 201
    assert "Location" not in response.headers
    assert response.json["data"]["id"] == "44"
