from japyd.dotnet import JsonApiQueryModel
from japyd.models import JsonApiBaseModel


class TestIssue2:

    class ContentObject(JsonApiBaseModel):
        jsonapi_type = "content"
        id: str

        class SameObject(JsonApiBaseModel):
            id: str
            jsonapi_type = "same"

        same1: SameObject
        same2: SameObject

    import pytest

    @pytest.mark.wip
    def test_not_included_twice(self):
        query = JsonApiQueryModel(include={"same1", " same2"})
        same = TestIssue2.ContentObject.SameObject(id="same")
        content = TestIssue2.ContentObject(id="object1", same1=same, same2=same)
        included = []
        r = content.as_resource(included, query)
        assert len(included) == 1
