import pytest
from decimal import Decimal
from datetime import date
from rules_engine.core import RulesEngine, TaxInput, TaxRule
from rules_engine.tax_slabs import SALARIED_2025_26
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def get_verified_slabs() -> list[TaxRule]:
    """Returns slabs with ca_verified=True for testing only."""
    verified = []
    for rule in SALARIED_2025_26:
        import dataclasses
        verified.append(dataclasses.replace(rule, ca_verified=True))
    return verified
 
 
def make_engine() -> RulesEngine:
    return RulesEngine(get_verified_slabs())
 
 
def calculate(income: int) -> Decimal:
    engine = make_engine()
    result = engine.calculate(TaxInput(
        annual_income=Decimal(str(income)),
        taxpayer_type="salaried",
        tax_year="2025-26"
    ))
    return result.tax_payable
 
 
# ── Tier boundary tests ───────────────────────────────────────────────────────
 
def test_tier1_zero_tax():
    """Income at or below 600,000 = zero tax."""
    assert calculate(600000) == Decimal("0.00")
 
 
def test_tier2_lower_boundary():
    """First rupee above 600,000 triggers 1% on excess."""
    assert calculate(600001) == Decimal("0.01")
 
 
def test_tier2_midpoint():
    """900,000 income: 1% on 300,000 excess = 3,000."""
    assert calculate(900000) == Decimal("3000.00")
 
 
def test_tier2_upper_boundary():
    """1,200,000 income: 1% on 600,000 = 6,000."""
    assert calculate(1200000) == Decimal("6000.00")
 
 
def test_tier3_lower_boundary():
    """1,200,001: fixed 6,000 + 11% on 1 rupee excess."""
    assert calculate(1200001) == Decimal("6000.11")
 
 
def test_tier3_midpoint():
    """1,700,000: fixed 6,000 + 11% on 500,000 = 61,000."""
    assert calculate(1700000) == Decimal("61000.00")
 
 
def test_tier4_midpoint():
    """2,700,000: fixed 116,000 + 23% on 500,000 = 231,000."""
    assert calculate(2700000) == Decimal("231000.00")
 
 
def test_tier4_upper_boundary():
    """
    3,200,000: fixed 116,000 + 23% on 1,000,000 = 346,000.
    This must equal Tier 5 fixed_tax — confirms internal slab consistency.
    Source: FBR Circular No. 01 of 2025-26, page 4.
    """
    assert calculate(3200000) == Decimal("346000.00")
 
 
def test_tier5_lower_boundary():
    """3,200,001: fixed 346,000 + 30% on 1 rupee excess."""
    assert calculate(3200001) == Decimal("346000.30")
 
 
def test_tier5_midpoint():
    """
    3,600,000: fixed 346,000 + 30% on 400,000 = 466,000.
    Source: FBR Circular No. 01 of 2025-26, page 4.
    """
    assert calculate(3600000) == Decimal("466000.00")   # corrected from 465000
 
 
def test_tier5_upper_boundary():
    """
    4,100,000: fixed 346,000 + 30% on 900,000 = 616,000.
    This must equal Tier 6 fixed_tax — confirms internal slab consistency.
    Source: FBR Circular No. 01 of 2025-26, page 4.
    """
    assert calculate(4100000) == Decimal("616000.00")
 
 
def test_tier6_lower_boundary():
    """4,100,001: fixed 616,000 + 35% on 1 rupee excess."""
    assert calculate(4100001) == Decimal("616000.35")
 
 
def test_tier6_midpoint():
    """
    5,000,000: fixed 616,000 + 35% on 900,000 = 931,000.
    Source: FBR Circular No. 01 of 2025-26, page 4.
    """
    assert calculate(5000000) == Decimal("931000.00")   # corrected from 930000
 
 
# ── Engine safety tests ───────────────────────────────────────────────────────
 
def test_unverified_rule_raises():
    """Engine must refuse unverified rules."""
    engine = RulesEngine(SALARIED_2025_26)  # ca_verified=False
    with pytest.raises(ValueError, match="CA verified"):
        engine.calculate(TaxInput(
            annual_income=Decimal("1000000"),
            taxpayer_type="salaried",
            tax_year="2025-26"
        ))
 
 
def test_unknown_taxpayer_type_raises():
    """Engine must raise for unknown taxpayer type."""
    engine = make_engine()
    with pytest.raises(ValueError, match="No rule found"):
        engine.calculate(TaxInput(
            annual_income=Decimal("1000000"),
            taxpayer_type="unknown_type",
            tax_year="2025-26"
        ))
 
 
def test_unknown_tax_year_raises():
    """Engine must raise for unknown tax year."""
    engine = make_engine()
    with pytest.raises(ValueError, match="No rule found"):
        engine.calculate(TaxInput(
            annual_income=Decimal("1000000"),
            taxpayer_type="salaried",
            tax_year="2099-00"
        ))
 
 
# ── Audit trail test ──────────────────────────────────────────────────────────
 
def test_result_contains_audit_trail():
    """Every result must contain calculation steps."""
    engine = make_engine()
    result = engine.calculate(TaxInput(
        annual_income=Decimal("1000000"),
        taxpayer_type="salaried",
        tax_year="2025-26"
    ))
    assert len(result.calculation_steps) > 0
    assert result.source_document == "Finance Act 2025"
    assert result.ca_verified is True
 
 
# ── Validation tests ──────────────────────────────────────────────────────────
 
from rules_engine.validation import validate_tax_input, ValidationError
 
 
def test_validation_accepts_valid_input():
    result = validate_tax_input(1000000, "salaried", "2025-26")
    assert result.annual_income == Decimal("1000000.00")
    assert result.taxpayer_type == "salaried"
 
 
def test_validation_accepts_string_income():
    result = validate_tax_input("1500000", "salaried", "2025-26")
    assert result.annual_income == Decimal("1500000.00")
 
 
def test_validation_rejects_negative_income():
    with pytest.raises(ValidationError, match="negative"):
        validate_tax_input(-1000, "salaried", "2025-26")
 
 
def test_validation_rejects_invalid_income():
    with pytest.raises(ValidationError, match="Invalid income"):
        validate_tax_input("abc", "salaried", "2025-26")
 
 
def test_validation_rejects_unsupported_taxpayer():
    with pytest.raises(ValidationError, match="Unsupported taxpayer type"):
        validate_tax_input(1000000, "freelancer", "2025-26")
 
 
def test_validation_rejects_unsupported_year():
    with pytest.raises(ValidationError, match="Unsupported tax year"):
        validate_tax_input(1000000, "salaried", "2020-21")
 
 
def test_validation_normalizes_taxpayer_type():
    result = validate_tax_input(1000000, "  SALARIED  ", "2025-26")
    assert result.taxpayer_type == "salaried"
 
 
def test_validation_rejects_excessive_income():
    with pytest.raises(ValidationError, match="exceeds maximum"):
        validate_tax_input(2000000000, "salaried", "2025-26")
 

def test_validation_rejects_non_finite_income():
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError, match="finite"):
            validate_tax_input(value, "salaried", "2025-26")
