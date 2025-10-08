import typing as t

import requests
from pydantic import AnyUrl, BaseModel

from .jsonapi import Error, JsonApi, Link, Resource


class __TopLevel(BaseModel):
    errors: list[Error] | None = None
    meta: dict | None = None
    jsonapi: JsonApi | None = None
    links: dict[str, AnyUrl | Link | None] | None = None
    included: list[Resource] | None = None


#
# Duck typing TopLevel classes
#


class TopLevelSingle(__TopLevel):
    data: Resource


class TopLevelArray(__TopLevel):
    data: list[Resource]


class JapydClient:

    def __init__(self, url: str):
        self.url = url.rstrip("/")

    @t.overload
    def __call__(self, method: str, entry: str, /, id: str, **kwargs) -> TopLevelSingle: ...

    @t.overload
    def __call__(self, method: str, entry: str, /, **kwargs) -> TopLevelArray: ...

    def __call__(self, method: str, entry: str, /, id=None, **kwargs):
        if id is not None:
            resp = requests.request(method, f"{self.url.rstrip('/')}/{entry.strip('/')}/{id}", **kwargs)
            return TopLevelSingle.model_validate(resp.json())

        resp = requests.request(method, f"{self.url.rstrip('/')}/{entry}/{id}", **kwargs)
        return TopLevelArray.model_validate(resp.json())
