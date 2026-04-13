from .client import JapydClient
from .dotnet import JsonApiBaseModel, JsonApiQueryModel
from .jsonapi import (
    Error,
    JsonApiApp,
    JsonApiBodyModel,
    Link,
    MultiBodyModel,
    MultiResourcesTopLevel,
    Relationship,
    Resource,
    ResourceIdentifier,
    SingleBodyModel,
    SingleResourceTopLevel,
    TopLevel,
    extract_from_resource_identifier,
    extract_relationship,
)
from .utils import flatten_resource

__all__ = [
    "TopLevel",
    "Resource",
    "ResourceIdentifier",
    "Relationship",
    "Link",
    "Error",
    "JsonApiApp",
    "JsonApiBaseModel",
    "SingleBodyModel",
    "MultiBodyModel",
    "JsonApiQueryModel",
    "JsonApiBodyModel",
    "JapydClient",
    "SingleResourceTopLevel",
    "MultiResourcesTopLevel",
    "extract_relationship",
    "extract_from_resource_identifier",
    "flatten_resource",
]
