"""
Custom exception hierarchy for the log-worker service.
Distinguishes between non-retryable (PermanentError) and retryable (TransientError) failures.
"""


class PermanentError(Exception):
    """Base class for non-retryable / permanent errors."""
    pass


class TransientError(Exception):
    """Base class for retryable / transient errors."""
    pass


class ObjectNotFoundError(PermanentError):
    """Raised when an object key is not found in object storage."""
    pass


class InvalidLogFileError(PermanentError):
    """Raised when log file is corrupt, unparseable, empty, or exceeds skipped lines ratio."""
    pass


class StorageUnavailableError(TransientError):
    """Raised when object storage is unreachable or returns a server error."""
    pass


class DatabaseUnavailableError(TransientError):
    """Raised when MongoDB is unreachable or times out."""
    pass
