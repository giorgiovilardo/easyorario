"""Custom exception hierarchy for Easyorario."""


class EasyorarioError(Exception):
    """Base exception for all Easyorario domain errors."""

    error_key: str = ""


class EmailAlreadyTakenError(EasyorarioError):
    """Raised when registration email is already in use."""

    error_key = "email_taken"


class PasswordTooShortError(EasyorarioError):
    """Raised when password doesn't meet minimum length."""

    error_key = "password_too_short"


class InvalidEmailError(EasyorarioError):
    """Raised when email format is invalid."""

    error_key = "invalid_email"


class InvalidCredentialsError(EasyorarioError):
    """Raised when login credentials are invalid."""

    error_key = "invalid_credentials"


class InvalidTimetableDataError(EasyorarioError):
    """Raised when timetable form data fails validation."""

    def __init__(self, error_key: str) -> None:
        self.error_key = error_key
        super().__init__(error_key)


class InvalidConstraintDataError(EasyorarioError):
    """Raised when constraint form data fails validation."""

    def __init__(self, error_key: str) -> None:
        self.error_key = error_key
        super().__init__(error_key)


class LLMConfigError(EasyorarioError):
    """Raised when LLM configuration validation or connectivity fails."""

    def __init__(self, error_key: str) -> None:
        self.error_key = error_key
        super().__init__(error_key)
