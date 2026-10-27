import datetime
import typing as t
from decimal import Decimal
from enum import StrEnum

import pytest
from flask import Flask, request
from flask_pydantic import validate
from pydantic import Field, computed_field
from werkzeug.exceptions import BadRequest, UnprocessableEntity

from japyd import (
    FilterError,
    JsonApiBodyModel,
    JsonApiQueryModel,
    SingleResourceTopLevel,
)
from japyd.dotnet import Oper
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

    def test_parse_string_operators(self, client):
        client.get("/", query_string={"filter": "contains(name,'Brian')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.oper == Oper.CONTAINS
        assert filter.attr == "name"
        assert filter.value == "Brian"

        client.get("/", query_string={"filter": "startsWith(name,'Brian')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.oper == Oper.STARTS_WITH
        assert filter.attr == "name"
        assert filter.value == "Brian"

        client.get("/", query_string={"filter": "endsWith(name,'Connor')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.oper == Oper.ENDS_WITH
        assert filter.attr == "name"
        assert filter.value == "Connor"

    def test_parse_string_operators_ignore_case(self, client):
        client.get("/", query_string={"filter": "containsIgnoreCase(name,'brian')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.oper == Oper.CONTAINS_IGNORE_CASE
        assert filter.attr == "name"
        assert filter.value == "brian"

        client.get("/", query_string={"filter": "startsWithIgnoreCase(name,'BRIAN')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.oper == Oper.STARTS_WITH_IGNORE_CASE
        assert filter.attr == "name"
        assert filter.value == "BRIAN"

        client.get("/", query_string={"filter": "endsWithIgnoreCase(name,'CONNOR')"})
        assert len(request.query_params.filters) == 1  # type: ignore
        filter = next(iter(request.query_params.filters))  # type: ignore
        assert filter.oper == Oper.ENDS_WITH_IGNORE_CASE
        assert filter.attr == "name"
        assert filter.value == "CONNOR"

    def test_parse_or(self):
        query_filter = "or(equals(name,'Brian O''Connor, Jr'), equals(attr1,null) )"
        query = JsonApiQueryModel.model_validate({"filter": query_filter})
        assert len(query.filters) == 1
        filter = next(iter(query.filters))
        assert filter.oper == Oper.OR
        assert len(filter.subfilter) == 2
        assert filter.subfilter[0].oper == Oper.EQUALS
        assert filter.subfilter[0].attr == "name"
        assert filter.subfilter[0].value == "Brian O'Connor, Jr"
        assert filter.subfilter[1].attr == "attr1"
        assert filter.subfilter[1].value is None

    def test_parse_and(self):
        query_filter = "and(equals(a,'1'),greaterThan(b,2),startsWith(c,'x'))"
        filter = JsonApiQueryModel.model_validate({"filter": query_filter}).filters[0]
        assert filter.oper == Oper.AND
        assert [f.oper for f in filter.subfilter] == [Oper.EQUALS, Oper.GREATER_THAN, Oper.STARTS_WITH]
        assert [f.value for f in filter.subfilter] == ["1", 2, "x"]

    def test_parse_nested_logical(self):
        query_filter = "and(equals(a,'1'),or(equals(b,'2'),not(equals(c,'3'))))"
        filter = JsonApiQueryModel.model_validate({"filter": query_filter}).filters[0]
        assert filter.oper == Oper.AND
        first, second = filter.subfilter
        assert first.attr == "a"
        assert second.oper == Oper.OR
        assert second.subfilter[0].attr == "b"
        assert second.subfilter[1].oper == Oper.NOT
        assert second.subfilter[1].subfilter.attr == "c"

    @pytest.mark.parametrize(
        "query_filter",
        [
            "and(equals(a,'1'))",  # and requires at least two filters
            "or(equals(a,'1'),)",
            "not(equals(a,'1'),equals(b,'2'))",  # not takes exactly one filter
            "and(equals(a,'1'),equals(b,'2')",
            "and(equals(a,'1')),equals(b,'2'))",
            "and(equals(a,'1),equals(b,'2'))",
            "not(equals(a,'1')) trailing",
        ],
    )
    def test_parse_wrong_logical(self, query_filter):
        with pytest.raises(UnprocessableEntity):
            JsonApiQueryModel.model_validate({"filter": query_filter})

    def test_parse_special_characters(self, client):
        filter = JsonApiQueryModel.model_validate({"filter": "equals(tenant_data.gmp+,true)"}).filters[0]
        assert filter.attr == "tenant_data.gmp+"
        assert filter.value is True
        assert filter.other_attr is None

        filter = JsonApiQueryModel.model_validate({"filter": "equals(a,false)"}).filters[0]
        assert filter.value is False

        filter = JsonApiQueryModel.model_validate({"filter": "equals(a,5x)"}).filters[0]
        assert filter.value is None
        assert filter.other_attr == "5x"

        # In a query string '+' is decoded as a space, so it must be encoded as %2B
        client.get("/?filter=equals(tenant_data.gmp%2B,true)")
        filter = request.query_params.filters[0]  # type: ignore
        assert filter.attr == "tenant_data.gmp+"

    def test_parse_quoted_values(self):
        filter = JsonApiQueryModel.model_validate({"filter": "equals(a,'''quoted''')"}).filters[0]
        assert filter.value == "'quoted'"

        filter = JsonApiQueryModel.model_validate({"filter": "any(a,'x,y','O''Connor',3)"}).filters[0]
        assert filter.value == ["x,y", "O'Connor", 3]

    @pytest.mark.parametrize(
        "query_filter, value",
        [("equals(a,1e5)", 1e5), ("equals(a,-2E-3)", -2e-3), ("equals(a,-12)", -12), ("any(a,1e2,3)", [100.0, 3])],
    )
    def test_parse_numbers(self, query_filter, value):
        assert JsonApiQueryModel.model_validate({"filter": query_filter}).filters[0].value == value

    def test_parse_too_nested(self):
        JsonApiQueryModel.model_validate({"filter": "not(" * 30 + "equals(a,1)" + ")" * 30})
        with pytest.raises(UnprocessableEntity):
            JsonApiQueryModel.model_validate({"filter": "not(" * 2000 + "equals(a,1)" + ")" * 2000})

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
        assert res.json["data"] is None
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

    def test_match_string_operators(self, client):
        # Test contains with lowercase
        res = client.get("/example", query_string={"filter": "contains(name,'rian')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

        # Test startsWith with lowercase
        res = client.get("/example", query_string={"filter": "startsWith(name,'Brian')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

        # Test endsWith with lowercase
        res = client.get("/example", query_string={"filter": "endsWith(name,'Connor')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

    def test_match_string_operators_ignore_case(self, client):
        # Test containsIgnoreCase with uppercase - should match "Brian O'Connor"
        res = client.get("/example", query_string={"filter": "containsIgnoreCase(name,'BRIAN')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

        # Test containsIgnoreCase with lowercase
        res = client.get("/example", query_string={"filter": "containsIgnoreCase(name,'connor')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

        # Test startWithIgnoreCase with uppercase - should match "Brian O'Connor"
        res = client.get("/example", query_string={"filter": "startsWithIgnoreCase(name,'BRIAN')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

        # Test startWithIgnoreCase with lowercase
        res = client.get("/example", query_string={"filter": "startsWithIgnoreCase(name,'brian')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

        # Test endsWithIgnoreCase with uppercase - should match "Brian O'Connor"
        res = client.get("/example", query_string={"filter": "endsWithIgnoreCase(name,'CONNOR')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

        # Test endsWithIgnoreCase with lowercase
        res = client.get("/example", query_string={"filter": "endsWithIgnoreCase(name,'connor')"})
        assert res.status_code == 200
        example = ExampleBaseModel(**res.json)
        assert example.name == "Brian O'Connor"

        # Test that case-sensitive operators do NOT match with wrong case
        res = client.get("/example", query_string={"filter": "contains(name,'BRIAN')"})
        assert res.status_code == 200
        assert "meta" in res.json

        res = client.get("/example", query_string={"filter": "startsWith(name,'brian')"})
        assert res.status_code == 200
        assert "meta" in res.json

        res = client.get("/example", query_string={"filter": "endsWith(name,'CONNOR')"})
        assert res.status_code == 200
        assert "meta" in res.json


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


class LineModel(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "line"
    id: str
    quantity: int


class Status(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class MatchedModel(JsonApiBaseModel):
    jsonapi_type: t.ClassVar[str] = "matched"
    name: str = "Brian"
    notice: int = 10
    limit: int = 20
    lines: list[LineModel] = Field(
        default_factory=lambda: [LineModel(id="1", quantity=1), LineModel(id="2", quantity=5)]
    )
    others: list[LineModel] | None = None
    main: LineModel = Field(default_factory=lambda: LineModel(id="1", quantity=1))
    secondary: LineModel | None = None
    comment: str | None = None
    tenant_data: dict = Field(default_factory=lambda: {"gmp+": True, "é-x/y": "Brian", "sub": {"key": 1}})
    created: datetime.date = datetime.date(2025, 6, 15)
    updated: datetime.datetime = datetime.datetime(2025, 6, 15, 10, 30)
    price: Decimal = Decimal("12.50")
    status: Status = Status.OPEN


class TestMatch:

    @pytest.mark.parametrize(
        "query_filter, expected",
        [
            ("not(equals(name,'Brian'))", False),
            ("not(equals(name,'Dom'))", True),
            ("and(equals(name,'Brian'),greaterThan(notice,5))", True),
            ("and(equals(name,'Brian'),greaterThan(notice,5),lessThan(notice,8))", False),
            ("or(equals(name,'Dom'),equals(notice,10))", True),
            ("or(equals(name,'Dom'),equals(notice,11))", False),
            ("and(equals(name,'Brian'),or(equals(notice,11),not(equals(notice,12))))", True),
            ("any(name,'Dom','Brian')", True),
            ("any(notice,1,2)", False),
            ("has(lines)", True),
            ("has(others)", False),
            ("has(lines,greaterThan(quantity,3))", True),
            ("has(lines,greaterThan(quantity,10))", False),
            ("has(lines,and(equals(id,'1'),equals(quantity,1)))", True),
            ("has(others,equals(id,'1'))", False),
            ("not(has(others))", True),
            ("equals(main.id,'1')", True),
            ("greaterThan(main.quantity,0)", True),
            ("lessThan(notice,main.quantity)", False),
            ("equals(secondary.id,null)", True),
            ("equals(secondary.id,'1')", False),
            ("equals(comment,null)", True),
            ("not(equals(comment,null))", False),
            ("lessThan(comment,'a')", False),
            ("greaterOrEqual(comment,'a')", False),
            ("contains(comment,'a')", False),
            ("startsWithIgnoreCase(comment,'a')", False),
            ("greaterThan(secondary.quantity,0)", False),
            ("lessThan(notice,null)", False),
            ("equals(tenant_data.gmp+,true)", True),
            ("equals(tenant_data.gmp+,false)", False),
            ("equals(tenant_data.é-x/y,name)", True),
            ("equals(tenant_data.sub.key,1)", True),
            ("equals(tenant_data.missing,null)", True),
            ("equals(tenant_data.missing.key,null)", True),
            ("and(equals(tenant_data.gmp+,true),any(tenant_data.é-x/y,'Dom','Brian'))", True),
            ("lessThan(notice,limit)", True),
            ("greaterThan(notice,limit)", False),
            # The value is converted to the attribute type
            ("greaterThan(created,'2025-01-01')", True),
            ("lessThan(created,'2025-01-01')", False),
            ("equals(created,'2025-06-15')", True),
            ("any(created,'2024-01-01','2025-06-15')", True),
            ("greaterOrEqual(updated,'2025-06-15T10:30:00')", True),
            ("lessThan(updated,'2025-06-15T10:00:00')", False),
            ("equals(price,'12.5')", True),
            ("greaterThan(price,12)", True),
            ("equals(status,'open')", True),
            ("any(status,'closed')", False),
            ("equals(status,'unknown')", False),
            ("equals(notice,'10')", True),
        ],
    )
    def test_match(self, query_filter, expected):
        query = JsonApiQueryModel.model_validate({"filter": query_filter})
        assert query.match(MatchedModel()) is expected

    def test_parse_has(self):
        filter = JsonApiQueryModel.model_validate({"filter": "has(lines)"}).filters[0]
        assert filter.oper == Oper.HAS
        assert filter.attr == "lines"
        assert filter.subfilter is None

        filter = JsonApiQueryModel.model_validate({"filter": "has(lines, equals(id,'1'))"}).filters[0]
        assert filter.oper == Oper.HAS
        assert filter.attr == "lines"
        assert filter.subfilter.oper == Oper.EQUALS
        assert filter.subfilter.attr == "id"

    @pytest.mark.parametrize(
        "query_filter",
        ["has()", "has('lines')", "has(lines,'a')", "has(lines,equals(id,'1'),equals(id,'2'))"],
    )
    def test_parse_wrong_has(self, query_filter):
        with pytest.raises(UnprocessableEntity):
            JsonApiQueryModel.model_validate({"filter": query_filter})

    def test_match_has_on_values(self):
        class TaggedModel(JsonApiBaseModel):
            jsonapi_type: t.ClassVar[str] = "tagged"
            tags: list[str] = Field(default_factory=lambda: ["a", "b"])

        query = JsonApiQueryModel.model_validate({"filter": "has(tags)"})
        assert query.match(TaggedModel()) is True

        query = JsonApiQueryModel.model_validate({"filter": "has(tags,equals(name,'a'))"})
        with pytest.raises(BadRequest):
            query.match(TaggedModel())

    @pytest.mark.parametrize(
        "query_filter",
        [
            "equals(unknown,'a')",
            "equals(main.unknown,'a')",
            "equals(lines.id,'1')",  # to-many relationship must be filtered with has
            "equals(match,'a')",  # methods are not attributes
            "equals(model_config.frozen,true)",  # pydantic internals are not attributes
            "equals(__class__,'a')",
            "lessThan(name,5)",
            "startsWith(notice,'1')",
            "has(unknown)",
            "lessThan(notice,unknown)",
            "greaterThan(created,'not a date')",
        ],
    )
    def test_match_wrong_attribute(self, query_filter):
        query = JsonApiQueryModel.model_validate({"filter": query_filter})
        with pytest.raises(BadRequest):
            query.match(MatchedModel())

    def test_model_match_raises_filter_error(self):
        with pytest.raises(FilterError):
            MatchedModel().match(Oper.EQUALS, "unknown", "a")
        with pytest.raises(FilterError):
            MatchedModel().match(Oper.LESS_THAN, "name", 5)

    def test_match_all_filters(self):
        query = JsonApiQueryModel.model_validate({"filter": ["equals(name,'Brian')", "equals(notice,11)"]})
        assert query.match(MatchedModel()) is False
