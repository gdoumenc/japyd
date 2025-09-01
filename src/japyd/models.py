from __future__ import annotations

import types
import typing as t

from pydantic import AnyUrl
from pydantic import BaseModel

from japyd.jsonapi import Link
from japyd.jsonapi import Relationship
from japyd.jsonapi import Resource
from japyd.jsonapi import ResourceIdentifier

if t.TYPE_CHECKING:
    from japyd.dotnet import JsonApiQueryModel


class JsonApiBaseModel(BaseModel):
    """Base model for JSON:API resources."""

    @property
    def jsonapi_type(self) -> str:
        return getattr(self, 'type', '')

    @property
    def jsonapi_id(self) -> str:
        return getattr(self, 'id', '')

    @property
    def links(self) -> dict[str, AnyUrl | Link | None] | None:
        return None

    def as_resource(self, included: list[Resource], query: JsonApiQueryModel, *,
                    key_prefix: str | None = None) -> Resource:
        jsonapi_id = self.jsonapi_id
        jsonapi_type = self.jsonapi_type
        relationships: dict[str, Relationship] = {}

        def _add_in_included(value, prefixed_key: str) -> ResourceIdentifier:
            """Adds the value in the included list if it is included in the query and returns a ResourceIdentifier."""
            if query.include and prefixed_key in query.include:
                included.append(value.as_resource(included, query, key_prefix=prefixed_key))
            if isinstance(value, ResourceIdentifier):
                return value
            return ResourceIdentifier(type=value.jsonapi_type, id=value.jsonapi_id)

        fields = query.get_fields(jsonapi_type) if query else None

        # Creates relationships
        excluded_attributes = {'id', 'type'}
        for key, f in self.__class__.model_fields.items():

            if fields is not None and key not in fields:
                continue

            value = getattr(self, key)
            prefixed_key = f"{key_prefix}.{key}" if key_prefix else key
            if issubtype(f.annotation, JsonApiBaseModel) and value is not None:  # type: ignore[arg-type]

                # Bypass if annotated as a dict
                if 'as_attribute' in f.metadata:
                    continue

                if isinstance(value, list):
                    data = [_add_in_included(v, prefixed_key) for v in value]
                else:
                    data = _add_in_included(value, prefixed_key)
                relationships[key] = Relationship(data=data)  # noqa
                excluded_attributes.add(key)

        # Creates resource with attributes and relationships
        attributes = self.model_dump(include=fields, exclude=excluded_attributes)
        return Resource(id=jsonapi_id, type=jsonapi_type,
                        attributes=attributes, relationships=relationships, links=self.links)


T = t.TypeVar("T", bound="BaseModel")
UnionType = getattr(types, "UnionType", t.Union)


def issubtype(type_: t.Type, of_class: t.Generic[T]) -> T | None:  # type: ignore
    """Returns the subtype of a generic type if it is a subtype of the given class."""
    try:
        if issubclass(type(type_), types.GenericAlias) or issubclass(type_, t.Generic):  # type: ignore
            type_ = t.get_args(type_)[0]
    except TypeError:
        pass

    origin = t.get_origin(type_) or type_
    if origin is t.Union or origin is UnionType:
        for type__ in t.get_args(type_):
            type__ = issubtype(type__, of_class)
            if type__:
                return type__
        return None

    return origin if issubclass(origin, of_class) else None  # type: ignore
