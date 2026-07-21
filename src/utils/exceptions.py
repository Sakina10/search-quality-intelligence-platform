"""Custom Exception Classes for the Google Search Quality Intelligence Platform.

This module defines a clear exception hierarchy, allowing components to raise and
catch specific domain-level errors rather than generic Python runtime exceptions.
"""

class SearchQualityBaseError(Exception):
    """Base exception class for all errors raised by the Search Quality Platform."""
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(SearchQualityBaseError):
    """Raised when environment variables or config YAML parameters are invalid or missing."""
    pass


class DataValidationError(SearchQualityBaseError):
    """Raised when incoming search log data fails data validation checks."""
    pass


class DatabaseConnectionError(SearchQualityBaseError):
    """Raised when connecting to or executing statements on the relational warehouse fails."""
    pass


class FeatureStoreError(SearchQualityBaseError):
    """Raised when feature views configuration or Feast registry operations fail."""
    pass


class ModelInferenceError(SearchQualityBaseError):
    """Raised when loading model weights, calculating SHAP, or serving predictions fails."""
    pass


class AnomalyDetectionError(SearchQualityBaseError):
    """Raised when anomaly detection scoring or calibration fails."""
    pass


class ExperimentationError(SearchQualityBaseError):
    """Raised when power calculations or Sample Ratio Mismatch (SRM) checks fail."""
    pass
