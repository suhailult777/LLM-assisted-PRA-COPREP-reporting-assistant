# COREP Reporting Assistant

Prototype for LLM-assisted population of PRA COREP template C 01.00 (Own Funds). Takes bank financial data as input, retrieves relevant regulatory text, and uses Gemini to populate all 16 template fields with values, reasoning, and citations.

Built as a rapid proof-of-concept to explore how large language models can support regulatory reporting workflows.

## What it does

1. Accepts bank scenario data (share capital, retained earnings, deductions, etc.)
2. Retrieves relevant regulatory passages from a curated corpus of CRR, EBA, and PRA rules
3. Sends the scenario + retrieved context to Gemini, which returns structured field values
4. Validates the output against 6 arithmetic consistency rules
5. Displays results in a Streamlit UI and exports a formatted Excel workbook

## Architecture

```
User input (scenario JSON + query)
        |
        v
Retrieval engine -- semantic (Gemini embeddings) or keyword fallback
        |
        v
Gemini 2.5 Flash -- structured JSON output via Pydantic schema
        |
        v
Validation engine -- 6 intra-template arithmetic checks
        |
        v
Output -- Streamlit UI + 3-sheet Excel export
```

The retrieval layer uses Gemini Embedding 001 to embed the query and compute cosine similarity against a pre-embedded corpus of 28 regulatory text chunks. If the embedding API is unavailable, it falls back to keyword scoring automatically. Embeddings are cached to disk after the first run.

Gemini is configured with `response_schema=AnalysisResult` (a Pydantic model), which constrains the output to valid JSON matching the expected structure. This avoids the most common failure mode in LLM pipelines: malformed output.

## Setup

Requires Python 3.11+ and a Google AI Studio API key.

```bash
git clone https://github.com/suhailult777/LLM-assisted-PRA-COPREP-reporting-assistant.git
cd corep-assistant
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Create a `.env` file from the template and add your key:

```bash
copy .env.example .env
```

Then edit `.env`:

```
GEMINI_API_KEY=your-actual-key-here
```

Keys are available at https://aistudio.google.com/apikey

## Running

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Usage

Pick a test scenario from the sidebar (or enter custom JSON), choose a retrieval method, and hit **Analyse & Populate Template**. The app runs retrieval, LLM analysis, and validation, then displays:

- **Retrieved passages** -- the regulatory text chunks fed to Gemini
- **Populated template** -- all 16 fields with values and confidence levels
- **Validation results** -- pass/fail for each arithmetic rule
- **Audit trail** -- per-field reasoning and regulatory citations
- **Excel download** -- formatted 3-sheet workbook

## Test scenarios

Three pre-built scenarios cover the main use cases:

| Name                 | What it tests                                                   |
| -------------------- | --------------------------------------------------------------- |
| Simple Retail Bank   | CET1 only, no deductions. Basic field mapping.                  |
| Bank with Deductions | Goodwill, intangibles, DTA deductions under CRR Articles 36-38. |
| Full Capital Stack   | CET1 + AT1 + T2. Tests the complete Own Funds hierarchy.        |

Expected values are documented in `data/test_scenarios.json` with min/max ranges for each field.

## Project structure

```
corep-assistant/
    app.py                  Streamlit UI
    engine.py               Gemini analysis engine
    retrieval.py            Embedding + keyword retrieval
    validation.py           Intra-template validation rules
    excel_export.py         Excel workbook generator
    models.py               Pydantic data models
    requirements.txt
    .env.example
    data/
        regulatory_corpus.json   28 regulatory text chunks
        template_c0100.json      Field definitions and formulas
        test_scenarios.json      3 test scenarios with expected values
```

## How the pieces fit together

**models.py** defines all shared data structures: `BankScenario` for input, `PopulatedField` for individual field results, `AnalysisResult` as the top-level Gemini response schema, and `ValidationResult` for rule outcomes. These models do triple duty -- they validate input data, define the Gemini output schema, and structure the Excel export.

**retrieval.py** loads the regulatory corpus and provides two retrieval strategies. The semantic path embeds the query via Gemini Embedding 001 and ranks chunks by cosine similarity. The keyword path scores chunks by word overlap with a boost for field ID matches (e.g., "r0040"). The `retrieve()` method tries semantic first and falls back to keyword on failure.

**engine.py** builds a detailed prompt containing the query, scenario data, retrieved regulatory text, template field definitions, and validation rules. It sends this to Gemini 2.5 Flash with `response_schema=AnalysisResult`, which forces the model to return valid structured JSON. If the output is truncated (can happen with very detailed reasoning), it retries with a higher token limit.

**validation.py** checks the populated field values against 6 rules:

| Rule | Check                                                                 |
| ---- | --------------------------------------------------------------------- |
| V001 | Own Funds = Tier 1 + Tier 2                                           |
| V002 | Tier 1 = CET1 + AT1                                                   |
| V003 | CET1 = instruments + retained earnings + AOCI + reserves - deductions |
| V004 | CET1 instruments = sum of sub-types                                   |
| V005 | Own Funds >= 0                                                        |
| V006 | CET1 >= 0                                                             |

Rules V001-V004 have a tolerance of 0.5 to account for rounding.

**excel_export.py** generates a workbook with three sheets: the populated template (with confidence color coding and cell comments), an audit trail (reasoning and citations per field), and validation results (pass/fail with highlighting).

**app.py** ties everything together in a Streamlit interface. Components are cached with `@st.cache_resource` so the Gemini client and retriever are only initialized once per session.

## Regulatory corpus

The retrieval corpus (`data/regulatory_corpus.json`) contains 28 curated text chunks drawn from:

- **CRR (575/2013)** -- Articles 26-92 covering CET1 definitions, instrument conditions, retained earnings, AOCI, deductions (goodwill, intangibles, DTA), AT1 and T2 definitions, own funds aggregation, and capital ratio requirements
- **EBA reporting instructions** -- Row-by-row field definitions for C 01.00, template hierarchy, validation rules
- **PRA Rulebook** -- UK-specific reporting requirements and submission rules

Each chunk is tagged with source, section reference, template ID, and keywords for both retrieval strategies.

## Technology choices

| Component  | Choice               | Rationale                                                            |
| ---------- | -------------------- | -------------------------------------------------------------------- |
| LLM        | Gemini 2.5 Flash     | Native structured output via Pydantic schema, no JSON parsing needed |
| Embeddings | Gemini Embedding 001 | Same API ecosystem, 768-dim vectors                                  |
| UI         | Streamlit            | Fast to build, runs locally, no frontend code required               |
| Validation | Pure Python          | 6 rules, no framework overhead needed                                |
| Export     | openpyxl             | Full control over Excel formatting, comments, and styling            |
| Models     | Pydantic v2          | Shared between input validation, LLM schema, and export logic        |

## Dependencies

```
google-genai>=1.0.0
streamlit>=1.30.0
pandas>=2.0.0
openpyxl>=3.1.0
numpy>=1.24.0
python-dotenv>=1.0.0
```

## Limitations

- Only covers template C 01.00 (Own Funds). Does not handle C 02.00 through C 09.02.
- The regulatory corpus is 28 hand-curated chunks, not a full document pipeline.
- Output is Excel only, no XBRL or iXBRL generation.
- Single reporting entity. No consolidated/solo switching or group aggregation.
- Session-based state only. No database persistence or version history.
- Prototype-level error handling. Not hardened for production use.

## Possible extensions

- Additional COREP templates (C 02.00 Capital Requirements, C 03.00 Capital Ratios)
- Vector database (ChromaDB, Pinecone) for a larger regulatory corpus
- XBRL/iXBRL output for regulatory submission systems
- Multi-entity consolidation support
- REST API integration with core banking systems
- Cross-template validation (EBA DPM rules)

## Author

Suhail -- [@suhailult777](https://github.com/suhailult777)
