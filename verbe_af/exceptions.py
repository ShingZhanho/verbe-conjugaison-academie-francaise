"""Custom exceptions for the verb conjugation crawler."""


class CrawlerError(Exception):
    """Base exception for all crawler errors."""


class NetworkError(CrawlerError):
    """Raised when an HTTP request fails after all retries."""

    def __init__(self, message: str, verb: str | None = None, url: str | None = None):
        self.verb = verb
        self.url = url
        super().__init__(message)


class ParsingError(CrawlerError):
    """Raised when HTML conjugation data cannot be parsed."""

    def __init__(self, message: str, verb: str | None = None):
        self.verb = verb
        super().__init__(message)


class CacheError(CrawlerError):
    """Raised when a cache read/write operation fails."""

    def __init__(self, message: str, path: str | None = None):
        self.path = path
        super().__init__(message)


class ConfigError(CrawlerError):
    """Raised when configuration is invalid."""
