class DomainValidationError(ValueError):
    """Raised when a domain invariant is violated."""


class BusinessRuleViolation(ValueError):
    """Raised when an operation violates a documented business rule."""
