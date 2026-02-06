"""
LLM analysis engine using Google Gemini.

Uses Gemini's native structured output (response_schema) to guarantee
valid JSON responses mapped directly to Pydantic models.
"""

from __future__ import annotations

import json
import pathlib
from typing import Optional

from google import genai
from google.genai import types

from models import AnalysisResult, BankScenario, PopulatedField, TemplateSchema

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEMPLATE_PATH = pathlib.Path(__file__).parent / "data" / "template_c0100.json"
GEMINI_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# System instruction
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """\
You are a PRA regulatory reporting specialist with deep expertise in:
- The Capital Requirements Regulation (CRR 575/2013 as amended by CRR2)
- COREP reporting templates, specifically C 01.00 (Own Funds)
- EBA reporting instructions and validation rules
- PRA Rulebook requirements for UK-authorised firms

Your task is to populate COREP template C 01.00 fields based on a bank scenario
and the relevant regulatory text provided. You must:

1. Map each piece of scenario data to the correct template field
2. Apply regulatory rules (e.g., deductions from CET1 under Articles 36-47)
3. Calculate derived fields using the template formulas
4. Cite the specific regulation for each decision
5. Flag any missing information or assumptions
6. Ensure internal consistency (e.g., r0010 = r0020 + r0500)

All values are in thousands of GBP. Report deduction fields as positive numbers
(they will be subtracted in the formula).
"""


# ---------------------------------------------------------------------------
# Engine class
# ---------------------------------------------------------------------------

class COREPAssistant:
    """Gemini-powered analysis engine for COREP template population."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        template_path: str | pathlib.Path = _TEMPLATE_PATH,
    ):
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.template = self._load_template(template_path)

    @staticmethod
    def _load_template(path: str | pathlib.Path) -> TemplateSchema:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return TemplateSchema(**raw)

    # ------------------------------------------------------------------
    # Build the user prompt
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        query: str,
        scenario: BankScenario,
        retrieved_docs: list[dict],
    ) -> str:
        # Regulatory context
        reg_context = "\n\n".join(
            f"[{doc['source']} — {doc['section_ref']}]\n{doc['text']}"
            for doc in retrieved_docs
        )

        # Template field definitions
        field_defs = "\n".join(
            f"  {f.field_id}: {f.name}"
            + (f" (formula: {f.formula})" if f.formula else "")
            + f" [{f.crr_reference}]"
            for f in self.template.fields
        )

        # Scenario data
        scenario_json = json.dumps(scenario.model_dump(), indent=2)

        return f"""\
USER QUERY:
{query}

BANK SCENARIO DATA (all values in thousands GBP):
{scenario_json}

RELEVANT REGULATORY TEXT:
{reg_context}

TEMPLATE FIELDS TO POPULATE ({self.template.template_id} — {self.template.template_name}):
{field_defs}

VALIDATION RULES THAT MUST HOLD:
{chr(10).join(f"  {r.rule_id}: {r.expression} — {r.description}" for r in self.template.validation_rules)}

INSTRUCTIONS:
- Populate ALL template fields listed above
- For each field, provide the value, step-by-step reasoning, and regulatory citations
- Deduction fields (goodwill, intangibles, DTA) should be reported as POSITIVE numbers
- Ensure all validation rules hold in your output
- Set confidence to "high" when the mapping is direct, "medium" when judgment is needed, "low" when data is missing
- If a field has no applicable data, set value to 0 and explain why
"""

    # ------------------------------------------------------------------
    # Run analysis
    # ------------------------------------------------------------------

    def analyze(
        self,
        query: str,
        scenario: BankScenario,
        retrieved_docs: list[dict],
    ) -> AnalysisResult:
        """
        Run Gemini analysis and return structured AnalysisResult.

        Uses Gemini's native JSON schema enforcement to guarantee valid output.
        """
        prompt = self._build_prompt(query, scenario, retrieved_docs)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=AnalysisResult,
            temperature=0.2,
            max_output_tokens=16384,
        )

        # Try up to 2 times — first attempt may truncate on very large outputs
        last_error = None
        for attempt in range(2):
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

            # Check for truncation via finish_reason
            finish_reason = None
            if response.candidates and response.candidates[0].finish_reason:
                finish_reason = response.candidates[0].finish_reason

            # response.parsed is already an AnalysisResult instance
            if response.parsed is not None:
                return response.parsed

            # Fallback: parse from text if .parsed is None
            text = response.text or ""
            if text.strip().startswith("{"):
                try:
                    return AnalysisResult.model_validate_json(text)
                except Exception as e:
                    last_error = e
                    # If truncated, retry with even higher token limit
                    if attempt == 0:
                        config = types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            response_schema=AnalysisResult,
                            temperature=0.2,
                            max_output_tokens=32768,
                        )
                        continue
                    raise

        # Last resort: return empty result with warning
        return AnalysisResult(
            fields=[],
            warnings=[
                f"LLM returned unparseable response after 2 attempts. "
                f"Last error: {last_error}. Please try again."
            ],
        )
