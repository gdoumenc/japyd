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

    ANY = "any"  # Equals one value from set
    HAS = "has"  # Collection contains items
