# Brandguard

AI brand consistency monitoring — Part of the GozerAI ecosystem.

## Overview

Brandguard provides a programmatic toolkit for defining, validating, and enforcing brand identity standards. Community tier includes core data models, the service layer, and licensing integration.

## Features (Community Tier)

- **Core data models** — BrandIdentity, ColorPalette, Typography, BrandAsset, BrandGuideline
- **Service layer** — BrandService unified high-level API
- **License integration** — Vinzy license gate for feature tiers

Pro and Enterprise tiers unlock advanced brand guidelines validation, consistency checking, asset management with versioning, and executive reporting.

Visit [gozerai.com/pricing](https://gozerai.com/pricing) for tier details.

## Installation

```
pip install brandguard
```

For development:

```
pip install -e ".[dev]"
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

## Links

- **Pricing & Licensing**: https://gozerai.com/pricing
- **Documentation**: https://gozerai.com/docs/brandguard
