from decimal import Decimal, InvalidOperation
from rules_engine.core import TaxInput


SUPPORTED_TAXPAYER_TYPES = {"salaried", "business", "individual", "company", "freelance"}
SUPPORTED_TAX_YEARS = {"2025-26", "2026-27"}
MAX_INCOME = Decimal("1000000000")  # 1 billion PKR ceiling


class ValidationError(ValueError):
    """
    Raised when tax input fails validation.

    Subclasses ValueError so that any `except ValueError` handler in the
    API layer catches this correctly. Previously this was a bare
    Exception subclass, which meant validation failures (negative
    income, unsupported tax year, etc.) bypassed every route's error
    handling and surfaced as raw 500s instead of clean 422 responses.
    """
    pass


def validate_tax_input(
    annual_income: str | int | float | Decimal,
    taxpayer_type: str,
    tax_year: str,
) -> TaxInput:
    """
    Validates and sanitizes raw input before passing to RulesEngine.
    Always call this before engine.calculate().
    Returns a clean TaxInput or raises ValidationError.
    """

    # --- Income validation ---
    try:
        raw_income = Decimal(str(annual_income))
    except InvalidOperation:
        raise ValidationError(
            f"Invalid income value: '{annual_income}'. Must be a number."
        )

    if not raw_income.is_finite():
        raise ValidationError(
            f"Income must be a finite number. Got: {annual_income}"
        )

    try:
        income = raw_income.quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValidationError(
            f"Invalid income value: '{annual_income}'. Must be a number."
        )

    if not income.is_finite():
        raise ValidationError(
            f"Income must be a finite number. Got: {annual_income}"
        )

    if income < Decimal("0"):
        raise ValidationError(
            f"Income cannot be negative. Got: {income}"
        )

    if income > MAX_INCOME:
        raise ValidationError(
            f"Income {income} exceeds maximum supported value of {MAX_INCOME}. "
            f"Contact support for high-income calculations."
        )

    # --- Taxpayer type validation ---
    taxpayer_type = taxpayer_type.strip().lower()
    if taxpayer_type not in SUPPORTED_TAXPAYER_TYPES:
        raise ValidationError(
            f"Unsupported taxpayer type: '{taxpayer_type}'. "
            f"Supported types: {sorted(SUPPORTED_TAXPAYER_TYPES)}"
        )

    # --- Tax year validation ---
    tax_year = tax_year.strip()
    if tax_year not in SUPPORTED_TAX_YEARS:
        raise ValidationError(
            f"Unsupported tax year: '{tax_year}'. "
            f"Supported years: {sorted(SUPPORTED_TAX_YEARS)}"
        )

    return TaxInput(
        annual_income=income,
        taxpayer_type=taxpayer_type,
        tax_year=tax_year,
    )