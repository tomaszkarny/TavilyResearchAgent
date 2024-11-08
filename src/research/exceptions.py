"""
Custom exceptions for research operations.
"""

class ResearchError(Exception):
    """Base exception for research operations"""
    pass

class SearchError(ResearchError):
    """Raised when search operation fails"""
    pass

class DocumentProcessingError(ResearchError):
    """Raised when document processing fails"""
    pass

class DatabaseError(ResearchError):
    """Raised when database operations fail"""
    pass

class ConfigurationError(ResearchError):
    """Raised when configuration is invalid or missing"""
    pass