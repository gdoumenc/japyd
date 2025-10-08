import pytest

data = {
    "data": {
        "type": "article",
        "id": "1",
        "attributes": {
            "title": "Rails is Omakase",
        },
        "relationships": {
            "author": {"data": {"type": "people", "id": "9"}},
            "comments": {"data": [{"type": "comments", "id": "5"}, {"type": "comments", "id": "12"}]},
        },
    },
    "included": [
        {
            "type": "people",
            "id": "2",
            "attributes": {
                "firstName": "Alice",
            },
            "relationships": {"country": {"data": {"type": "country", "id": "1"}}},
        },
        {
            "type": "people",
            "id": "9",
            "attributes": {
                "firstName": "Dan",
            },
            "relationships": {"country": {"data": {"type": "country", "id": "1"}}},
        },
        {
            "type": "comments",
            "id": "5",
            "attributes": {"body": "First!"},
            "relationships": {"author": {"data": {"type": "people", "id": "2"}}},
        },
        {
            "type": "comments",
            "id": "12",
            "attributes": {"body": "I like XML better"},
            "relationships": {"author": {"data": {"type": "people", "id": "9"}}},
        },
        {
            "type": "country",
            "id": "1",
            "attributes": {"name": "France"},
        },
    ],
}


@pytest.fixture
def article():
    return data


@pytest.fixture
def articles():
    added = {
        "type": "article",
        "id": "2",
        "attributes": {
            "title": "New article",
        },
        "relationships": {"author": {"data": {"type": "people", "id": "2"}}, "comments": {"data": []}},
    }
    data_list = data
    data_list["data"] = [data_list["data"], added]
    return data_list
