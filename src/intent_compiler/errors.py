class IntentCompilerError(Exception):
    """Base error for the reference implementation."""


class ValidationFailure(IntentCompilerError):
    pass


class InvalidTransition(IntentCompilerError):
    pass


class AuthorizationFailure(IntentCompilerError):
    pass


class PrerequisiteFailure(IntentCompilerError):
    pass


class UnsafeTarget(IntentCompilerError):
    pass


class UnknownExecutionState(IntentCompilerError):
    """Raised when an action may have occurred but the target state is unknown."""
