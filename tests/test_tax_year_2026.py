from decimal import Decimal
from rules_engine.tax_slabs import get_rules_for_year
from rules_engine.core import RulesEngine, TaxInput

def test_current_year_salary_has_eight_slabs():
    rules=get_rules_for_year("2026-27","salaried")
    assert len(rules)==8
    assert rules[3].marginal_rate==Decimal("0.20")
    assert rules[-1].income_min==Decimal("7000000")

def test_salary_3_2m_boundary():
    rules=[__import__('dataclasses').replace(r,ca_verified=True) for r in get_rules_for_year("2026-27","salaried")]
    result=RulesEngine(rules).calculate(TaxInput(Decimal("3200000"),"salaried","2026-27"))
    assert result.tax_payable==Decimal("316000.00")

def test_salary_7m_boundary():
    rules=[__import__('dataclasses').replace(r,ca_verified=True) for r in get_rules_for_year("2026-27","salaried")]
    result=RulesEngine(rules).calculate(TaxInput(Decimal("7000000"),"salaried","2026-27"))
    assert result.tax_payable==Decimal("1424000.00")
