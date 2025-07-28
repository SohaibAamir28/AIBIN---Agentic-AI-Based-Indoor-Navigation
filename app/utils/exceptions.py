"""
Custom exception classes for AIBIN platform.
Provides specific exceptions for different error scenarios.
"""

from typing import Optional, Dict, Any


class AIBINException(Exception):
    """Base exception class for AIBIN application."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AIBINException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(AIBINException):
    """Raised when user lacks required permissions."""
    pass


class ValidationError(AIBINException):
    """Raised when data validation fails."""
    pass


class NotFoundError(AIBINException):
    """Raised when requested resource is not found."""
    pass


class ConflictError(AIBINException):
    """Raised when resource already exists or conflicts."""
    pass


class DatabaseError(AIBINException):
    """Raised when database operations fail."""
    pass


class ExternalServiceError(AIBINException):
    """Raised when external service calls fail."""
    pass


class AIAgentError(AIBINException):
    """Raised when AI agent operations fail."""
    pass


class GroqAPIError(ExternalServiceError):
    """Raised when Groq API calls fail."""
    pass


class RateLimitError(AIBINException):
    """Raised when rate limits are exceeded."""
    pass


class ConfigurationError(AIBINException):
    """Raised when configuration is invalid."""
    pass