import typing as t

import requests

from .jsonapi import MultiResourcesTopLevel, SingleResourceTopLevel


class JapydClient:

    def __init__(self, url: str):
        self.url = url.rstrip("/")

    @t.overload
    def __call__(self, method: str, entry: str, /, id: str, **kwargs) -> SingleResourceTopLevel: ...

    @t.overload
    def __call__(self, method: str, entry: str, /, **kwargs) -> MultiResourcesTopLevel: ...

    def __call__(self, method: str, entry: str, /, id=None, **kwargs):
        if id is not None:
            resp = requests.request(method, f"{self.url.rstrip('/')}/{entry.strip('/')}/{id}", **kwargs)
            return SingleResourceTopLevel.model_validate(resp.json())

        resp = requests.request(method, f"{self.url.rstrip('/')}/{entry}/{id}", **kwargs)
        return MultiResourcesTopLevel.model_validate(resp.json())
