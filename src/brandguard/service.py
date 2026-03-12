"""
Brand Service - High-level service interface for executives.

Provides a unified API for teams to interact with
brand management and consistency enforcement.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from brandguard.core import (
    BrandIdentity,
    BrandAsset,
    BrandAssetType,
    BrandGuideline,
    BrandVoiceGuideline,
    BrandTone,
    BrandVoice,
    ColorPalette,
    ColorValue,
    Typography,
    FontFamily,
    ContentType,
)
from brandguard.guidelines import (
    ComplianceReporter,
    GuidelineManager,
    GuidelineValidator,
    ConsistencyChecker,
    ValidationResult,
)
from brandguard.assets import (
    AssetManager,
    AssetLibrary,
)
from brandguard.licensing import license_gate

logger = logging.getLogger(__name__)

# Optional telemetry
try:
    from gozerai_telemetry import get_collector, Tracer

    _collector = get_collector("brandguard")
    _tracer = Tracer("brandguard")
    _validations_counter = _collector.counter("validations_total", "Total content validations")
    _assets_gauge = _collector.gauge("assets_count", "Total brand assets")
    _guidelines_gauge = _collector.gauge("guidelines_count", "Total guidelines")
    _HAS_TELEMETRY = True
except ImportError:
    _HAS_TELEMETRY = False


class BrandService:
    """
    High-level brand management service.

    This service provides a unified interface for:
    - CMO (Echo): Brand strategy, voice guidelines, marketing materials
    - CCO (Artisan): Content consistency, asset management
    - CPO (Visionary): Product branding, visual identity

    Example:
        ```python
        service = BrandService()

        # Create brand identity
        service.create_identity(
            name="TechCorp",
            tagline="Innovation for Everyone",
            primary_tone="professional",
        )

        # Validate content
        result = service.validate_content(
            "Check out our amazing new product!",
            content_type="social_media",
        )

        # Get brand report for CMO
        report = service.get_executive_report("CMO")
        ```
    """

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the brand service."""
        self._storage_path = Path(storage_path) if storage_path else None
        self._identity_file = self._storage_path / "identity.json" if self._storage_path else None
        self._identity: Optional[BrandIdentity] = None
        self._guideline_manager = GuidelineManager()
        self._asset_library = AssetLibrary(self._storage_path)

        self._initialized = False

        # Auto-load persisted identity
        if self._identity_file and self._identity_file.exists():
            self._load_identity()

    def _save_identity(self) -> None:
        """Persist identity to JSON file."""
        if not self._identity_file or not self._identity:
            return
        try:
            self._identity_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "name": self._identity.name,
                "description": self._identity.description,
                "version": self._identity.version,
                "voice": {
                    "primary_tone": self._identity.voice_guidelines.primary_tone.value,
                    "tagline": self._identity.voice_guidelines.tagline,
                    "mission_statement": self._identity.voice_guidelines.mission_statement,
                    "preferred_words": self._identity.voice_guidelines.preferred_words,
                    "avoided_words": self._identity.voice_guidelines.avoided_words,
                    "sentence_length": self._identity.voice_guidelines.sentence_length,
                    "use_contractions": self._identity.voice_guidelines.use_contractions,
                    "use_active_voice": self._identity.voice_guidelines.use_active_voice,
                },
                "color_palette": self._identity.color_palette.to_dict(),
                "typography": self._identity.typography.to_dict(),
            }
            with open(self._identity_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved identity to {self._identity_file}")
        except Exception as e:
            logger.error(f"Failed to save identity: {e}")

    def _load_identity(self) -> None:
        """Load identity from JSON file."""
        if not self._identity_file or not self._identity_file.exists():
            return
        try:
            with open(self._identity_file) as f:
                data = json.load(f)

            tone_map = {t.value: t for t in BrandTone}
            voice_data = data.get("voice", {})

            voice = BrandVoiceGuideline(
                primary_tone=tone_map.get(voice_data.get("primary_tone", ""), BrandTone.PROFESSIONAL),
                tagline=voice_data.get("tagline", ""),
                mission_statement=voice_data.get("mission_statement", ""),
                preferred_words=voice_data.get("preferred_words", []),
                avoided_words=voice_data.get("avoided_words", []),
                sentence_length=voice_data.get("sentence_length", "medium"),
                use_contractions=voice_data.get("use_contractions", True),
                use_active_voice=voice_data.get("use_active_voice", True),
            )

            palette = ColorPalette(name=data.get("name", "Default") + " Palette")
            typography = Typography()

            self._identity = BrandIdentity(
                name=data.get("name", ""),
                description=data.get("description", ""),
                version=data.get("version", "1.0"),
                voice_guidelines=voice,
                color_palette=palette,
                typography=typography,
            )
            self._initialized = True
            logger.info(f"Loaded identity '{self._identity.name}' from {self._identity_file}")
        except Exception as e:
            logger.error(f"Failed to load identity: {e}")

    def create_identity(
        self,
        name: str,
        tagline: str = "",
        mission: str = "",
        primary_tone: str = "professional",
        voice_attributes: Optional[List[str]] = None,
        primary_color: Optional[str] = None,
        primary_font: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new brand identity.

        Args:
            name: Brand name
            tagline: Brand tagline
            mission: Mission statement
            primary_tone: Primary brand tone
            voice_attributes: List of voice characteristics
            primary_color: Primary brand color (hex)
            primary_font: Primary font family name

        Returns:
            Created identity summary
        """
        # Create voice guidelines
        tone_map = {
            "professional": BrandTone.PROFESSIONAL,
            "friendly": BrandTone.FRIENDLY,
            "authoritative": BrandTone.AUTHORITATIVE,
            "playful": BrandTone.PLAYFUL,
            "inspirational": BrandTone.INSPIRATIONAL,
            "casual": BrandTone.CASUAL,
        }

        voice_map = {
            "confident": BrandVoice.CONFIDENT,
            "approachable": BrandVoice.APPROACHABLE,
            "innovative": BrandVoice.INNOVATIVE,
            "trustworthy": BrandVoice.TRUSTWORTHY,
            "expert": BrandVoice.EXPERT,
        }

        voice = BrandVoiceGuideline(
            primary_tone=tone_map.get(primary_tone, BrandTone.PROFESSIONAL),
            voice_attributes=[
                voice_map.get(v, BrandVoice.CONFIDENT)
                for v in (voice_attributes or [])
                if v in voice_map
            ],
            tagline=tagline,
            mission_statement=mission,
        )

        # Create color palette
        palette = ColorPalette(name=f"{name} Palette")
        if primary_color:
            palette.primary = ColorValue(
                name="Primary",
                hex=primary_color,
                usage="primary",
            )

        # Create typography
        typography = Typography()
        if primary_font:
            typography.primary_font = FontFamily(
                name=primary_font,
                category="sans-serif",
            )

        # Create identity
        self._identity = BrandIdentity(
            name=name,
            description=mission,
            voice_guidelines=voice,
            color_palette=palette,
            typography=typography,
        )

        self._initialized = True
        self._save_identity()
        logger.info(f"Created brand identity: {name}")

        return self._identity.to_dict()

    def get_identity(self) -> Optional[Dict[str, Any]]:
        """Get current brand identity."""
        if not self._identity:
            return None
        return self._identity.to_dict()

    def update_voice(
        self,
        tagline: Optional[str] = None,
        mission: Optional[str] = None,
        primary_tone: Optional[str] = None,
        preferred_words: Optional[List[str]] = None,
        avoided_words: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update brand voice guidelines."""
        if not self._identity:
            return {"error": "No brand identity created"}

        voice = self._identity.voice_guidelines

        if tagline:
            voice.tagline = tagline
        if mission:
            voice.mission_statement = mission
        if primary_tone:
            tone_map = {
                "professional": BrandTone.PROFESSIONAL,
                "friendly": BrandTone.FRIENDLY,
                "casual": BrandTone.CASUAL,
            }
            voice.primary_tone = tone_map.get(primary_tone, voice.primary_tone)
        if preferred_words:
            voice.preferred_words.extend(preferred_words)
        if avoided_words:
            voice.avoided_words.extend(avoided_words)

        self._save_identity()
        return voice.to_dict()

    def validate_content(
        self,
        content: str,
        content_type: str = "website",
    ) -> Dict[str, Any]:
        """
        Validate content against brand guidelines.

        Args:
            content: Text content to validate
            content_type: Type of content

        Returns:
            Validation result
        """
        license_gate.gate("std.brandguard.advanced")
        if not self._identity:
            return {"error": "No brand identity created", "passed": False}

        type_map = {
            "social_media": ContentType.SOCIAL_MEDIA,
            "email": ContentType.EMAIL,
            "website": ContentType.WEBSITE,
            "blog": ContentType.BLOG,
            "advertising": ContentType.ADVERTISING,
        }
        ct = type_map.get(content_type, ContentType.WEBSITE)

        if _HAS_TELEMETRY:
            _validations_counter.inc()

        validator = GuidelineValidator(self._identity)
        result = validator.validate_text(content, ct)

        return result.to_dict()

    def check_consistency(
        self,
        content_samples: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Check brand consistency across content samples.

        Args:
            content_samples: List of {type, text, name} dicts

        Returns:
            Consistency report
        """
        license_gate.gate("std.brandguard.advanced")
        if not self._identity:
            return {"error": "No brand identity created"}

        checker = ConsistencyChecker(self._identity)
        return checker.generate_consistency_report(content_samples)

    def generate_compliance_report(
        self,
        content_samples: List[Dict[str, str]],
        report_name: str = "Brand Compliance Report",
    ) -> Dict[str, Any]:
        """
        Generate a structured compliance report for content.

        Args:
            content_samples: List of {name, text, type} dicts
            report_name: Title for the report

        Returns:
            Compliance report with scores, issues, and recommendations
        """
        license_gate.gate("std.brandguard.advanced")
        if not self._identity:
            return {"error": "No brand identity created"}

        reporter = ComplianceReporter(self._identity)
        return reporter.generate_report(content_samples, report_name)

    def add_guideline(
        self,
        category: str,
        title: str,
        description: str,
        rule_type: str = "guideline",
        priority: str = "normal",
        enforcement: str = "recommended",
        applies_to: Optional[List[str]] = None,
    ) -> str:
        """
        Add a brand guideline.

        Args:
            category: Guideline category (logo, color, voice, etc.)
            title: Guideline title
            description: Full description
            rule_type: Type (guideline, requirement, prohibition)
            priority: Priority level
            enforcement: Enforcement level
            applies_to: List of content types

        Returns:
            Guideline ID
        """
        type_map = {
            "social_media": ContentType.SOCIAL_MEDIA,
            "email": ContentType.EMAIL,
            "website": ContentType.WEBSITE,
        }

        guideline = BrandGuideline(
            category=category,
            title=title,
            description=description,
            rule_type=rule_type,
            priority=priority,
            enforcement=enforcement,
            applies_to=[type_map[t] for t in (applies_to or []) if t in type_map],
        )

        self._guideline_manager.add_guideline(guideline)

        if self._identity:
            self._identity.guidelines.append(guideline)

        if _HAS_TELEMETRY:
            _guidelines_gauge.set(len(self._guideline_manager.list_all()))

        return guideline.id

    def get_guidelines(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get brand guidelines."""
        if category:
            guidelines = self._guideline_manager.get_by_category(category)
        else:
            guidelines = self._guideline_manager.list_all()

        return [g.to_dict() for g in guidelines]

    def add_asset(
        self,
        name: str,
        asset_type: str,
        description: str = "",
        file_url: Optional[str] = None,
        usage_guidelines: str = "",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Add a brand asset.

        Args:
            name: Asset name
            asset_type: Type of asset
            description: Asset description
            file_url: URL to asset file
            usage_guidelines: Usage guidelines
            tags: Asset tags

        Returns:
            Asset ID
        """
        type_map = {
            "logo": BrandAssetType.LOGO,
            "logo_variant": BrandAssetType.LOGO_VARIANT,
            "icon": BrandAssetType.ICON,
            "template": BrandAssetType.TEMPLATE,
            "pattern": BrandAssetType.PATTERN,
        }

        asset = BrandAsset(
            name=name,
            description=description,
            asset_type=type_map.get(asset_type, BrandAssetType.LOGO),
            file_url=file_url,
            usage_guidelines=usage_guidelines,
            tags=tags or [],
        )

        asset_id = self._asset_library.add_asset(asset)

        if self._identity:
            self._identity.assets.append(asset)

        if _HAS_TELEMETRY:
            _assets_gauge.set(len(self._asset_library._manager.list_all()))

        return asset_id

    def get_assets(
        self,
        asset_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get brand assets."""
        if asset_type:
            type_map = {
                "logo": BrandAssetType.LOGO,
                "icon": BrandAssetType.ICON,
                "template": BrandAssetType.TEMPLATE,
            }
            at = type_map.get(asset_type)
            if at:
                assets = self._asset_library._manager.get_by_type(at)
            else:
                assets = []
        else:
            assets = self._asset_library._manager.list_all()

        return [a.to_dict() for a in assets]

    def get_brand_kit(self) -> Dict[str, Any]:
        """
        Get complete brand kit for export/sharing.

        Returns comprehensive brand information for use
        by designers, marketers, and content creators.
        """
        license_gate.gate("std.brandguard.advanced")
        if not self._identity:
            return {"error": "No brand identity created"}

        return {
            "name": self._identity.name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "identity": self._identity.to_dict(),
            "voice": {
                "guidelines": self._identity.voice_guidelines.to_dict(),
                "key_messages": self._identity.voice_guidelines.key_messages,
                "vocabulary": {
                    "preferred": self._identity.voice_guidelines.preferred_words,
                    "avoided": self._identity.voice_guidelines.avoided_words,
                },
            },
            "visual": {
                "colors": self._identity.color_palette.to_dict(),
                "typography": self._identity.typography.to_dict(),
            },
            "assets": {
                "logos": [a.to_dict() for a in self._asset_library.get_logos()],
                "icons": [a.to_dict() for a in self._asset_library.get_icons()],
                "templates": [a.to_dict() for a in self._asset_library.get_templates()],
            },
            "guidelines": [g.to_dict() for g in self._guideline_manager.list_all()],
        }

    def get_executive_report(self, executive_code: str) -> Dict[str, Any]:
        """
        Generate a report tailored for a specific executive.

        Args:
            executive_code: The executive code (CMO, CCO, CPO)

        Returns:
            Executive-specific brand report
        """
        license_gate.gate("std.brandguard.enterprise")
        if not self._identity:
            return {"error": "No brand identity created"}

        base_info = {
            "brand_name": self._identity.name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if executive_code == "CMO":
            # Marketing focus: voice, messaging, campaigns
            return {
                "executive": "CMO",
                "focus": "Brand Voice & Marketing",
                **base_info,
                "brand_voice": {
                    "primary_tone": self._identity.voice_guidelines.primary_tone.value,
                    "tagline": self._identity.voice_guidelines.tagline,
                    "key_messages": self._identity.voice_guidelines.key_messages,
                    "value_propositions": self._identity.voice_guidelines.value_propositions,
                },
                "messaging_toolkit": {
                    "preferred_vocabulary": self._identity.voice_guidelines.preferred_words[:10],
                    "avoided_vocabulary": self._identity.voice_guidelines.avoided_words[:10],
                },
                "campaign_assets": {
                    "social_media": [a.to_dict() for a in self._asset_library.get_for_social_media()],
                    "templates": [a.to_dict() for a in self._asset_library.get_templates()],
                },
                "guidelines_summary": {
                    "total": len(self._guideline_manager.list_all()),
                    "required": len(self._guideline_manager.get_required_guidelines()),
                },
            }

        elif executive_code == "CCO":
            # Content focus: consistency, assets, quality
            return {
                "executive": "CCO",
                "focus": "Content & Consistency",
                **base_info,
                "content_standards": {
                    "writing_style": {
                        "sentence_length": self._identity.voice_guidelines.sentence_length,
                        "use_contractions": self._identity.voice_guidelines.use_contractions,
                        "use_active_voice": self._identity.voice_guidelines.use_active_voice,
                    },
                },
                "asset_library": self._asset_library.generate_asset_report(),
                "guidelines": {
                    "by_category": self._guideline_manager.get_stats().get("by_category", {}),
                    "required": [
                        g.to_dict() for g in self._guideline_manager.get_required_guidelines()
                    ],
                },
                "quality_checklist": [
                    "Verify voice alignment",
                    "Check color consistency",
                    "Validate typography usage",
                    "Confirm logo placement",
                ],
            }

        elif executive_code == "CPO":
            # Product focus: visual identity, product branding
            return {
                "executive": "CPO",
                "focus": "Product & Visual Identity",
                **base_info,
                "visual_identity": {
                    "color_palette": self._identity.color_palette.to_dict(),
                    "typography": self._identity.typography.to_dict(),
                },
                "product_branding": {
                    "logos": [a.to_dict() for a in self._asset_library.get_logos()],
                    "icons": [a.to_dict() for a in self._asset_library.get_icons()],
                },
                "brand_application": {
                    "digital": {
                        "colors": [c.hex for c in self._identity.color_palette.get_all_colors()],
                        "fonts": [self._identity.typography.primary_font.name],
                    },
                    "print": [a.to_dict() for a in self._asset_library.get_for_print()],
                },
            }

        else:
            # Default: full brand kit
            return self.get_brand_kit()

    def get_telemetry(self) -> Dict[str, Any]:
        """Get telemetry data (metrics + traces). Returns empty dict if telemetry not installed."""
        if not _HAS_TELEMETRY:
            return {}
        return {
            "metrics": _collector.to_dict(),
            "traces": len(_tracer.get_completed()),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "initialized": self._initialized,
            "has_identity": self._identity is not None,
            "guidelines": self._guideline_manager.get_stats(),
            "assets": self._asset_library.get_stats(),
        }

    def run_autonomous_analysis(self) -> Dict[str, Any]:
        """
        Run autonomous brand analysis.

        Performs real brand health checks including identity completeness,
        guideline coverage, and sample content validation.
        """
        license_gate.gate("std.brandguard.enterprise")
        if not self._identity:
            return {"error": "No brand identity created"}

        guidelines = self._guideline_manager.list_all()
        assets = self._asset_library._manager.list_all()
        recommendations = []
        health_score = 100.0

        # Check identity completeness
        identity_checks = {
            "has_name": bool(self._identity.name),
            "has_tagline": bool(self._identity.voice_guidelines.tagline),
            "has_mission": bool(self._identity.voice_guidelines.mission_statement),
            "has_colors": bool(self._identity.color_palette.primary),
            "has_typography": bool(self._identity.typography.primary_font),
        }
        completeness = sum(identity_checks.values()) / len(identity_checks) * 100
        if completeness < 100:
            missing = [k.replace("has_", "") for k, v in identity_checks.items() if not v]
            recommendations.append(
                f"Complete brand identity — missing: {', '.join(missing)}"
            )
            health_score -= (100 - completeness) * 0.2

        # Check guideline coverage
        guideline_categories = {g.category for g in guidelines} if guidelines else set()
        expected_categories = {"voice", "visual", "content"}
        missing_categories = expected_categories - guideline_categories
        if missing_categories:
            recommendations.append(
                f"Add guidelines for: {', '.join(sorted(missing_categories))}"
            )
            health_score -= len(missing_categories) * 5

        if len(guidelines) == 0:
            recommendations.append("Define at least 3 brand guidelines")
            health_score -= 10

        # Check asset library
        if len(assets) == 0:
            recommendations.append("Upload brand assets (logo, colors, fonts)")
            health_score -= 5

        # Run sample validation against brand name
        brand_name = self._identity.name
        sample_texts = [
            f"Welcome to {brand_name}, your trusted partner.",
            f"At {brand_name.lower()}, we believe in excellence.",
            f"Contact {brand_name.upper()} for more information.",
        ]

        validation_results = []
        for text in sample_texts:
            result = self.validate_content(content=text, content_type="website")
            if isinstance(result, dict) and "score" in result:
                validation_results.append(result)

        avg_validation_score = 0.0
        if validation_results:
            avg_validation_score = sum(
                r.get("score", 0) for r in validation_results
            ) / len(validation_results)
            if avg_validation_score < 80:
                health_score -= (80 - avg_validation_score) * 0.3
                recommendations.append(
                    f"Content validation average is {avg_validation_score:.0f}/100 — review brand name consistency"
                )

        health_score = max(0.0, min(100.0, health_score))

        if not recommendations:
            recommendations.append("Brand health is strong — no issues detected")

        return {
            "cycle_completed_at": datetime.now(timezone.utc).isoformat(),
            "health_score": round(health_score, 1),
            "brand_health": {
                "identity_completeness": completeness,
                "identity_checks": identity_checks,
                "guidelines_defined": len(guidelines),
                "guideline_categories": sorted(guideline_categories),
                "assets_available": len(assets),
                "avg_validation_score": round(avg_validation_score, 1),
            },
            "recommendations": recommendations,
        }
