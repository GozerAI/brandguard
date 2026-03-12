"""Tests for BrandService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from brandguard.service import BrandService


class TestBrandService:
    """Tests for the BrandService."""

    @pytest.fixture
    def brand_service(self):
        """Create a BrandService instance."""
        from brandguard import BrandService
        return BrandService()

    def test_service_initialization(self, brand_service):
        """Verify service initializes correctly."""
        assert brand_service is not None
        assert hasattr(brand_service, "_identity")

    def test_get_identity_empty(self, brand_service):
        """Get identity returns None when not created."""
        identity = brand_service.get_identity()
        assert identity is None

    def test_create_identity(self, brand_service):
        """Create brand identity."""
        result = brand_service.create_identity(
            name="TestBrand",
            tagline="Test Tagline",
            mission="Test Mission",
            primary_tone="professional",
        )
        assert "name" in result
        assert result["name"] == "TestBrand"

    def test_get_identity_after_create(self, brand_service):
        """Get identity returns data after creation."""
        brand_service.create_identity(
            name="TestBrand",
            tagline="Test Tagline",
        )
        identity = brand_service.get_identity()
        assert identity is not None
        assert identity["name"] == "TestBrand"

    def test_validate_content_no_identity(self, brand_service):
        """Validate content fails without identity."""
        result = brand_service.validate_content(
            content="Test content",
            content_type="website",
        )
        assert "error" in result or "passed" in result

    def test_validate_content_with_identity(self, brand_service):
        """Validate content with identity."""
        brand_service.create_identity(
            name="TestBrand",
            primary_tone="professional",
        )
        result = brand_service.validate_content(
            content="This is professional test content.",
            content_type="website",
        )
        assert isinstance(result, dict)

    def test_add_guideline(self, brand_service):
        """Add a brand guideline."""
        guideline_id = brand_service.add_guideline(
            category="voice",
            title="Test Guideline",
            description="Test description",
            rule_type="guideline",
        )
        assert guideline_id is not None
        assert isinstance(guideline_id, str)

    def test_get_guidelines(self, brand_service):
        """Get brand guidelines."""
        brand_service.add_guideline(
            category="voice",
            title="Test Guideline",
            description="Test description",
        )
        guidelines = brand_service.get_guidelines()
        assert isinstance(guidelines, list)
        assert len(guidelines) >= 1

    def test_get_executive_report_cmo(self, brand_service):
        """CMO report has marketing focus."""
        brand_service.create_identity(
            name="TestBrand",
        )
        report = brand_service.get_executive_report("CMO")
        assert report["executive"] == "CMO"
        assert report["focus"] == "Brand Voice & Marketing"

    def test_get_brand_kit(self, brand_service):
        """Get brand kit."""
        brand_service.create_identity(
            name="TestBrand",
        )
        kit = brand_service.get_brand_kit()
        assert "name" in kit
        assert kit["name"] == "TestBrand"

    def test_autonomous_analysis_no_identity(self, brand_service):
        """Autonomous analysis returns error without identity."""
        result = brand_service.run_autonomous_analysis()
        assert "error" in result

    def test_autonomous_analysis_with_identity(self, brand_service):
        """Autonomous analysis returns real health data."""
        brand_service.create_identity(
            name="HealthBrand",
            tagline="Stay healthy",
            primary_tone="friendly",
        )
        result = brand_service.run_autonomous_analysis()
        assert "health_score" in result
        assert "brand_health" in result
        assert "recommendations" in result
        assert result["health_score"] > 0
        assert isinstance(result["brand_health"]["identity_completeness"], float)
        assert isinstance(result["brand_health"]["guidelines_defined"], int)

    def test_autonomous_analysis_completeness_check(self, brand_service):
        """Analysis detects incomplete identity fields."""
        brand_service.create_identity(name="MinimalBrand")
        result = brand_service.run_autonomous_analysis()
        # Missing tagline, mission, colors, typography
        assert result["health_score"] < 100
        recs = " ".join(result["recommendations"])
        assert "missing" in recs.lower() or "Complete" in recs

    def test_autonomous_analysis_guideline_coverage(self, brand_service):
        """Analysis recommends missing guideline categories."""
        brand_service.create_identity(name="GuidelineBrand")
        brand_service.add_guideline(
            category="voice", title="Tone", description="Be friendly",
        )
        result = brand_service.run_autonomous_analysis()
        categories = result["brand_health"]["guideline_categories"]
        assert "voice" in categories

    def test_get_stats(self, brand_service):
        """Get service stats."""
        stats = brand_service.get_stats()
        assert "initialized" in stats
        assert "has_identity" in stats

    def test_get_telemetry_returns_dict(self, brand_service):
        """get_telemetry always returns a dict (empty if lib not installed)."""
        result = brand_service.get_telemetry()
        assert isinstance(result, dict)

    def test_get_telemetry_graceful_without_lib(self, brand_service):
        """Without gozerai-telemetry installed, get_telemetry returns {}."""
        import brandguard.service as svc
        original = svc._HAS_TELEMETRY
        try:
            svc._HAS_TELEMETRY = False
            result = brand_service.get_telemetry()
            assert result == {}
        finally:
            svc._HAS_TELEMETRY = original

    def test_identity_persistence_save_load(self, tmp_path):
        """Identity persists to disk and loads on init."""
        storage = str(tmp_path)
        svc = BrandService(storage_path=storage)
        svc.create_identity(
            name="PersistBrand",
            tagline="Persisted",
            primary_tone="friendly",
        )

        # Verify file exists
        identity_file = tmp_path / "identity.json"
        assert identity_file.exists()

        # Create new service instance and verify auto-load
        svc2 = BrandService(storage_path=storage)
        identity = svc2.get_identity()
        assert identity is not None
        assert identity["name"] == "PersistBrand"

    def test_identity_persistence_update_voice(self, tmp_path):
        """Voice updates are persisted."""
        storage = str(tmp_path)
        svc = BrandService(storage_path=storage)
        svc.create_identity(name="VoiceBrand", tagline="Test")
        svc.update_voice(avoided_words=["synergy"])

        svc2 = BrandService(storage_path=storage)
        assert svc2._identity is not None
        assert "synergy" in svc2._identity.voice_guidelines.avoided_words

    def test_no_storage_path_no_persistence(self):
        """Without storage_path, no files created."""
        svc = BrandService()
        svc.create_identity(name="MemOnly")
        assert svc._identity_file is None
