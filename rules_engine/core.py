from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


@dataclass
class TaxRule:
    """
    Single FBR tax rule. Every field is mandatory except ca_verified fields.
    No rule executes in production without ca_verified = True.
    """
    rule_id: str
    taxpayer_type: str          # salaried | business | individual | company
    tax_year: str               # e.g. "2025-26"
    income_min: Decimal
    income_max: Decimal         # use Decimal("Infinity") for top slab
    fixed_tax: Decimal          # fixed amount for this slab
    marginal_rate: Decimal      # rate applied above income_min
    source_document: str        # e.g. "Finance Act 2026"
    source_section: str         # e.g. "First Schedule, Part I, Tier 2"
    effective_date: date
    ca_verified: bool = False
    ca_name: str | None = None
    ca_verified_date: date | None = None


@dataclass
class TaxInput:
    """Input to the rules engine. AI never constructs this directly."""
    annual_income: Decimal
    taxpayer_type: str
    tax_year: str


@dataclass
class TaxResult:
    """Output from the rules engine. Immutable audit record."""
    input: TaxInput
    rule_applied: str
    source_document: str
    source_section: str
    taxable_income: Decimal
    tax_payable: Decimal
    effective_rate: Decimal
    ca_verified: bool
    calculation_steps: list[str] = field(default_factory=list)


class RulesEngine:
    """
    Deterministic tax calculation engine.
    AI never calls this directly — only via MCP tools.
    """

    def __init__(self, rules: list[TaxRule]):
        self.rules = rules

    def calculate(self, tax_input: TaxInput) -> TaxResult:
        rule = self._find_rule(tax_input)

        if rule is None:
            raise ValueError(
                f"No rule found for: {tax_input.taxpayer_type}, "
                f"{tax_input.tax_year}, income={tax_input.annual_income}"
            )

        if not rule.ca_verified:
            raise ValueError(
                f"Rule {rule.rule_id} has not been CA verified. "
                f"Cannot calculate tax with unverified rules."
            )

        return self._apply_rule(tax_input, rule)

    def _find_rule(self, tax_input: TaxInput) -> TaxRule | None:
        for rule in self.rules:
            if (
                rule.taxpayer_type == tax_input.taxpayer_type
                and rule.tax_year == tax_input.tax_year
                and rule.income_min <= tax_input.annual_income < rule.income_max
            ):
                return rule
        return None

    def _apply_rule(self, tax_input: TaxInput, rule: TaxRule) -> TaxResult:
        income = tax_input.annual_income
        excess = (income - rule.income_min).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        marginal_tax = (excess * rule.marginal_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_tax = (rule.fixed_tax + marginal_tax).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        effective_rate = (
            (total_tax / income * 100).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            if income > 0
            else Decimal(0)
        )

        steps = [
            f"Income: PKR {income:,}",
            f"Rule: {rule.rule_id} ({rule.source_section})",
            f"Fixed tax: PKR {rule.fixed_tax:,}",
            f"Excess over PKR {rule.income_min:,}: PKR {excess:,}",
            f"Marginal tax: PKR {excess:,} x {rule.marginal_rate * 100}% = PKR {marginal_tax:,}",
            f"Total tax: PKR {rule.fixed_tax:,} + PKR {marginal_tax:,} = PKR {total_tax:,}",
            f"Effective rate: {effective_rate}%",
        ]

        return TaxResult(
            input=tax_input,
            rule_applied=rule.rule_id,
            source_document=rule.source_document,
            source_section=rule.source_section,
            taxable_income=income,
            tax_payable=total_tax,
            effective_rate=effective_rate,
            ca_verified=rule.ca_verified,
            calculation_steps=steps,
        )