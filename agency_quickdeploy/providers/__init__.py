"""Provider abstraction layer for agency-quickdeploy.

This module provides an abstract base class for deployment providers,
allowing agency-quickdeploy to support multiple backends (GCP, Railway, etc.).

Note: Concrete providers (GCPProvider, RailwayProvider) are NOT imported here
to avoid circular imports. Import them directly when needed:
    from agency_quickdeploy.providers.gcp import GCPProvider
    from agency_quickdeploy.providers.railway import RailwayProvider
"""

from agency_quickdeploy.providers.base import (
    BaseProvider,
    DeploymentResult,
    ProviderType,
)

__all__ = [
    "BaseProvider",
    "DeploymentResult",
    "ProviderType",
]
