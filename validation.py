"""
Validation engine for COREP C 01.00 template.

Checks intra-template consistency rules against populated field values.
"""

from __future__ import annotations

from models import PopulatedField, ValidationResult


def _field_map(fields: list[PopulatedField]) -> dict[str, float]:
    """Build {row_id: value} lookup from populated fields."""
    m: dict[str, float] = {}
    for f in fields:
        # Store both full field_id (r0010_c0010) and just row part (r0010)
        m[f.field_id] = f.value
        row = f.field_id.split("_")[0]
        m[row] = f.value
    return m


def _get(m: dict[str, float], key: str, default: float = 0.0) -> float:
    return m.get(key, m.get(f"{key}_c0010", default))


# ---------------------------------------------------------------------------
# Individual validation rules
# ---------------------------------------------------------------------------

def _v001_own_funds(m: dict[str, float]) -> ValidationResult:
    """V001: Own Funds = Tier 1 + Tier 2"""
    r0010 = _get(m, "r0010")
    r0020 = _get(m, "r0020")
    r0500 = _get(m, "r0500")
    expected = r0020 + r0500
    passed = abs(r0010 - expected) < 0.5  # tolerance for rounding
    return ValidationResult(
        rule_id="V001",
        description="Own Funds = Tier 1 + Tier 2",
        passed=passed,
        expected=expected,
        actual=r0010,
        message="" if passed else f"r0010 ({r0010}) != r0020 ({r0020}) + r0500 ({r0500}) = {expected}",
    )


def _v002_tier1(m: dict[str, float]) -> ValidationResult:
    """V002: Tier 1 = CET1 + AT1"""
    r0020 = _get(m, "r0020")
    r0030 = _get(m, "r0030")
    r0300 = _get(m, "r0300")
    expected = r0030 + r0300
    passed = abs(r0020 - expected) < 0.5
    return ValidationResult(
        rule_id="V002",
        description="Tier 1 = CET1 + AT1",
        passed=passed,
        expected=expected,
        actual=r0020,
        message="" if passed else f"r0020 ({r0020}) != r0030 ({r0030}) + r0300 ({r0300}) = {expected}",
    )


def _v003_cet1(m: dict[str, float]) -> ValidationResult:
    """V003: CET1 = Instruments + RE + AOCI + Other Reserves - Goodwill - Intangibles - DTA"""
    r0030 = _get(m, "r0030")
    r0040 = _get(m, "r0040")
    r0100 = _get(m, "r0100")
    r0110 = _get(m, "r0110")
    r0130 = _get(m, "r0130")
    r0200 = _get(m, "r0200")
    r0210 = _get(m, "r0210")
    r0220 = _get(m, "r0220")
    expected = r0040 + r0100 + r0110 + r0130 - r0200 - r0210 - r0220
    passed = abs(r0030 - expected) < 0.5
    return ValidationResult(
        rule_id="V003",
        description="CET1 = Instruments + RE + AOCI + Reserves - Goodwill - Intangibles - DTA",
        passed=passed,
        expected=expected,
        actual=r0030,
        message="" if passed else f"r0030 ({r0030}) != calculated ({expected})",
    )


def _v004_instruments_breakdown(m: dict[str, float]) -> ValidationResult:
    """V004: CET1 instruments = sum of types"""
    r0040 = _get(m, "r0040")
    r0050 = _get(m, "r0050")
    r0060 = _get(m, "r0060")
    r0070 = _get(m, "r0070")
    expected = r0050 + r0060 + r0070
    passed = abs(r0040 - expected) < 0.5
    return ValidationResult(
        rule_id="V004",
        description="CET1 instruments = type 1 + type 2 + type 3",
        passed=passed,
        expected=expected,
        actual=r0040,
        message="" if passed else f"r0040 ({r0040}) != r0050+r0060+r0070 ({expected})",
    )


def _v005_own_funds_positive(m: dict[str, float]) -> ValidationResult:
    """V005: Own Funds >= 0"""
    r0010 = _get(m, "r0010")
    passed = r0010 >= 0
    return ValidationResult(
        rule_id="V005",
        description="Own Funds must be non-negative",
        passed=passed,
        expected=0,
        actual=r0010,
        message="" if passed else f"Own Funds ({r0010}) is negative",
    )


def _v006_cet1_positive(m: dict[str, float]) -> ValidationResult:
    """V006: CET1 >= 0"""
    r0030 = _get(m, "r0030")
    passed = r0030 >= 0
    return ValidationResult(
        rule_id="V006",
        description="CET1 must be non-negative",
        passed=passed,
        expected=0,
        actual=r0030,
        message="" if passed else f"CET1 ({r0030}) is negative",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_ALL_RULES = [
    _v001_own_funds,
    _v002_tier1,
    _v003_cet1,
    _v004_instruments_breakdown,
    _v005_own_funds_positive,
    _v006_cet1_positive,
]


def validate(fields: list[PopulatedField]) -> list[ValidationResult]:
    """Run all validation rules against populated fields. Returns list of results."""
    m = _field_map(fields)
    return [rule(m) for rule in _ALL_RULES]
