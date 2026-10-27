import json

import pytest

from japyd import (
    Relationship,
    Resource,
    ResourceIdentifier,
    SingleResourceTopLevel,
    MultiResourcesTopLevel,
    TopLevel,
    extract_from_resource_identifier,
    extract_relationship,
    flatten_resource,
)


class TestJsonApi:

    def test_toplevel(self, article):
        toplevel = TopLevel(**article)
        author = extract_relationship(toplevel, "author")
        assert isinstance(author, Resource)
        assert author.attributes["firstName"] == "Dan"
        country = extract_relationship(toplevel, "author.country")
        assert isinstance(country, Resource)
        assert country.attributes["name"] == "France"

        assert isinstance(toplevel.data, Resource)
        assert toplevel.data.relationships is not None
        author = extract_relationship(toplevel, toplevel.data.relationships["author"])
        assert isinstance(author, Resource)
        assert author.attributes["firstName"] == "Dan"

    def test_extraction(self, article):
        toplevel = TopLevel(**article)
        author = extract_relationship(toplevel, toplevel.data.relationships["author"])
        assert author.relationships is not None
        country = extract_relationship(toplevel, author.relationships["country"])
        assert isinstance(country, Resource)
        assert country.attributes["name"] == "France"

        resources = extract_relationship(toplevel, "comments")
        assert isinstance(resources, list)
        assert len(resources) == 2
        authors = extract_relationship(toplevel, "comments.author")
        assert isinstance(authors, list)
        assert len(authors) == 2
        country = extract_relationship(toplevel, "comments.author.country")
        assert isinstance(country, list)
        assert len(country) == 1

    def test_str(self, article):
        toplevel = json.dumps(article)
        author = extract_relationship(toplevel, "author")
        assert isinstance(author, dict)
        assert author["attributes"]["firstName"] == "Dan"
        country = extract_relationship(toplevel, "author.country")
        assert isinstance(country, dict)
        assert country["attributes"]["name"] == "France"

    def test_attributes(self, article):
        toplevel = TopLevel(**article)
        author = extract_relationship(toplevel, "author")
        assert isinstance(author, Resource)
        assert author.attributes["firstName"] == "Dan"

    def test_relationship(self, article):
        toplevel = TopLevel(**article)
        assert toplevel.errors is None
        assert isinstance(toplevel.data, Resource)
        attrs = toplevel.data.attributes
        assert attrs["title"] == "Rails is Omakase"

        assert toplevel.data.relationships is not None
        author_rel = toplevel.data.relationships["author"]
        author = extract_relationship(toplevel, author_rel)
        assert isinstance(author, Resource)
        assert author.attributes["firstName"] == "Dan"

        comments_rel: Relationship = toplevel.data.relationships["comments"]
        assert isinstance(comments_rel.data, list)
        assert len(comments_rel.data) == 2

        resources = extract_relationship(toplevel, comments_rel)
        assert isinstance(resources, list)
        assert len(resources) == 2
        resource: Resource = [r for r in resources if r.id == "12"][0]
        assert resource.id == "12"
        assert resource.type == "comments"
        assert resource.attributes["body"] == "I like XML better"

        comment: ResourceIdentifier = [c for c in comments_rel.data if c.id == "12"][0]
        assert comment.id == "12"
        assert comment.type == "comments"
        resource = extract_from_resource_identifier(toplevel, comment)
        assert resource.attributes["body"] == "I like XML better"

        assert resource.relationships is not None
        author = extract_relationship(toplevel, resource.relationships["author"])
        assert isinstance(author, Resource)
        assert author.attributes["firstName"] == "Dan"

    def test_relationship_from_path(self, article):
        toplevel = TopLevel(**article)
        assert toplevel.errors is None
        assert isinstance(toplevel.data, Resource)
        attrs = toplevel.data.attributes
        assert attrs["title"] == "Rails is Omakase"

        author = extract_relationship(toplevel, "author")
        assert isinstance(author, Resource)
        assert author.attributes["firstName"] == "Dan"
        country = extract_relationship(toplevel, "author.country")
        assert isinstance(country, Resource)
        assert country.attributes["name"] == "France"

        resources = extract_relationship(toplevel, "comments")
        assert isinstance(resources, list)
        assert len(resources) == 2
        resource: Resource = [r for r in resources if r.id == "12"][0]
        assert resource.id == "12"
        assert resource.type == "comments"
        assert resource.attributes["body"] == "I like XML better"

    def test_single(self, article):
        toplevel = SingleResourceTopLevel(**article)
        assert isinstance(toplevel.data, Resource)
        assert toplevel.meta is not None
        assert toplevel.meta["count"] == 1

    def test_multi(self, articles):
        toplevel = MultiResourcesTopLevel(**articles)
        assert toplevel.meta is not None
        assert toplevel.meta["count"] == len(toplevel.data)

        authors = extract_relationship(toplevel, "author")
        assert isinstance(authors, list)
        assert len(authors) == 2


class TestConsistency:

    def test_null_to_one_relationship(self):
        doc = {
            "data": {"type": "article", "id": "1", "relationships": {"author": {"data": None}}},
            "included": [],
        }
        toplevel = SingleResourceTopLevel.model_validate(doc)
        assert toplevel.data is not None
        assert toplevel.data.relationships is not None
        assert toplevel.data.relationships["author"].data is None
        assert extract_relationship(toplevel, "author") is None
        assert extract_relationship(doc, "author") is None
        assert flatten_resource(toplevel, pattern="author")["author"] is None

    def test_relationship_data_states(self):
        # data null (empty to-one), [] (empty to-many) and absent (only links) are kept distinct
        relationships = {
            "author": {"data": None},
            "comments": {"data": []},
            "editor": {"links": {"related": "http://example.com/articles/1/editor"}},
        }
        doc = {"data": {"type": "article", "id": "1", "relationships": relationships}}
        toplevel = SingleResourceTopLevel.model_validate(doc)
        assert toplevel.data is not None and toplevel.data.relationships is not None
        editor = toplevel.data.relationships["editor"]
        assert not editor.has_data
        assert toplevel.data.relationships["author"].has_data
        assert toplevel.data.relationships["comments"].has_data

        dumped = toplevel.model_dump(mode="json", exclude_none=True)["data"]["relationships"]
        assert dumped == relationships
        assert "data" not in toplevel.model_dump(mode="json")["data"]["relationships"]["editor"]

        assert extract_relationship(toplevel, "author") is None
        assert extract_relationship(toplevel, "comments") == []
        with pytest.raises(AttributeError, match="No resource linkage in relationship editor"):
            extract_relationship(toplevel, "editor")
        with pytest.raises(AttributeError, match="No resource linkage"):
            extract_relationship(toplevel, editor)

        with pytest.raises(AttributeError, match="No resource linkage"):
            flatten_resource(toplevel, pattern="editor")
        assert "editor" not in flatten_resource(toplevel, pattern="editor?")
        with pytest.raises(AttributeError, match="No resource linkage"):
            flatten_resource(toplevel, pattern="editor.country")

    def test_relationship_constructed(self):
        assert Relationship(data=None).model_dump(exclude_none=True) == {"data": None}
        assert Relationship(data=[]).model_dump(exclude_none=True) == {"data": []}
        assert Relationship(meta={"count": 3}).model_dump(exclude_none=True) == {"meta": {"count": 3}}

    def test_extract_list_from_dict(self, articles):
        authors = extract_relationship(articles, "author")
        assert isinstance(authors, list)
        assert all(isinstance(a, dict) for a in authors)

    def test_flatten_empty_list(self):
        assert flatten_resource([]) == []
        assert flatten_resource(MultiResourcesTopLevel()) == []

    def test_resource_without_id(self):
        res = Resource.model_validate({"type": "article", "lid": "new-1", "attributes": {"title": "t"}})
        assert res.id == ""
        assert res.lid == "new-1"

    def test_error_without_code(self):
        toplevel, code, _ = TopLevel.error(title="t", detail="d")
        assert code == 500
        assert toplevel.errors is not None
        assert toplevel.errors[0].id is None
        assert toplevel.errors[0].status == "500"
