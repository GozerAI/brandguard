"""
Brandguard - Brand Suite.

Provides brand guidelines, asset management, and consistency enforcement
for C-Suite executives. Enables brand-aligned content creation and
marketing material validation.

Primary Owners: CMO (Echo), CCO (Artisan)
Secondary Owners: CPO (Visionary)
"""

from brandguard.core import (
    BrandAssetType,
    BrandTone,
    BrandVoice,
    ColorPalette,
    Typography,
    BrandAsset,
    BrandGuideline,
    BrandIdentity,
)
from brandguard.guidelines import (
    ComplianceReporter,
    GuidelineManager,
    GuidelineValidator,
    ConsistencyChecker,
)
from brandguard.assets import (
    AssetManager,
    AssetLibrary,
)
from brandguard.service import BrandService

__all__ = [
    # Core
    "BrandAssetType",
    "BrandTone",
    "BrandVoice",
    "ColorPalette",
    "Typography",
    "BrandAsset",
    "BrandGuideline",
    "BrandIdentity",
    # Guidelines
    "ComplianceReporter",
    "GuidelineManager",
    "GuidelineValidator",
    "ConsistencyChecker",
    # Assets
    "AssetManager",
    "AssetLibrary",
    # Service
    "BrandService",
]
