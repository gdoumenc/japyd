from __future__ import annotations

import typing as t

from flask import Flask, Response, make_response, request
from pydantic import AnyUrl, BaseModel, ConfigDict, Field
from werkzeug.exceptions import HTTPException


class Link(BaseModel):
    href: str
    meta: dict | None = None


class JsonApi(BaseModel):
    version: str | None = None
    meta: dict | None = None


class Error(BaseModel):
    id: str | None = None
    status: str | None = None
    code: str | None = None
    title: str | None = None
    detail: str | None = None
    source: dict | None = None
    meta: dict | None = None


class ResourceIdentifier(BaseModel):
    type: str
    id: str
    meta: dict | None = None


class Relationship(BaseModel):
    data: ResourceIdentifier | list[ResourceIdentifier] = Field(default_factory=list)
    links: dict[str, AnyUrl | Link | None] | None = None
    meta: dict | None = None


class Resource(BaseModel):
    type: str
    id: str
    attributes: dict = Field(default_factory=dict)
    relationships: dict[str, Relationship] | None = None
    links: dict[str, AnyUrl | Link | None] | None = None
    meta: dict | None = None

    def flatten(self):
        return {"id": self.id, "type": self.type, **self.attributes}


class TopLevel(BaseModel):
    data: Resource | list[Resource] | None = None
    errors: list[Error] | None = None
    meta: dict | None = None
    jsonapi: JsonApi | None = None
    links: dict[str, AnyUrl | Link | None] | None = None
    included: list[Resource] | None = None

    @classmethod
    def http_error(cls, e: HTTPException) -> tuple[TopLevel, int, dict]:
        errors = [Error(id=str(e.code), title=e.name, detail=e.description, status=str(e.code))]
        return TopLevel(errors=errors), e.code or 500, {"Content-Type": "application/vnd.api+json"}

    @classmethod
    def error(
        cls, *, code: int | None = None, title: str, detail: str, status: str | None = None
    ) -> tuple[TopLevel, int, dict]:
        errors = [Error(id=str(code), title=title, detail=detail, status=status or str(code))]
        return TopLevel(errors=errors), code or 500, {"Content-Type": "application/vnd.api+json"}


class SingleResourceTopLevel(TopLevel):
    data: Resource | None = None  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    def empty(cls, meta=None, jsonapi=None, links=None) -> SingleResourceTopLevel:
        if meta is None:
            meta = {"count": 0}
        return cls(data=None, meta=meta, jsonapi=jsonapi, links=links)


class MultiResourcesTopLevel(TopLevel):
    data: list[Resource] = Field(default_factory=list)  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    def empty(cls, meta=None, jsonapi=None, links=None) -> MultiResourcesTopLevel:
        if meta is None:
            meta = {"count": 0}
        return cls(data=[], meta=meta, jsonapi=jsonapi, links=links)


class _JsonApiBodyModel(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    included: list[Resource] | None = Field(default_factory=list)
    meta: dict | None = None
    debug: bool = False


class JsonApiBodyModel(_JsonApiBodyModel):
    data: Resource | list[Resource] | None = None

    @property
    def attributes(self) -> dict[str, t.Any] | list[dict[str, t.Any]]:
        if isinstance(self.data, list):
            return [d.attributes for d in self.data]
        return self.data.attributes if self.data else {}


class SingleBodyModel(_JsonApiBodyModel):
    data: Resource | None = None

    @property
    def attributes(self) -> dict[str, t.Any]:
        return self.data.attributes if self.data else {}


class MultiBodyModel(_JsonApiBodyModel):
    data: list[Resource] = Field(default_factory=list)

    @property
    def attributes(self) -> list[dict[str, t.Any]]:
        return [d.attributes for d in self.data]


class JsonApiApp:
    """Flask's extension implementing JSON:API specification."""

    def __init__(self, app: Flask | None = None):
        self.app: Flask | None = None

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """
        - Adds exception handler to transform any exception to TopLevel error.
        - Forces response content type to JSON:API.
        """
        self.app = app

        handle_exception = app.error_handler_spec[None][None].get(Exception)
        app.after_request(self._change_content_type)

        def _handle_exception(e: Exception) -> Response:
            status_code: str
            title: str
            detail: str

            if handle_exception:
                try:
                    resp = handle_exception(e)
                    if not isinstance(resp, Response):
                        resp = make_response(resp)
                    status_code = str(resp.status_code)
                    title = str(e)
                    detail = resp.data
                except Exception as ex:
                    status_code = "500"
                    title = type(e).__name__
                    detail = f"Error in the application exception handler: {ex}"

            elif isinstance(e, HTTPException):
                status_code = str(e.code or 500)
                title = e.name
                detail = e.description or str(e)
            else:
                status_code = "500"
                title = type(e).__name__
                detail = str(e)

            error = Error(id=status_code, title=title, detail=detail, status=status_code)
            toplevel = TopLevel(errors=[error]).model_dump_json(exclude_none=True)
            return make_response(toplevel, status_code, {"Content-Type": "application/vnd.api+json"})

        app.error_handler_spec[None][None][Exception] = _handle_exception

    def _change_content_type(self, resp: Response) -> Response:
        if "application/vnd.api+json" not in request.headers.getlist("accept"):
            return resp

        resp.content_type = "application/vnd.api+json"
        return resp


@t.overload
def extract_relationship(data: dict | str, relationship: str) -> list[dict] | dict:
    """Extracts from dict or a JSON string. Relationship string may be composed with '.' to extract nested relationships."""


@t.overload
def extract_relationship(data: TopLevel, relationship: Relationship | str) -> list[Resource] | Resource:
    """Extracts from a TopLevel model. Relationship string may be composed with '.' to extract nested relationships."""


@t.overload
def extract_relationship(data: SingleBodyModel, relationship: Relationship | str) -> Resource:
    """Extracts from a JsonApiBodyModel as a single resource. Relationship string may be composed with '.' to extract nested relationships."""


@t.overload
def extract_relationship(data: MultiBodyModel, relationship: Relationship | str) -> list[Resource]:
    """Extracts from a JsonApiBodyModel as a multiple resource. Relationship string may be composed with '.' to extract nested relationships."""


def extract_relationship(data, relationship: Relationship | str) -> list[Resource] | Resource | list[dict] | dict:
    """Returns the resource associated with the relationship if defined in included.

    :param toplevel: The toplevel jsonapi structure.
    :param relationship: The relationship to extract or the relationship path to extract.
                         Relationship string may be composed with '.' to extract nested relationships.
    """
    if isinstance(data, dict) or isinstance(data, str):
        _data = _to_toplevel(data)
    else:
        _data = data

    if isinstance(relationship, str):
        identifiers = get_relation_identifiers(_data, _data.data, relationship)
    elif isinstance(relationship, Relationship):
        identifiers = relationship.data
    else:
        raise AttributeError(f"Wrong relationship structure : {type(relationship)}.")

    if isinstance(identifiers, list):
        # Set in dictionary to avoid duplicate
        resources: dict[str, Resource] = {}
        for ident in identifiers:
            res = extract_from_resource_identifier(_data, ident)
            resources[f"{res.type}{res.id}"] = res
        return list(resources.values())

    res = extract_from_resource_identifier(_data, t.cast(ResourceIdentifier, identifiers))
    if isinstance(data, dict) or isinstance(data, str):
        return res.model_dump()
    return res


def flatten_resource(
    res: Resource | TopLevel,
    *,
    toplevel: TopLevel | SingleBodyModel | MultiBodyModel | None = None,
    pattern: str | None = None,
) -> dict:
    """Returns the resource attributes with the 'id' added. Can add more data if needed."""
    if isinstance(res, TopLevel):
        data = res.data
        if toplevel is None:
            toplevel = res
    else:
        data = res

    if not data:
        return {}

    if isinstance(data, list):
        return [flatten_resource(r, toplevel=toplevel, pattern=pattern) for r in data]  # type: ignore

    if not pattern:
        return {"type": data.type, "id": data.id, **data.attributes}

    if toplevel is None:
        raise ValueError("flatten_resource: toplevel must be provided if pattern is specified.")

    flatten = flatten_resource(data)

    if "." not in pattern:
        rel = extract_relationship(toplevel, pattern)
        flatten[pattern] = flatten_resource(rel) if isinstance(rel, Resource) else [flatten_resource(r) for r in rel]
        return flatten

    _flatten_resource(toplevel, data, flatten, *pattern.split(".", 1))

    return flatten


def extract_from_resource_identifier(
    toplevel: TopLevel | SingleBodyModel | MultiBodyModel, identifier: ResourceIdentifier
) -> Resource:
    """Returns the resource associated with the resource identifier if defined in included.

    :param toplevel: The toplevel jsonapi structure.
    :param identifier: The resource identifier.
    """
    tl = _to_toplevel(toplevel)
    ident = _to_identifier(identifier)

    # Get all attributes values of the included resources
    if tl.included:
        for r in tl.included:
            if r.type == ident.type and r.id == ident.id:
                return r
    raise AttributeError(f"Cannot extract identifier {ident} from {tl}")


def get_relation_identifiers(toplevel, data, relationship: str) -> ResourceIdentifier | list[ResourceIdentifier]:
    if isinstance(data, list):
        flat_list = []
        for d in data:
            rel = d.relationships[relationship].data
            flat_list.extend(rel) if isinstance(rel, list) else flat_list.append(rel)
        return flat_list

    if "." not in relationship:
        if relationship not in data.relationships:
            raise AttributeError(f"Cannot extract relationship {relationship} from {toplevel}")
        return data.relationships[relationship].data

    # Composed relationships
    *first, last = relationship.split(".")
    res = extract_relationship(toplevel, ".".join(first))
    if isinstance(res, list):
        flat_list = []
        for r in res:
            rel = get_relation_identifiers(toplevel, r, last)
            flat_list.extend(rel) if isinstance(rel, list) else flat_list.append(rel)
        return flat_list
    else:
        return get_relation_identifiers(toplevel, res, last)


def _to_toplevel(toplevel) -> TopLevel:
    if isinstance(toplevel, TopLevel):
        tl = toplevel
    elif isinstance(toplevel, _JsonApiBodyModel):
        tl = TopLevel.model_validate(toplevel.model_dump())
    elif isinstance(toplevel, dict):
        tl = TopLevel.model_validate(toplevel)
    elif isinstance(toplevel, str):
        tl = TopLevel.model_validate_json(toplevel)
    else:
        raise AttributeError(f"Wrong toplevel structure: no data available for {type(toplevel)}.")
    return tl


def _to_identifier(identifier) -> ResourceIdentifier:
    if isinstance(identifier, ResourceIdentifier):
        ident = identifier
    elif isinstance(identifier, Resource):
        ident = ResourceIdentifier.model_validate(identifier.model_dump())
    elif isinstance(identifier, dict):
        ident = ResourceIdentifier.model_validate(identifier)
    elif isinstance(identifier, str):
        ident = ResourceIdentifier.model_validate_json(identifier)
    else:
        raise AttributeError(f"Wrong resource identifier structure : {type(identifier)}.")
    return ident


def _flatten_resource(
    toplevel: TopLevel | SingleBodyModel | MultiBodyModel, current_res, current_flatten, first: str, lasts: str
):
    current_rel = current_res.relationships[first]
    if isinstance(current_rel.data, list):
        current_flatten[first] = []
        for r in current_rel.data:
            extracted = extract_from_resource_identifier(toplevel, r)
            frel = flatten_resource(extracted)
            current_flatten[first].append(frel)
            if "." in lasts:
                _flatten_resource(toplevel, extracted, frel, *lasts.split(".", 1))
            else:
                _add_flatten_relationship(toplevel, extracted, frel, lasts)
    else:
        extracted = extract_from_resource_identifier(toplevel, current_rel.data)
        frel = flatten_resource(extracted)
        current_flatten[first] = frel
        if "." in lasts:
            _flatten_resource(toplevel, extracted, frel, *lasts.split(".", 1))
        else:
            _add_flatten_relationship(toplevel, extracted, frel, lasts)


def _add_flatten_relationship(
    toplevel: TopLevel | SingleBodyModel | MultiBodyModel, res: Resource, flatten: dict, relationship: str
):
    if not res.relationships:
        raise AttributeError(f"No relationship in resource {res}")

    if "|" in relationship:
        for key in relationship.split("|"):
            _add_flatten_relationship(toplevel, res, flatten, key)
        return

    if relationship not in res.relationships:
        raise AttributeError(f"Relationship {relationship} not found in resource {res}")
    rel = res.relationships[relationship]
    if isinstance(rel.data, list):
        flatten[relationship] = [flatten_resource(extract_from_resource_identifier(toplevel, r)) for r in rel.data]
    else:
        flatten[relationship] = flatten_resource(extract_from_resource_identifier(toplevel, rel.data))
