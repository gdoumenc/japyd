import json

import pytest

from japyd.jsonapi import Relationship, Resource, ResourceIdentifier, TopLevel
from japyd.utils import extract_from_resource_identifier, extract_relationship


class TestExtraction:

    def test_article(self, article):
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
        peoples = extract_relationship(toplevel, "comments.author.country")
        assert isinstance(peoples, list)
        assert len(peoples) == 1

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

    def test_articles(self, articles):
        toplevel = TopLevel(**articles)
        authors = extract_relationship(toplevel, "author")
        assert isinstance(authors, list)
        assert len(authors) == 2
