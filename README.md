# Brandguard

Brand guidelines management, asset organization, and consistency enforcement -- all in pure Python.

## Overview

Brandguard provides a programmatic toolkit for defining, validating, and enforcing brand identity standards. It covers visual identity (colors, typography, logos), voice and tone guidelines, asset management with versioning, and automated content validation against your brand rules. Zero external dependencies.

## Features

- **Brand identity management** -- Define and maintain a complete brand identity including name, mission, tagline, color palette, typography, and voice guidelines
- **Guideline validation** -- Validate text content against brand rules with a 0-100 compliance score, issue tracking, and actionable suggestions
- **Consistency checking** -- Audit content across channels (social media, email, web, advertising, print)
- **Voice and tone analysis** -- Detect mismatches between content and brand voice, flag avoided vocabulary, enforce writing style rules
- **Asset library with versioning** -- Store, organize, and retrieve brand assets (logos, icons, templates, patterns) with automatic version tracking
- **Content-type-specific rules** -- Built-in validation for social media (length, hashtags), email (greetings), and advertising (copy length)
- **Executive reporting** -- Role-specific brand reports for CMO, CCO, and CPO
- **Brand kit export** -- Comprehensive brand kit combining identity, voice, visual standards, assets, and guidelines

## Installation

```
pip install brandguard
```

For development:

```
pip install -e ".[dev]"
```

## Quick Start

```python
from brandguard import BrandService

service = BrandService()

# Create a brand identity
service.create_identity(
    name="Acme Corp",
    tagline="Building the future",
    primary_tone="professional",
    voice_attributes=["confident", "trustworthy"],
    primary_color="#1A73E8",
    primary_font="Inter",
)

# Validate content against brand guidelines
result = service.validate_content(
    content="Our innovative platform streamlines your workflow.",
    content_type="website",
)
print(result["score"])       # 0-100 compliance score
print(result["passed"])      # True if no issues found

# Register a brand asset
asset_id = service.add_asset(
    name="Primary Logo",
    asset_type="logo",
    description="Full-color horizontal logo",
)

# Generate an executive report
report = service.get_executive_report("CMO")

# Export the complete brand kit
kit = service.get_brand_kit()
```

## Architecture

```
src/brandguard/
    core.py        Data models: BrandIdentity, ColorPalette, Typography,
                   BrandAsset, BrandGuideline, BrandVoiceGuideline
    guidelines.py  GuidelineValidator, ConsistencyChecker, GuidelineManager
    assets.py      AssetManager (CRUD + versioning), AssetLibrary (collections)
    service.py     BrandService -- unified high-level API
```

## Running Tests

```
pytest tests/ -v
```

## Requirements

- Python >= 3.10
- No external dependencies (stdlib only)

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

Chris Arseno
