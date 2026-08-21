"""
DataFlow Automator Pro - Custom Exceptions Module
Provides domain-specific exceptions for robust error handling and recovery.
"""

class DataFlowException(Exception):
    """Base exception for all DataFlow Automator operations."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class FileOperationError(DataFlowException):
    """Raised when file management operations (organize, rename, delete, duplicate detection) fail."""
    pass


class DataProcessingError(DataFlowException):
    """Raised when Excel or CSV data ingestion, cleaning, transformation or aggregation fails."""
    pass


class PDFGenerationError(DataFlowException):
    """Raised when PDF report generation, rendering, or manipulation encounters an error."""
    pass


class EmailDispatchError(DataFlowException):
    """Raised when SMTP connection, template rendering, or email sending fails."""
    pass


class ScrapingError(DataFlowException):
    """Raised when web scraping, network requests, or HTML parsing fails."""
    pass


class WorkflowExecutionError(DataFlowException):
    """Raised when an end-to-end pipeline workflow encounters an execution step failure."""
    pass
