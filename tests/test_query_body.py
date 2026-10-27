import pytest
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, InternalServerError, UnprocessableEntity

from japyd import (
    JsonApiBaseModel,
    JsonApiQueryModel,
    MultiBodyModel,
    MultiResourcesTopLevel,
    Resource,
    ResourceIdentifier,
    SingleBodyModel,
    SingleResourceTopLevel,
    TopLevel,
    extract_relationship,
)


class SimpleBaseModel(JsonApiBaseModel):
    test: str = "test"


class ContentObject(JsonApiBaseModel):
    jsonapi_type = "content"
    id: str

    class SameObject(SimpleBaseModel):
        id: str
        jsonapi_type = "same"

    same1: SameObject
    same2: SameObject


class TestQuery:

    def test_fields(self):
        query = JsonApiQueryModel(fields={"content": ["same1", " same2"]})
        fields = query.get_fields("content")
        assert fields is not None
        assert len(fields) == 2
        assert "same2" in fields

    def test_include_resource_identifier(self):
        class Holder(JsonApiBaseModel):
            jsonapi_type = "holder"
            id: str
            same: ContentObject.SameObject | ResourceIdentifier

        query = JsonApiQueryModel(include={"same"})
        included: list[Resource] = []
        r = Holder(id="1", same=ResourceIdentifier(type="same", id="2")).as_resource(included, query)
        assert r.relationships is not None
        assert r.relationships["same"].data == ResourceIdentifier(type="same", id="2")
        assert included == []

    def test_not_included_twice(self):
        query = JsonApiQueryModel(include={"same1", " same2"})
        same = ContentObject.SameObject(id="same")
        content = ContentObject(id="object1", same1=same, same2=same)
        included = []
        r = content.as_resource(included, query)
        assert len(included) == 1

    def test_one(self):
        query = JsonApiQueryModel()
        simple = SimpleBaseModel(test="test")
        r = query.one(simple)
        assert r.data is not None
        assert r.meta is not None
        assert r.meta["count"] == 1
        assert "test" in r.data.attributes

        r = query.one({"test": "test"})
        assert r.data is not None
        assert r.meta is not None
        assert r.meta["count"] == 1
        assert "test" in r.data.attributes

        r = query.one({"id": "1", "test": "test"})
        assert r.data is not None
        assert r.meta is not None
        assert r.meta["count"] == 1
        assert r.data.id == "1"
        assert "test" in r.data.attributes

    def test_one_or_none(self):
        query = JsonApiQueryModel()
        r = query.one_or_none(None)
        assert r.data is None
        assert r.meta is not None
        assert r.meta["count"] == 0
        # The null primary data is kept, even with exclude_none
        assert r.model_dump(exclude_none=True) == {"data": None, "meta": {"count": 0}}
        assert SingleResourceTopLevel(errors=[{"status": "404"}]).model_dump(exclude_none=True) == {
            "errors": [{"status": "404"}],
        }

    @pytest.mark.parametrize("toplevel_class", [TopLevel, SingleResourceTopLevel, MultiResourcesTopLevel])
    def test_data_and_errors(self, toplevel_class):
        # The members data and errors must not coexist, an error document has no data, included or count
        top = toplevel_class.model_validate({"errors": [{"status": "404"}]})
        assert top.model_dump() == {"errors": [top.errors[0].model_dump()], "meta": None, "jsonapi": None, "links": None}
        assert top.model_dump(exclude_none=True) == {"errors": [{"status": "404"}]}

        resource = {"type": "a", "id": "1"}
        data = resource if toplevel_class is SingleResourceTopLevel else [resource]
        with pytest.raises(ValidationError, match="MUST NOT coexist"):
            toplevel_class.model_validate({"data": data, "errors": [{"status": "404"}]})

    def test_pagination(self):
        query = JsonApiQueryModel()
        assert query.pagination is not None
        assert query.pagination.number == 1
        assert query.pagination.size == 20

        query = JsonApiQueryModel(pagination={"number": 2})
        assert query.pagination is not None
        assert query.pagination.number == 2
        assert query.pagination.size == 20

        query = JsonApiQueryModel(pagination={"size": 50})
        assert query.pagination is not None
        assert query.pagination.number == 1
        assert query.pagination.size == 50

    def test_paginate(self):
        values = [SimpleBaseModel(test=str(i)) for i in range(1, 21)]

        query = JsonApiQueryModel()
        toplevel = query.paginate(values)
        assert toplevel.meta["count"] == 20
        assert toplevel.data[0].attributes["test"] == "1"
        assert toplevel.data[-1].attributes["test"] == "20"
        assert toplevel.meta["pagination"]["page"] == 1
        assert not toplevel.meta["pagination"]["has_prev"]
        assert not toplevel.meta["pagination"]["has_next"]

        query = JsonApiQueryModel(pagination={"size": 10})
        toplevel = query.paginate(values)
        assert toplevel.meta["count"] == 20  # total number of values, not the page size
        assert toplevel.data[0].attributes["test"] == "1"
        assert toplevel.data[-1].attributes["test"] == "10"
        assert not toplevel.meta["pagination"]["has_prev"]
        assert toplevel.meta["pagination"]["has_next"]

        query = JsonApiQueryModel(pagination={"number": 2, "size": 10})
        toplevel = query.paginate(values)
        assert toplevel.meta["count"] == 20
        assert toplevel.data[0].attributes["test"] == "11"
        assert toplevel.data[-1].attributes["test"] == "20"
        assert toplevel.meta["pagination"]["page"] == 2
        assert toplevel.meta["pagination"]["has_prev"]
        assert not toplevel.meta["pagination"]["has_next"]

        query = JsonApiQueryModel(pagination={"number": 1})
        toplevel = query.paginate(values, full_list=False)
        assert "count" not in toplevel.meta
        assert toplevel.data[0].attributes["test"] == "1"
        assert toplevel.data[-1].attributes["test"] == "20"
        assert not toplevel.meta["pagination"]["has_prev"]
        assert toplevel.meta["pagination"]["has_next"]

        query = JsonApiQueryModel(pagination={"number": 2})
        toplevel = query.paginate(values, full_list=False)
        assert "count" not in toplevel.meta
        assert toplevel.data[0].attributes["test"] == "1"
        assert toplevel.data[-1].attributes["test"] == "20"
        assert toplevel.meta["pagination"]["page"] == 2
        assert toplevel.meta["pagination"]["has_prev"]
        assert toplevel.meta["pagination"]["has_next"]

        values = [SimpleBaseModel(test=str(i)) for i in range(1, 11)]

        query = JsonApiQueryModel()
        toplevel = query.paginate(values, full_list=False)
        assert toplevel.data[0].attributes["test"] == "1"
        assert toplevel.data[-1].attributes["test"] == "10"
        assert not toplevel.meta["pagination"]["has_prev"]
        assert not toplevel.meta["pagination"]["has_next"]

        query = JsonApiQueryModel(pagination={"number": 2})
        toplevel = query.paginate(values, full_list=False)
        assert toplevel.data[0].attributes["test"] == "1"
        assert toplevel.data[-1].attributes["test"] == "10"
        assert toplevel.meta["pagination"]["has_prev"]
        assert not toplevel.meta["pagination"]["has_next"]

        query = JsonApiQueryModel(pagination={"size": 5})
        with pytest.raises(InternalServerError):
            query.paginate(values, full_list=False)

    def test_flatten(self):

        query = JsonApiQueryModel()
        r = query.one_or_none(None)
        assert r.data is None
        assert r.meta is not None
        assert r.meta["count"] == 0

        same1 = ContentObject.SameObject(id="same1", test="test1")
        same2 = ContentObject.SameObject(id="same2", test="test2")
        content = ContentObject(id="object1", same1=same1, same2=same2)

        query = JsonApiQueryModel()
        r = query.one(content)
        assert r.data is not None
        assert r.meta is not None
        assert r.meta["count"] == 1
        assert len(r.data.attributes.keys()) == 0

        query = JsonApiQueryModel(include=["same1"], flatten="same1")
        r = query.one(content)
        assert r.data is not None
        assert r.meta is not None
        assert r.meta["count"] == 1
        assert len(r.data.attributes) == 1
        assert "same1" in r.data.attributes

        query = JsonApiQueryModel(include=["same1, same2"], flatten="same1")
        r = query.one(content)
        assert r.data is not None
        assert r.meta is not None
        assert r.meta["count"] == 1
        assert len(r.data.attributes) == 1
        assert "same1" in r.data.attributes

        query = JsonApiQueryModel(include=["same1, same2"], flatten="same1,same2")
        r = query.one(content)
        assert r.data is not None
        assert r.meta is not None
        assert r.meta["count"] == 1
        assert len(r.data.attributes) == 2
        assert "same1" in r.data.attributes
        assert "same2" in r.data.attributes

        query = JsonApiQueryModel(include=["same1, same2"], flatten="same1,same2")
        r = query.paginate([content])
        assert r.data is not None
        assert r.meta is not None
        assert r.meta["count"] == 1
        assert len(r.data[0].attributes) == 2
        assert "same1" in r.data[0].attributes
        assert "same2" in r.data[0].attributes

    def test_flatten_without_include(self):
        same1 = ContentObject.SameObject(id="same1", test="test1")
        same2 = ContentObject.SameObject(id="same2", test="test2")
        content = ContentObject(id="object1", same1=same1, same2=same2)

        query = JsonApiQueryModel(flatten="same1,same2")
        assert query.include == {"same1", "same2"}
        r = query.one(content)
        assert r.data is not None
        assert r.data.attributes["same1"]["test"] == "test1"
        assert r.data.attributes["same2"]["test"] == "test2"
        assert r.included is None

        r = query.paginate([content])
        assert r.data[0].attributes["same1"]["test"] == "test1"
        assert r.included is None

    def test_flatten_removed_from_included(self):
        same1 = ContentObject.SameObject(id="same1", test="test1")
        same2 = ContentObject.SameObject(id="same2", test="test2")
        content = ContentObject(id="object1", same1=same1, same2=same2)

        query = JsonApiQueryModel(include=["same2"], flatten="same1")
        r = query.one(content)
        assert r.data is not None
        assert r.data.attributes["same1"]["test"] == "test1"
        assert [(i.type, i.id) for i in r.included] == [(same2.jsonapi_type, "same2")]

        assert r.data.relationships is not None
        assert "same1" not in r.data.relationships
        assert r.data.relationships["same2"].data.id == "same2"

        r = query.paginate([content])
        assert [(i.type, i.id) for i in r.included] == [(same2.jsonapi_type, "same2")]
        assert r.data[0].relationships is not None
        assert "same1" not in r.data[0].relationships
        assert r.data[0].relationships["same2"].data.id == "same2"

    def test_include_strip(self):
        assert JsonApiQueryModel(include=[" same1 , same2,,"]).include == {"same1", "same2"}
        assert JsonApiQueryModel(include={" same1"}).include == {"same1"}

    def test_flatten_include_paths(self):
        query = JsonApiQueryModel(include=["tenant"], flatten="order.lines.product|product_page?,customer?")
        assert query.include == {
            "tenant",
            "order",
            "order.lines",
            "order.lines.product",
            "order.lines.product_page",
            "customer",
        }


class TestBody:

    def test_body(self, article):
        body = SingleBodyModel.model_validate(article)
        assert body is not None
        author = extract_relationship(body, "author")
        assert isinstance(author, Resource)
        assert author.attributes["firstName"] == "Dan"

        assert len(body.included) == 5
        assert body.included[0].attributes["firstName"] == "Alice"

    def test_toplevel(self, article, articles):
        body = SingleBodyModel.model_validate(article)
        assert body is not None
        toplevel = body.toplevel
        assert isinstance(toplevel, SingleResourceTopLevel)
        body = MultiBodyModel.model_validate(articles)
        assert body is not None
        toplevel = body.toplevel
        assert isinstance(toplevel, MultiResourcesTopLevel)
        
        assert len(body.included) == 5
        assert body.included[0].attributes["firstName"] == "Alice"


class SortedModel(JsonApiBaseModel):
    jsonapi_type = "sorted"
    id: str
    name: str
    rank: int | None = None


class TestFixes:

    def test_one_does_not_change_the_value(self):
        value = {"id": "1", "type": "t", "x": 1}
        r = JsonApiQueryModel().one(value)
        assert r.data is not None
        assert r.data.id == "1"
        assert r.data.attributes == {"x": 1}
        assert value == {"id": "1", "type": "t", "x": 1}

    @pytest.mark.parametrize("pagination", [{"number": 0}, {"size": 0}, {"number": -1, "size": -5}])
    def test_wrong_pagination(self, pagination):
        with pytest.raises(ValidationError):
            JsonApiQueryModel(pagination=pagination)

    def test_pagination_from_query_args(self):
        query = JsonApiQueryModel.model_validate({"page[number]": "2", "page[size]": "5"})
        assert query.pagination.number == 2
        assert query.pagination.size == 5

        with pytest.raises(ValidationError):
            JsonApiQueryModel.model_validate({"page[number]": "x"})

    def test_body_without_id(self):
        body = SingleBodyModel.model_validate({"data": {"type": "content", "attributes": {"a": 1}}})
        assert body.data is not None
        assert body.data.id == ""
        assert body.attributes == {"a": 1}

    def test_sort(self):
        values = [
            SortedModel(id="1", name="b", rank=2),
            SortedModel(id="2", name="a", rank=None),
            SortedModel(id="3", name="c", rank=2),
            SortedModel(id="4", name="a", rank=1),
        ]
        assert [v.id for v in JsonApiQueryModel().sort_values(values)] == ["1", "2", "3", "4"]
        assert [v.id for v in JsonApiQueryModel(sort="name").sort_values(values)] == ["2", "4", "1", "3"]
        assert [v.id for v in JsonApiQueryModel(sort="-name").sort_values(values)] == ["3", "1", "2", "4"]
        # Null values are lower than any other value
        assert [v.id for v in JsonApiQueryModel(sort="rank,-name").sort_values(values)] == ["2", "4", "3", "1"]
        assert [v.id for v in JsonApiQueryModel(sort="-rank,name").sort_values(values)] == ["1", "3", "4", "2"]

    def test_select(self):
        values = [SortedModel(id=str(i), name=n) for i, n in enumerate("cab")]
        query = JsonApiQueryModel(sort="name", filter="not(equals(name,'a'))")
        assert [v.name for v in query.select(values)] == ["b", "c"]

    @pytest.mark.parametrize("sort", ["unknown", "-unknown", "model_config"])
    def test_sort_unknown_attribute(self, sort):
        with pytest.raises(BadRequest):
            JsonApiQueryModel(sort=sort).sort_values([SortedModel(id="1", name="a")])

    @pytest.mark.parametrize("sort", ["name,", "-", ",name"])
    def test_wrong_sort(self, sort):
        with pytest.raises(UnprocessableEntity):
            JsonApiQueryModel(sort=sort).sort_values([SortedModel(id="1", name="a")])

    def test_empty_relationships_and_included_omitted(self):
        r = JsonApiQueryModel().one(SortedModel(id="1", name="a"))
        assert r.data is not None
        assert r.data.relationships is None
        assert r.included is None
        assert "included" not in r.model_dump(exclude_none=True)

        r = JsonApiQueryModel().paginate([SortedModel(id="1", name="a")])
        assert r.data[0].relationships is None
        assert r.included is None
