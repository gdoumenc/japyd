from enum import StrEnum


class FilterError(ValueError):
    """The filter cannot be applied on the model (unknown attribute, incompatible types, ...)."""


class Oper(StrEnum):
    NOT = "not"
    OR = "or"
    AND = "and"

    EQUALS = "equals"
    LESS_THAN = "lessThan"
    LESS_OR_EQUAL = "lessOrEqual"
    GREATER_THAN = "greaterThan"
    GREATER_OR_EQUAL = "greaterOrEqual"

    CONTAINS = "contains"
    STARTS_WITH = "startsWith"
    ENDS_WITH = "endsWith"

    CONTAINS_IGNORE_CASE = "containsIgnoreCase"
    STARTS_WITH_IGNORE_CASE = "startsWithIgnoreCase"
    ENDS_WITH_IGNORE_CASE = "endsWithIgnoreCase"

    ANY = "any"  # Equals one value from set
    HAS = "has"  # Collection is not empty, or has an item matching the filter
