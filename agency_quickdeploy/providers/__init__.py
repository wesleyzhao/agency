"""Provider abstraction layer for agency-quickdeploy.

This module provides an abstract base class for deployment providers,
allowing agency-quickdeploy to support multiple backends (GCP, Railway, etc.).
"""

from agency_quickdeploy.providers.base import (
    BaseProvider,
    DeploymentResult,
    ProviderType,
)
from agency_quickdeploy.providers.gcp import GCPProvider
from agency_quickdeploy.providers.railway import RailwayProvider

__all__ = [
    "BaseProvider",
    "DeploymentResult",
    "ProviderType",
    "GCPProvider",
    "RailwayProvider",
]
