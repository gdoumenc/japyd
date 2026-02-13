from japyd.dotnet import JsonApiQueryModel
from japyd.models import JsonApiBaseModel


class SimpleBaseModel(JsonApiBaseModel):
    test: str


class ContentObject(JsonApiBaseModel):
    jsonapi_type = "content"
    id: str

    class SameObject(JsonApiBaseModel):
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
