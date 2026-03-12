# Brandguard

**Brand identity management, guideline validation, and consistency enforcement.**

Part of the [GozerAI](https://gozerai.com) ecosystem.

## Overview

Brandguard provides a programmatic toolkit for defining, validating, and enforcing brand identity standards. It covers visual identity (colors, typography, logos), voice and tone guidelines, asset management with versioning, and automated content validation. Zero external dependencies at the library layer.

## Installation

```bash
pip install brandguard
```

For development:

```bash
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

# Get service statistics
stats = service.get_stats()
```

## Feature Tiers

| Feature | Community | Pro | Enterprise |
|---|:---:|:---:|:---:|
| Brand identity creation | x | x | x |
| Voice and tone configuration | x | x | x |
| Content validation (basic) | x | x | x |
| Asset registration | x | x | x |
| Guideline management | x | x | x |
| Basic statistics | x | x | x |
| Advanced guideline validation | | x | x |
| Consistency checking across channels | | x | x |
| Brand kit export | | x | x |
| Executive reports (CMO, CCO, CPO) | | x | x |
| Autonomous brand analysis | | x | x |
| Enterprise asset management | | | x |

### Gated Features

Pro and Enterprise features require a license key. Set the `VINZY_LICENSE_KEY` environment variable or visit [gozerai.com/pricing](https://gozerai.com/pricing) to upgrade.

## API Endpoints

Start the API server:

```bash
uvicorn brandguard.app:app --host 0.0.0.0 --port 8003
```

### Community (brandguard:basic)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/v1/identity` | Create brand identity |
| GET | `/v1/identity` | Get current identity |
| PUT | `/v1/identity/voice` | Update voice configuration |
| POST | `/v1/guidelines` | Add a guideline |
| GET | `/v1/guidelines` | List guidelines |
| POST | `/v1/assets` | Register a brand asset |
| GET | `/v1/assets` | List assets |
| GET | `/v1/stats` | Service statistics |

### Pro (brandguard:full)

| Method | Path | Description |
|---|---|---|
| POST | `/v1/validate` | Full content validation |
| POST | `/v1/consistency` | Cross-channel consistency check |
| GET | `/v1/brand-kit` | Export brand kit |
| GET | `/v1/executive/{code}` | Executive report |
| POST | `/v1/autonomous/analyze` | Autonomous brand analysis |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ZUULTIMATE_BASE_URL` | `http://localhost:8000` | Auth service URL |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `VINZY_LICENSE_KEY` | (empty) | License key for Pro/Enterprise features |
| `VINZY_SERVER` | `http://localhost:8080` | License validation server |

## Requirements

- Python >= 3.10
- No external dependencies for the library (stdlib only)
- FastAPI + httpx + slowapi for the API server

## License

MIT License. See [LICENSE](LICENSE) for details.
