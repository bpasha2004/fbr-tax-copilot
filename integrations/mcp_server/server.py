"""Official MCP server exposing safe, deterministic FBR tax tools.
Run: python -m mcp.server
"""
from mcp.server.fastmcp import FastMCP

from config.settings import settings
from src.business_tax.calculator import BusinessTaxCalculator
from src.freelance_tax.calculator import FreelanceTaxCalculator
from src.salary_tax.calculator import SalaryTaxCalculator

mcp=FastMCP("FBR Tax Copilot")

@mcp.tool()
def calculate_salary_tax(annual_income: float, tax_year: str="2026-27") -> dict:
    """Calculate salaried tax using versioned deterministic rules."""
    return SalaryTaxCalculator(tax_year=tax_year, dev_mode=(settings.ENV != "production")).calculate(annual_income)

@mcp.tool()
def calculate_business_tax(net_business_income: float, tax_year: str="2026-27") -> dict:
    """Calculate non-salaried individual/business tax using versioned rules."""
    return BusinessTaxCalculator(tax_year=tax_year, dev_mode=(settings.ENV != "production")).calculate(net_business_income)

@mcp.tool()
def calculate_it_export_tax(gross_export_proceeds: float, tax_year: str="2026-27", atl: bool=True, pseb_registered: bool=True) -> dict:
    """Calculate Section 154A IT/ITeS export tax with explicit eligibility inputs."""
    return FreelanceTaxCalculator(tax_year=tax_year, dev_mode=(settings.ENV != "production"), atl=atl, pseb_registered=pseb_registered).calculate(gross_export_proceeds)

@mcp.tool()
def validate_calculation_result(result: dict) -> dict:
    """Validate that a tool result has required audit fields and a non-negative tax value."""
    required={"tax_year","taxpayer_type","tax_payable","rule_applied","source_document","source_section","ca_verified"}
    missing=sorted(required-set(result))
    tax=float(result.get("tax_payable",-1))
    return {"valid":not missing and tax>=0,"missing":missing,"tax_non_negative":tax>=0}

if __name__=="__main__": mcp.run()
