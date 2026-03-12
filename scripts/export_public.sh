#!/usr/bin/env bash
# export_public.sh — Creates a clean public export of Brandguard for GozerAI/brandguard.
# Usage: bash scripts/export_public.sh [target_dir]
#
# Strips proprietary Pro/Enterprise modules and internal infrastructure,
# leaving only community-tier code + the license gate (so users see the upgrade path).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-${REPO_ROOT}/../brandguard-public-export}"

echo "=== Brandguard Public Export ==="
echo "Source: ${REPO_ROOT}"
echo "Target: ${TARGET}"

# Clean target
rm -rf "${TARGET}"
mkdir -p "${TARGET}"

# Use git archive to get a clean copy (respects .gitignore, excludes .git)
cd "${REPO_ROOT}"
git archive HEAD | tar -x -C "${TARGET}"

# ===== STRIP PROPRIETARY MODULES =====

# Pro tier — advanced brand guidelines validation
rm -f "${TARGET}/src/brandguard/guidelines.py"

# Enterprise tier — enterprise asset management
rm -f "${TARGET}/src/brandguard/assets.py"

# ===== STRIP TESTS FOR PROPRIETARY MODULES =====
rm -f "${TARGET}/tests/unit/test_guidelines.py"
rm -f "${TARGET}/tests/unit/test_compliance.py"

# ===== CREATE STUB FILES FOR STRIPPED MODULES =====

for mod in guidelines assets; do
    cat > "${TARGET}/src/brandguard/${mod}.py" << 'PYEOF'
"""This module requires a commercial license.

Visit https://gozerai.com/pricing for Pro and Enterprise tier details.
Set VINZY_LICENSE_KEY to unlock licensed features.
"""

raise ImportError(
    f"{__name__} requires a commercial Brandguard license. "
    "Visit https://gozerai.com/pricing for details."
)
PYEOF
done

# ===== SANITIZE README =====
cat > "${TARGET}/README.md" << 'MDEOF'
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
MDEOF

echo ""
echo "=== Export complete: ${TARGET} ==="
echo ""
echo "Community-tier modules included:"
echo "  __init__, app, core, licensing, service"
echo ""
echo "Stripped (Pro/Enterprise):"
echo "  guidelines, assets"
