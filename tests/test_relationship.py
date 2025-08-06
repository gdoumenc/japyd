from japyd.jsonapi import Relationship
from japyd.jsonapi import Resource
from japyd.jsonapi import ResourceIdentifier
from japyd.jsonapi import TopLevel
from japyd.utils import extract_from_resource_identifier
from japyd.utils import extract_relationship


class TestRelationship:

    def test_article(self, article):
        toplevel = TopLevel(**article)
        author = extract_relationship(toplevel, "author")
        assert author.attributes['firstName'] == 'Dan'
        country = extract_relationship(toplevel, "author.country")
        assert country.attributes['name'] == 'France'

        author = extract_relationship(toplevel, toplevel.data.relationships['author'])
        assert author.attributes['firstName'] == 'Dan'
        country = extract_relationship(toplevel, author.relationships['country'])
        assert country.attributes['name'] == 'France'

        resources = extract_relationship(toplevel, 'comments')
        assert len(resources) == 2
        authors = extract_relationship(toplevel, 'comments.author')
        assert len(authors) == 2
        peoples = extract_relationship(toplevel, 'comments.author.country')
        assert len(peoples) == 1

    def test_attributes(self, article):
        toplevel = TopLevel(**article)
        author = extract_relationship(toplevel, "author")
        assert author.attributes['firstName'] == 'Dan'

    def test_relationship(self, article):
        toplevel = TopLevel(**article)
        assert toplevel.errors is None
        attrs = toplevel.data.attributes
        assert attrs['title'] == 'Rails is Omakase'

        author_rel = toplevel.data.relationships['author']
        author = extract_relationship(toplevel, author_rel)
        assert author.attributes['firstName'] == 'Dan'

        comments_rel: Relationship = toplevel.data.relationships['comments']
        assert len(comments_rel.data) == 2

        resources = extract_relationship(toplevel, comments_rel)
        assert len(resources) == 2
        resource: Resource = [r for r in resources if r.id == '12'][0]
        assert resource.id == '12'
        assert resource.type == 'comments'
        assert resource.attributes["body"] == "I like XML better"

        comment: ResourceIdentifier = [c for c in comments_rel.data if c.id == '12'][0]
        assert comment.id == '12'
        assert comment.type == 'comments'
        resource = extract_from_resource_identifier(toplevel, comment)
        assert resource.attributes["body"] == "I like XML better"

        author = extract_relationship(toplevel, resource.relationships['author'])
        assert author.attributes['firstName'] == 'Dan'

    def test_relationship_from_path(self, article):
        toplevel = TopLevel(**article)
        assert toplevel.errors is None
        attrs = toplevel.data.attributes
        assert attrs['title'] == 'Rails is Omakase'

        author = extract_relationship(toplevel, 'author')
        assert author.attributes['firstName'] == 'Dan'
        country = extract_relationship(toplevel, 'author.country')
        assert country.attributes['name'] == 'France'

        resources = extract_relationship(toplevel, 'comments')
        assert len(resources) == 2
        resource: Resource = [r for r in resources if r.id == '12'][0]
        assert resource.id == '12'
        assert resource.type == 'comments'
        assert resource.attributes["body"] == "I like XML better"

    def test_articles(self, articles):
        toplevel = TopLevel(**articles)
        authors = extract_relationship(toplevel, "author")
        assert len(authors) == 2
