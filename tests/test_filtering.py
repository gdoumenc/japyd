import typing as t

import pytest
from flask import Flask, request
from flask_pydantic import validate
from pydantic import computed_field

from japyd.dotnet import (
    JsonApiBodyModel,
    JsonApiQueryModel,
    Oper,
    SingleResourceTopLevel,
)
from japyd.models import JsonApiBaseModel


class OtherBaseModel(JsonApiBaseModel):
    attr1: str = "undefined"

    @computed_field
    @property
    def jsonapi_id(self) -> str:
        return self.attr1


class ExampleBaseModel(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "example"
    name: str = "Brian O'Connor"
    notice: int = 10
    other: OtherBaseModel | None = None


class ExampleBodyModel(JsonApiBodyModel):
    data: ExampleBaseModel | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


@pytest.fixture()
def client():
    pytest_app = Flask("test")

    @pytest_app.route("/")
    @validate(exclude_none=True)
    def test(query: JsonApiQueryModel):
        return ""

    @pytest_app.route("/example", methods=["GET"])
    @validate(exclude_none=True)
    def get_example(query: JsonApiQueryModel):
        example = ExampleBaseModel()
        if query.match(example):
            return example.as_resource([], query)
        return SingleResourceTopLevel.empty()

    @pytest_app.route("/example", methods=["POST"])
    @validate(exclude_none=True)
    def post_example(body: ExampleBodyModel, query: JsonApiQueryModel):
        if body.data:
            example = ExampleBaseModel(**body.data.model_dump())
        else:
            example = ExampleBaseModel()

        if query.match(example):
            return SingleResourceTopLevel(data=example.as_resource([], query))
        return SingleResourceTopLevel.empty()

    @pytest_app.route("/multi", methods=["GET"])
    @validate(exclude_none=True)
    def get_multi(query: JsonApiQueryModel):
        assert query.filters is not None
        assert len(query.filters) == 2
        return SingleResourceTopLevel.empty()

    with pytest_app.test_client() as client:
        yield client


class TestFilter:

    def test_parse(self, client):
        client.get("/", query_string={"filter": "equals(name,'Brian O''Connor')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.attr == "name"
        assert filter.oper == Oper.EQUALS
        assert filter.value == "Brian O'Connor"
        assert filter.other_attr is None

        client.get("/", query_string={"filter": "equals(attr1,null)"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.attr == "attr1"
        assert filter.oper == Oper.EQUALS
        assert filter.value is None
        assert filter.other_attr is None

        client.get("/", query_string={"filter": "lessThan(price,'10')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.attr == "price"
        assert filter.oper == Oper.LESS_THAN
        assert filter.value == "10"
        assert filter.other_attr is None

        client.get("/", query_string={"filter": "lessOrEqual(attr1,attr2)"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.attr == "attr1"
        assert filter.oper == Oper.LESS_OR_EQUAL
        assert filter.value is None
        assert filter.other_attr == "attr2"

    def test_parse_spaces(self, client):
        client.get("/", query_string={"filter": " equals (name,'Brian O''Connor')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.attr == "name"
        assert filter.oper == Oper.EQUALS
        assert filter.value == "Brian O'Connor"
        assert filter.other_attr is None

        client.get("/", query_string={"filter": "equals(attr1,null) "})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.attr == "attr1"
        assert filter.oper == Oper.EQUALS
        assert filter.value is None
        assert filter.other_attr is None

        client.get("/", query_string={"filter": "lessThan( price , '10' )"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.attr == "price"
        assert filter.oper == Oper.LESS_THAN
        assert filter.value == "10"
        assert filter.other_attr is None

    def test_parse_values(self, client):
        client.get("/", query_string={"filter": "equals(attr1,null)"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.value is None

        client.get("/", query_string={"filter": "equals(attr1,'null')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.value == "null"

        client.get("/", query_string={"filter": "equals(attr1,0)"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.value == 0

        client.get("/", query_string={"filter": "equals(attr1,0.0)"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert isinstance(filter.value, float)
        assert filter.value == 0.0

        client.get("/", query_string={"filter": "equals(attr1.attr2,0.0)"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert isinstance(filter.value, float)
        assert filter.value == 0.0

    def test_parse_not(self, client):
        client.get("/", query_string={"filter": "not(equals(attr1,null) )"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.oper == Oper.NOT
        assert filter.subfilter.attr == "attr1"
        assert filter.subfilter.oper == Oper.EQUALS
        assert filter.subfilter.value is None

    def test_parse_any(self, client):
        client.get("/", query_string={"filter": "any(attr1, 'test')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.oper == Oper.ANY
        assert filter.attr == "attr1"
        assert filter.value == ["test"]

        client.get("/", query_string={"filter": "any(attr1, 'test', 'other')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        ""
        assert filter.oper == Oper.ANY
        assert filter.attr == "attr1"
        assert filter.value == ["test", "other"]

    def test_parse_or(self):
        query_filter = "not(equals (name,'Brian O''Connor'), equals(attr1,null) )"
        query = JsonApiQueryModel.model_validate({"filter": query_filter})
        assert len(query.filters) == 1
        filter = next(iter(query.filters))

    def test_parse_filter_array(self, client):
        client.get("/", query_string={"filter[0]": "equals(attr1,0)", "filter[1]": "any(attr2, 'test', 'other')"})
        filters = list(request.query_params.filters)  # type: ignore
        assert len(filters) == 2
        assert filters[0].attr == "attr1"
        assert filters[0].oper == Oper.EQUALS
        assert filters[1].attr == "attr2"
        assert filters[1].oper == Oper.ANY


class TestReturnedValue:

    def test_match(self, client):
        res = client.get("/example", query_string={"filter": "equals(name,'Brian O''Connor')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"
        assert example.notice == 10

        res = client.get("/example", query_string={"filter": "not(equals(name,'Brian O''Connor'))"})
        assert res.status_code == 200
        assert "data" not in res.json
        assert "meta" in res.json
        assert "count" in res.json["meta"]
        assert res.json["meta"]["count"] == 0

        res = client.post("/example", query_string={"filter": "lessThan(notice, 5)"}, json={})
        assert res.status_code == 200
        res = client.post("/example", query_string={"filter": "greaterThan(notice, 5)"}, json={})
        assert res.status_code == 200

        res = client.post("/example", json={"data": {"notice": 15}})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json["data"]["attributes"])
        assert example.notice == 15
        res = client.post(
            "/example", json={"data": {"notice": 15}}, query_string={"filter": "greaterOrEqual(notice, 15)"}
        )
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json["data"]["attributes"])
        assert example.notice == 15

class TestMultiFilter:

    def test_multi(self, client):
        res = client.get("/multi?filter=equals(name,'Brian O''Connor')&filter=equals(notice,10)")
        assert res.status_code == 200
    # def test_fields(self, client):
    # res = client.get('/example')
    # assert res.status_code == 200
    # assert 'name' in res.json['attributes']
    # assert 'notice' in res.json['attributes']
    # assert 'other' in res.json['attributes']
    # res = client.get('/example', query_string={"fields[example]": "name"})
    # assert res.status_code == 200
    # assert 'name' in res.json['attributes']
    # assert 'notice' not in res.json['attributes']
    # assert 'other' not in res.json['attributes']

    # res = client.post(
    #     "/example",
    #     json={"data": {"notice": 15, "other": {"attr1": "test"}}},
    #     query_string={"filter": "greaterOrEqual(notice, 15)"},
    #     headers={"Content-Type": "application/vnd.api+json"},
    # )
    # assert res.status_code == 200
    # example = ExampleBaseModel(**res.json["attributes"])
    # assert example.notice == 15
    # assert "other" not in res.json["attributes"]
    # assert "other" in res.json["relationships"]
