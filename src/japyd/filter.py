from enum import StrEnum


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
    START_WITH_IGNORE_CASE = "startWithIgnoreCase"
    ENDS_WITH_IGNORE_CASE = "endsWithIgnoreCase"

    ANY = "any"  # Equals one value from set
    HAS = "has"  # Collection contains items
