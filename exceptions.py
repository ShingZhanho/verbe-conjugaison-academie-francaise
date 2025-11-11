"""
Custom exceptions for the verb conjugation crawler.
Created on: 2025-11-11
"""


class CrawlerException(Exception):
    """Base exception for crawler errors."""
    pass


class NetworkException(CrawlerException):
    """Exception for network-related errors."""
    pass


class ParsingException(CrawlerException):
    """Exception for parsing errors."""
    pass


class CacheException(CrawlerException):
    """Exception for cache-related errors."""
    pass


class ConfigurationException(CrawlerException):
    """Exception for configuration errors."""
    pass
