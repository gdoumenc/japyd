from __future__ import annotations

import types
import typing as t

from pydantic import AnyUrl, BaseModel

from .filter import FilterError, Oper
from .jsonapi import Link, Relationship, Resource, ResourceIdentifier, flatten_resource

if t.TYPE_CHECKING:
    from .dotnet import JsonApiQueryModel

_UNKNOWN = object()


class JsonApiBaseModel(BaseModel):
    """Base model for JSON:API resources.

    A resource must have an id and a type. The type is defined as a class variable and the id is defined as a property.
    """

    jsonapi_type: t.ClassVar[str] = "jsonapi.type.undefined"

    @property
    def jsonapi_id(self) -> str:
        return getattr(self, "id", "")

    @property
    def links(self) -> dict[str, AnyUrl | Link | None] | None:
        return None

    @classmethod
    def from_resource(cls, res: Resource):
        if res.type != cls.jsonapi_type:
            raise ValueError(f"The resource type must be {cls.jsonapi_type}.")
        return cls.model_validate(flatten_resource(res))

    def as_resource(
        self, included: list[Resource], query: JsonApiQueryModel, *, key_prefix: str | None = None
    ) -> Resource:
        """Converts the model into a JSON:API resource.

        Args:
            included: List of included resources for relationships
            query: Query object containing the filtering parameters
            key_prefix: Prefix for the relationship keys (used for nested relationships)
        """

        jsonapi_id = self.jsonapi_id
        jsonapi_type = (
            self.jsonapi_type if isinstance(self.jsonapi_type, str) else getattr(self.jsonapi_type, "default", "")
        )
        if not isinstance(jsonapi_id, str):
            raise TypeError("The resource must have a string as id.")
        if not isinstance(jsonapi_type, str):
            raise TypeError("The resource must have a string as type.")
        relationships: dict[str, Relationship] = {}

        def _add_in_included(value, prefixed_key: str) -> ResourceIdentifier:
            """Adds the value in the included list if it is included in the query and returns a ResourceIdentifier."""
            if query.include and prefixed_key in query.include:
                to_be_incl: Resource = value.as_resource(included, query, key_prefix=prefixed_key)
                if len([r for r in included if r.type == to_be_incl.type and r.id == to_be_incl.id]) == 0:
                    included.append(to_be_incl)
            if isinstance(value, ResourceIdentifier):
                return value
            return ResourceIdentifier(type=value.jsonapi_type, id=value.jsonapi_id)

        fields = query.get_fields(jsonapi_type) if query else None

        # Creates relationships
        excluded_attributes = {"id", "type"}
        for key, f in self.__class__.model_fields.items():

            if fields is not None and key not in fields:
                continue

            value = getattr(self, key)
            prefixed_key = f"{key_prefix}.{key}" if key_prefix else key
            if issubtype(f.annotation, JsonApiBaseModel) and value is not None:  # type: ignore[arg-type]

                # Bypass if annotated as a dict
                if "as_attribute" in f.metadata:
                    continue

                if isinstance(value, list):
                    data = [_add_in_included(v, prefixed_key) for v in value]
                else:
                    data = _add_in_included(value, prefixed_key)
                relationships[key] = Relationship(data=data)
                excluded_attributes.add(key)

        # Creates resource with attributes and relationships
        attributes = self.model_dump(include=fields, exclude=excluded_attributes)
        return Resource(
            id=jsonapi_id, type=jsonapi_type, attributes=attributes, relationships=relationships, links=self.links
        )

    def resolve_attr(self, attr: str) -> t.Any:
        """Returns the attribute value, following the to-one relationships if the attribute is a dotted path.

        A dict attribute (JSON value) is followed by its keys, a missing key giving None.
        Raises FilterError if the attribute is unknown or the path goes through a to-many relationship.
        """
        value: t.Any = self
        for name in attr.split("."):
            if value is None:
                return None
            if isinstance(value, list):
                raise FilterError(f"Cannot filter on {attr} through a to-many relationship, use has instead")
            if isinstance(value, dict):
                value = value.get(name)
                continue
            value = getattr(value, name, _UNKNOWN)
            if value is _UNKNOWN or callable(value):
                raise FilterError(f"Unknown attribute {attr}")
        return value

    def match(self, oper: Oper, attr: str, value: t.Any) -> bool:
        attr_value = self.resolve_attr(attr)
        if oper == Oper.EQUALS:
            return attr_value == value
        if oper == Oper.ANY:
            return attr_value in value

        # As in SQL, a null value is never ordered or contained
        if attr_value is None or value is None:
            return False

        try:
            if oper == Oper.LESS_THAN:
                return attr_value < value
            if oper == Oper.LESS_OR_EQUAL:
                return attr_value <= value
            if oper == Oper.GREATER_THAN:
                return attr_value > value
            if oper == Oper.GREATER_OR_EQUAL:
                return attr_value >= value
            if oper == Oper.CONTAINS:
                return value in attr_value
            if oper == Oper.STARTS_WITH:
                return attr_value.startswith(value)
            if oper == Oper.ENDS_WITH:
                return attr_value.endswith(value)
            if oper == Oper.CONTAINS_IGNORE_CASE:
                return value.lower() in attr_value.lower()
            if oper == Oper.STARTS_WITH_IGNORE_CASE:
                return attr_value.lower().startswith(value.lower())
            if oper == Oper.ENDS_WITH_IGNORE_CASE:
                return attr_value.lower().endswith(value.lower())
        except (TypeError, AttributeError) as e:
            raise FilterError(f"Cannot apply {oper} on {attr} with value {value!r}") from e
        return False


class JapydDictBaseModel(JsonApiBaseModel):
    """Base model for JSON:API resources."""

    @property
    def jsonapi_type(self) -> str:
        return getattr(self, "type", "")

    @jsonapi_type.setter
    def jsonapi_type(self, value: str) -> None:  # type: ignore
        assert False, "Cannot change the type of a resource."


T = t.TypeVar("T", bound="BaseModel")
UnionType = getattr(types, "UnionType", t.Union)


def issubtype(type_: type, of_class: t.Generic[T]) -> T | None:  # type: ignore[valid-type]
    """Returns the subtype of a generic type if it is a subtype of the given class."""
    try:
        if issubclass(type(type_), types.GenericAlias) or issubclass(type_, t.Generic):  # type: ignore[arg-type]
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

    try:
        return origin if issubclass(origin, of_class) else None  # type: ignore
    except TypeError:
        # Should check for ForwardRef
        return None
