"""MCP Streamable HTTP deployment for the FBR tax tools.
Uses the official MCP Python SDK v2 Streamable HTTP transport.
"""
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from config.settings import settings
from src.business_tax.calculator import BusinessTaxCalculator
from src.freelance_tax.calculator import FreelanceTaxCalculator
from src.salary_tax.calculator import SalaryTaxCalculator

security = TransportSecuritySettings(
    allowed_hosts=["localhost:*", "127.0.0.1:*", "mcp:*", "mcp-server:*"],
    allowed_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
)

mcp = FastMCP(
    "FBR Tax Copilot",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=security,
)

@mcp.tool()
def calculate_salary_tax(annual_income: float, tax_year: str = "2026-27") -> dict:
    """Calculate salaried income tax using versioned deterministic rules."""
    return SalaryTaxCalculator(tax_year=tax_year, dev_mode=(settings.ENV != "production")).calculate(annual_income)

@mcp.tool()
def calculate_business_tax(net_business_income: float, tax_year: str = "2026-27") -> dict:
    """Calculate individual/business income tax using versioned deterministic rules."""
    return BusinessTaxCalculator(tax_year=tax_year, dev_mode=(settings.ENV != "production")).calculate(net_business_income)

@mcp.tool()
def calculate_it_export_tax(gross_export_proceeds: float, tax_year: str = "2026-27", atl: bool = True, pseb_registered: bool = True) -> dict:
    """Calculate Section 154A IT/ITeS export tax with explicit eligibility inputs."""
    return FreelanceTaxCalculator(tax_year=tax_year, dev_mode=(settings.ENV != "production"), atl=atl, pseb_registered=pseb_registered).calculate(gross_export_proceeds)

@mcp.tool()
def validate_calculation_result(result: dict) -> dict:
    """Validate that a result has audit fields and a non-negative tax value."""
    required = {"tax_year", "taxpayer_type", "tax_payable", "rule_applied", "source_document", "source_section", "ca_verified"}
    missing = sorted(required - set(result))
    try:
        tax = float(result.get("tax_payable", -1))
    except (TypeError, ValueError):
        tax = -1
    return {"valid": not missing and tax >= 0, "missing": missing, "tax_non_negative": tax >= 0}

app = mcp.streamable_http_app()
