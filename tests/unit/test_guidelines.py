"""Tests for brand guideline validation — semantic checks."""

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
from brandguard.guidelines import GuidelineValidator, ValidationResult


def _identity(
    name: str = "TestBrand",
    tone: BrandTone = BrandTone.PROFESSIONAL,
    avoided_words: list | None = None,
) -> BrandIdentity:
    """Create a minimal brand identity for testing."""
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


class TestReadability:
    def test_casual_tone_flags_complex_text(self):
        """Complex text should warn for casual brands."""
        identity = _identity(tone=BrandTone.CASUAL)
        validator = GuidelineValidator(identity)
        # Dense, multi-syllable text
        text = (
            "The implementation necessitates comprehensive restructuring of "
            "organizational infrastructure. Furthermore, the amalgamation of "
            "interdependent subsystems requires meticulous orchestration. "
            "Subsequently, the ramifications of inadequate preparation are "
            "considerable and multifaceted."
        )
        result = validator.validate_text(text)
        warnings = [w for w in result.warnings if w["category"] == "readability"]
        assert len(warnings) >= 1

    def test_formal_tone_flags_simple_text(self):
        """Very simple text should warn for formal brands."""
        identity = _identity(tone=BrandTone.FORMAL)
        validator = GuidelineValidator(identity)
        text = "We do it. You like it. It is fun. We are here. We help you. It is good. We go far."
        result = validator.validate_text(text)
        warnings = [w for w in result.warnings if w["category"] == "readability"]
        assert len(warnings) >= 1

    def test_readability_score_in_suggestions(self):
        """Readability score always appears in suggestions."""
        identity = _identity()
        validator = GuidelineValidator(identity)
        text = "Our platform delivers enterprise solutions. We help businesses grow every day."
        result = validator.validate_text(text)
        assert any("Flesch" in s for s in result.suggestions)


class TestSentiment:
    def test_negative_sentiment_flags_inspirational_brand(self):
        """Negative language warns for inspirational brands."""
        identity = _identity(tone=BrandTone.INSPIRATIONAL)
        validator = GuidelineValidator(identity)
        text = (
            "Unfortunately the failure of our broken system is a terrible problem. "
            "We worry about the awful risk and the horrible danger ahead."
        )
        result = validator.validate_text(text)
        warnings = [w for w in result.warnings if w["category"] == "sentiment"]
        assert len(warnings) >= 1

    def test_positive_text_no_sentiment_warning(self):
        """Positive text should not trigger sentiment warnings."""
        identity = _identity(tone=BrandTone.INSPIRATIONAL)
        validator = GuidelineValidator(identity)
        text = "We love building amazing products. Our innovative team achieves incredible growth."
        result = validator.validate_text(text)
        warnings = [w for w in result.warnings if w["category"] == "sentiment"]
        assert len(warnings) == 0

    def test_professional_tone_ignores_sentiment(self):
        """Professional tone doesn't flag negative sentiment."""
        identity = _identity(tone=BrandTone.PROFESSIONAL)
        validator = GuidelineValidator(identity)
        text = "The risk assessment reveals several problems and potential failures."
        result = validator.validate_text(text)
        warnings = [w for w in result.warnings if w["category"] == "sentiment"]
        assert len(warnings) == 0


class TestBrandNameConsistency:
    def test_correct_casing_passes(self):
        """Correctly cased brand name has no issues."""
        identity = _identity(name="GozerAI")
        validator = GuidelineValidator(identity)
        result = validator.validate_text("Welcome to GozerAI, the best platform.")
        issues = [i for i in result.issues if i["category"] == "brand_name"]
        assert len(issues) == 0

    def test_wrong_casing_flagged(self):
        """Incorrectly cased brand name is flagged."""
        identity = _identity(name="GozerAI")
        validator = GuidelineValidator(identity)
        result = validator.validate_text("Welcome to gozerai, the best platform.")
        issues = [i for i in result.issues if i["category"] == "brand_name"]
        assert len(issues) >= 1
        assert "GozerAI" in issues[0]["message"]

    def test_multiple_wrong_casings(self):
        """Multiple incorrect casings are each flagged."""
        identity = _identity(name="GozerAI")
        validator = GuidelineValidator(identity)
        result = validator.validate_text("GOZERAI and gozerai are both wrong.")
        issues = [i for i in result.issues if i["category"] == "brand_name"]
        assert len(issues) == 2


class TestRepetition:
    def test_repeated_word_flagged(self):
        """Words appearing too many times are flagged."""
        identity = _identity()
        validator = GuidelineValidator(identity)
        text = " ".join(["Our platform platform platform platform platform delivers platform results."] * 4)
        result = validator.validate_text(text)
        warnings = [w for w in result.warnings if w["category"] == "repetition"]
        assert len(warnings) >= 1
        assert "platform" in warnings[0]["message"]

    def test_short_text_skips_repetition(self):
        """Very short text doesn't trigger repetition checks."""
        identity = _identity()
        validator = GuidelineValidator(identity)
        result = validator.validate_text("Hello world.")
        warnings = [w for w in result.warnings if w["category"] == "repetition"]
        assert len(warnings) == 0

    def test_varied_text_no_repetition_warning(self):
        """Well-varied text has no repetition warnings."""
        identity = _identity()
        validator = GuidelineValidator(identity)
        text = (
            "Our innovative platform delivers exceptional results for enterprise customers. "
            "The powerful analytics engine transforms raw data into actionable insights. "
            "Teams collaborate effectively using streamlined workflows and modern tools. "
            "Every feature was designed with security, scalability, and reliability in mind."
        )
        result = validator.validate_text(text)
        warnings = [w for w in result.warnings if w["category"] == "repetition"]
        assert len(warnings) == 0


class TestValidationResultScoring:
    def test_clean_text_high_score(self):
        """Clean text matching brand voice scores high."""
        identity = _identity(tone=BrandTone.PROFESSIONAL)
        validator = GuidelineValidator(identity)
        text = "Our enterprise solution provides comprehensive analytics for informed decisions."
        result = validator.validate_text(text)
        assert result.score >= 80

    def test_issues_reduce_score(self):
        """Multiple issues reduce the score."""
        identity = _identity(
            name="GozerAI",
            tone=BrandTone.PROFESSIONAL,
            avoided_words=["cheap", "bad"],
        )
        validator = GuidelineValidator(identity)
        text = "gozerai is cheap and bad. Hey gonna wanna use it."
        result = validator.validate_text(text)
        assert result.score < 80
