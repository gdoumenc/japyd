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

    def test_pagination(self):
        query = JsonApiQueryModel()
        assert query.pagination is not None
        assert query.pagination.number == 1
        assert query.pagination.size == 20
        
        query = JsonApiQueryModel(pagination={"number":2})
        assert query.pagination is not None
        assert query.pagination.number == 2
        assert query.pagination.size == 20
        
        query = JsonApiQueryModel(pagination={"size":50})
        assert query.pagination is not None
        assert query.pagination.number == 1
        assert query.pagination.size == 50

class TestBody:

    def test_body(self, article):
        body = SingleBodyModel.model_validate(article)
        assert body is not None
        author = extract_relationship(body, "author")
        assert isinstance(author, Resource)
        assert author.attributes["firstName"] == "Dan"

    def test_toplevel(self, article, articles):
        body = SingleBodyModel.model_validate(article)
        assert body is not None
        toplevel = body.toplevel
        assert isinstance(toplevel, SingleResourceTopLevel)
        body = MultiBodyModel.model_validate(articles)
        assert body is not None
        toplevel = body.toplevel
        assert isinstance(toplevel, MultiResourcesTopLevel)
