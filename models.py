"""
Pydantic models for the COREP Assistant.
These serve triple duty: data validation, Gemini structured output schema, and documentation.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ValidationSeverity(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"


# ---------------------------------------------------------------------------
# Template schema models
# ---------------------------------------------------------------------------

class TemplateField(BaseModel):
    """A single field (row/column) in the COREP template."""
    row_id: str
    col_id: str
    field_id: str
    name: str
    description: str
    type: str = "number"
    crr_reference: str = ""
    formula: Optional[str] = None
    sign: str = "positive"
    level: int = 0


class ValidationRule(BaseModel):
    rule_id: str
    description: str
    expression: str
    severity: str = "error"


class TemplateSchema(BaseModel):
    template_id: str
    template_name: str
    reporting_framework: str = "COREP"
    regulation: str = ""
    currency_unit: str = "thousands_GBP"
    fields: list[TemplateField]
    validation_rules: list[ValidationRule] = []


# ---------------------------------------------------------------------------
# Regulatory corpus models
# ---------------------------------------------------------------------------

class RegulatoryChunk(BaseModel):
    chunk_id: str
    text: str
    source: str
    section_ref: str
    template_id: str = ""
    keywords: list[str] = []


# ---------------------------------------------------------------------------
# Bank scenario input
# ---------------------------------------------------------------------------

class BankScenario(BaseModel):
    """Input scenario data from the user."""
    bank_name: str = "Bank"
    reporting_date: str = "2025-12-31"
    currency: str = "GBP"
    share_capital_nominal: float = 0
    share_premium: float = 0
    retained_earnings: float = 0
    accumulated_oci: float = 0
    other_reserves: float = 0
    goodwill: float = 0
    other_intangible_assets: float = 0
    deferred_tax_assets_future_profit: float = 0
    at1_instruments: float = 0
    t2_instruments: float = 0
    t2_subordinated_loans: float = 0


# ---------------------------------------------------------------------------
# LLM output models  (used as Gemini response_schema)
# ---------------------------------------------------------------------------

class PopulatedField(BaseModel):
    """A single populated template field with reasoning."""
    field_id: str = Field(description="Template field ID, e.g. r0010_c0010")
    field_name: str = Field(description="Human-readable field name")
    value: float = Field(description="Calculated value in thousands GBP")
    reasoning: str = Field(description="Step-by-step reasoning for the value")
    citations: list[str] = Field(
        description="List of regulatory references used, e.g. ['CRR Art. 26', 'C01.00 instructions']"
    )
    confidence: Confidence = Field(description="Confidence level: high, medium, or low")


class AnalysisResult(BaseModel):
    """Complete LLM analysis output for one scenario."""
    fields: list[PopulatedField] = Field(description="All populated template fields")
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings about missing data or assumptions made",
    )


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    rule_id: str
    description: str
    passed: bool
    expected: Optional[float] = None
    actual: Optional[float] = None
    message: str = ""
