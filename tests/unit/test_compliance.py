"""Tests for ComplianceReporter and BrandService.generate_compliance_report."""

import pytest

from brandguard.core import (
    BrandIdentity,
    BrandTone,
    BrandVoiceGuideline,
    ColorPalette,
    ContentType,
    Typography,
    FontFamily,
)
from brandguard.guidelines import ComplianceReporter
from brandguard.service import BrandService


def _identity(
    name: str = "TestBrand",
    tone: BrandTone = BrandTone.PROFESSIONAL,
    avoided_words: list | None = None,
) -> BrandIdentity:
    voice = BrandVoiceGuideline(
        primary_tone=tone,
        avoided_words=avoided_words or [],
    )
    return BrandIdentity(
        name=name,
        voice_guidelines=voice,
        color_palette=ColorPalette(name="test"),
        typography=Typography(primary_font=FontFamily(name="Arial", category="sans-serif")),
    )


CLEAN_SAMPLES = [
    {"name": "Homepage", "text": "Our enterprise platform delivers reliable solutions.", "type": "website"},
    {"name": "About", "text": "We build professional tools for modern teams.", "type": "website"},
    {"name": "Blog post", "text": "Discover how analytics drive better decisions in your organization.", "type": "blog"},
]

MIXED_SAMPLES = [
    {"name": "Good page", "text": "Our enterprise platform delivers reliable solutions.", "type": "website"},
    {"name": "Bad page", "text": "Hey gonna wanna check this out, it's awesome and cool!", "type": "website"},
    {"name": "Wrong name", "text": "Welcome to testbrand, the cheap option for everyone.", "type": "website"},
]


class TestComplianceReporter:
    def test_empty_samples(self):
        """Empty content list returns no_content status."""
        reporter = ComplianceReporter(_identity())
        report = reporter.generate_report([])
        assert report["status"] == "no_content"
        assert report["samples_analyzed"] == 0

    def test_clean_content_compliant(self):
        """Clean content should produce compliant status."""
        reporter = ComplianceReporter(_identity())
        report = reporter.generate_report(CLEAN_SAMPLES)
        assert report["status"] == "compliant"
        assert report["overall_score"] >= 80
        assert report["pass_rate"] > 0

    def test_report_structure(self):
        """Report has all required fields."""
        reporter = ComplianceReporter(_identity())
        report = reporter.generate_report(CLEAN_SAMPLES)
        assert "name" in report
        assert "generated_at" in report
        assert "brand" in report
        assert "status" in report
        assert "samples_analyzed" in report
        assert "overall_score" in report
        assert "pass_rate" in report
        assert "summary" in report
        assert "by_sample" in report
        assert "top_issues" in report
        assert "recommendations" in report

    def test_report_name_custom(self):
        """Custom report name is used."""
        reporter = ComplianceReporter(_identity())
        report = reporter.generate_report(CLEAN_SAMPLES, report_name="Q1 Audit")
        assert report["name"] == "Q1 Audit"

    def test_brand_name_in_report(self):
        """Brand name appears in report."""
        reporter = ComplianceReporter(_identity(name="GozerAI"))
        report = reporter.generate_report(CLEAN_SAMPLES)
        assert report["brand"] == "GozerAI"

    def test_mixed_content_lower_score(self):
        """Mixed-quality content produces lower scores."""
        reporter = ComplianceReporter(
            _identity(name="TestBrand", avoided_words=["cheap"])
        )
        report = reporter.generate_report(MIXED_SAMPLES)
        assert report["overall_score"] < 100
        assert report["summary"]["total_issues"] > 0 or report["summary"]["total_warnings"] > 0

    def test_by_sample_breakdown(self):
        """Per-sample breakdown has correct count."""
        reporter = ComplianceReporter(_identity())
        report = reporter.generate_report(CLEAN_SAMPLES)
        assert len(report["by_sample"]) == 3
        for entry in report["by_sample"]:
            assert "name" in entry
            assert "score" in entry
            assert "passed" in entry

    def test_top_issues_sorted(self):
        """Top issues are sorted by frequency descending."""
        reporter = ComplianceReporter(
            _identity(name="TestBrand", avoided_words=["cheap", "bad"])
        )
        samples = [
            {"name": f"sample{i}", "text": "This is cheap and bad content.", "type": "website"}
            for i in range(5)
        ]
        report = reporter.generate_report(samples)
        if len(report["top_issues"]) >= 2:
            assert report["top_issues"][0]["count"] >= report["top_issues"][1]["count"]

    def test_status_levels(self):
        """Different content quality maps to different status levels."""
        reporter = ComplianceReporter(
            _identity(avoided_words=["bad", "terrible", "awful", "horrible", "broken"])
        )
        # All terrible content
        bad_samples = [
            {"name": f"s{i}", "text": "bad terrible awful horrible broken content bad terrible awful horrible broken", "type": "website"}
            for i in range(5)
        ]
        report = reporter.generate_report(bad_samples)
        assert report["status"] in ("non_compliant", "critical")

    def test_recommendations_generated(self):
        """Recommendations are generated for non-compliant content."""
        reporter = ComplianceReporter(
            _identity(name="TestBrand", avoided_words=["cheap"])
        )
        samples = [
            {"name": "s1", "text": "testbrand is cheap and gonna be awesome hey cool", "type": "website"},
        ]
        report = reporter.generate_report(samples)
        assert len(report["recommendations"]) > 0

    def test_no_text_samples_skipped(self):
        """Samples without text are skipped."""
        reporter = ComplianceReporter(_identity())
        samples = [
            {"name": "empty", "text": "", "type": "website"},
            {"name": "valid", "text": "Our platform delivers results.", "type": "website"},
        ]
        report = reporter.generate_report(samples)
        assert report["samples_analyzed"] == 1

    def test_brand_name_recommendation(self):
        """Brand name issues generate specific recommendation."""
        reporter = ComplianceReporter(_identity(name="GozerAI"))
        samples = [
            {"name": "wrong", "text": "Welcome to gozerai, we are here to help you.", "type": "website"},
        ]
        report = reporter.generate_report(samples)
        name_recs = [r for r in report["recommendations"] if "GozerAI" in r]
        assert len(name_recs) >= 1

    def test_vocabulary_recommendation(self):
        """Vocabulary issues generate specific recommendation."""
        reporter = ComplianceReporter(_identity(avoided_words=["synergy"]))
        samples = [
            {"name": "jargon", "text": "We leverage synergy to drive results.", "type": "website"},
        ]
        report = reporter.generate_report(samples)
        vocab_recs = [r for r in report["recommendations"] if "vocabulary" in r.lower()]
        assert len(vocab_recs) >= 1

    def test_compliant_recommendation(self):
        """Fully compliant content gets positive recommendation."""
        reporter = ComplianceReporter(_identity())
        samples = [
            {"name": "good", "text": "Our platform delivers reliable solutions.", "type": "website"},
        ]
        report = reporter.generate_report(samples)
        assert any("strong" in r.lower() or "continue" in r.lower() for r in report["recommendations"])


class TestBrandServiceCompliance:
    @pytest.fixture
    def service_with_identity(self):
        svc = BrandService()
        svc.create_identity(
            name="TestBrand",
            tagline="Testing",
            primary_tone="professional",
        )
        return svc

    def test_generate_compliance_report(self, service_with_identity):
        """Service method generates compliance report."""
        report = service_with_identity.generate_compliance_report(CLEAN_SAMPLES)
        assert "status" in report
        assert report["brand"] == "TestBrand"

    def test_compliance_report_no_identity(self):
        """Returns error without identity."""
        svc = BrandService()
        report = svc.generate_compliance_report(CLEAN_SAMPLES)
        assert "error" in report
