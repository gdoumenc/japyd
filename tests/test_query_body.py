import pytest
from werkzeug.exceptions import InternalServerError

from japyd import (
    JsonApiBaseModel,
    JsonApiQueryModel,
    MultiBodyModel,
    MultiResourcesTopLevel,
    Resource,
    SingleBodyModel,
    SingleResourceTopLevel,
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
        assert toplevel.meta["count"] == 10
        assert toplevel.data[0].attributes["test"] == "1"
        assert toplevel.data[-1].attributes["test"] == "10"
        assert not toplevel.meta["pagination"]["has_prev"]
        assert toplevel.meta["pagination"]["has_next"]

        query = JsonApiQueryModel(pagination={"number": 2, "size": 10})
        toplevel = query.paginate(values)
        assert toplevel.meta["count"] == 10
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
