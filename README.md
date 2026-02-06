# LLM-Assisted PRA COREP Reporting Assistant

> **A Rapid 3-Day Prototype for Automated Regulatory Reporting**

An intelligent system that uses **Google Gemini LLM** with **Retrieval-Augmented Generation (RAG)** to automatically populate the PRA COREP template **C 01.00 (Own Funds)** from bank scenario data, providing regulatory citations, confidence scoring, validation, and comprehensive audit trails.

---

## 📋 Executive Summary

This prototype demonstrates how **Large Language Models** can accelerate regulatory reporting workflows by:

- ✅ **Automating template population** — Gemini analyzes bank financial data and populates all 16 COREP C 01.00 fields
- ✅ **Providing regulatory citations** — Every value is backed by specific CRR Articles, EBA instructions, and PRA rules
- ✅ **Ensuring accuracy** — 6 validation rules check arithmetic consistency (e.g., Own Funds = Tier 1 + Tier 2)
- ✅ **Building audit trails** — Full reasoning chain from scenario data → regulatory rules → final values
- ✅ **Offering transparency** — Confidence levels (high/medium/low) flag uncertain mappings
- ✅ **Producing deliverables** — Interactive UI + downloadable 3-sheet Excel report

**Technology Stack:** Google Gemini 2.5 Flash, Streamlit, Pydantic, Python 3.11+

---

## ✅ Problem Statement Requirements — Complete

| Requirement                    | Status  | Implementation Details                                                           |
| ------------------------------ | ------- | -------------------------------------------------------------------------------- |
| **LLM-based COREP population** | ✅ Done | Gemini 2.5 Flash with structured JSON output (`engine.py`)                       |
| **RAG retrieval pipeline**     | ✅ Done | Semantic embeddings + keyword fallback for 28 regulatory chunks (`retrieval.py`) |
| **Template C 01.00 coverage**  | ✅ Done | All 16 fields: CET1, AT1, T2, deductions, formulas (`data/template_c0100.json`)  |
| **Regulatory corpus**          | ✅ Done | 28 curated chunks: CRR Articles 26-92, EBA C01.00 instructions, PRA Rulebook     |
| **Validation rules**           | ✅ Done | 6 intra-template arithmetic checks (V001-V006) in `validation.py`                |
| **Audit trail**                | ✅ Done | Per-field reasoning, citations, confidence displayed in UI and Excel             |
| **Test scenarios**             | ✅ Done | 3 scenarios: Simple CET1, Deductions, Full Capital Stack                         |
| **Interactive UI**             | ✅ Done | Streamlit with sidebar controls, styled results, real-time analysis              |
| **Excel export**               | ✅ Done | 3-sheet workbook: Populated template, Audit trail, Validation results            |
| **Confidence scoring**         | ✅ Done | High/Medium/Low per field with color coding (green/yellow/red)                   |
| **Documentation**              | ✅ Done | This README + inline code comments + architecture diagram                        |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INPUT                                  │
│  - Natural language query (e.g., "Calculate CET1 with deductions")  │
│  - Bank scenario JSON (share capital, retained earnings, etc.)      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL ENGINE (retrieval.py)                   │
│  1. Embeddings: Gemini Embedding 001 → cosine similarity (cached)   │
│  2. Keyword: Bag-of-words scoring (instant fallback)                │
│  → Returns top-6 relevant regulatory chunks                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LLM ANALYSIS ENGINE (engine.py)                  │
│  - Model: Gemini 2.5 Flash (temperature=0.2)                        │
│  - System prompt: "You are a PRA regulatory specialist..."          │
│  - Input: Query + Scenario + Retrieved passages + Template schema   │
│  - Output: Structured JSON (response_schema=AnalysisResult)          │
│  - Guarantees: Valid Pydantic model, no hallucinated fields          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   VALIDATION ENGINE (validation.py)                  │
│  - V001: r0010 = r0020 + r0500 (Own Funds = T1 + T2)                │
│  - V002: r0020 = r0030 + r0300 (T1 = CET1 + AT1)                    │
│  - V003: CET1 net calculation (instruments - deductions)            │
│  - V004: CET1 instruments breakdown                                 │
│  - V005/V006: Non-negativity checks                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       OUTPUT & EXPORT                                │
│  1. Streamlit UI: Styled table, validation metrics, audit trail     │
│  2. Excel workbook: 3 sheets (template/audit/validation)            │
│  3. Color-coded confidence: Green (high), Yellow (med), Red (low)   │
└─────────────────────────────────────────────────────────────────────┘
```

**Design Principles:**

- **Transparency:** Every value has visible reasoning + citations
- **Reliability:** Gemini's `response_schema` guarantees valid JSON structure
- **Fallback resilience:** Keyword retrieval works even if embeddings API fails
- **Caching:** Embeddings cached to disk for instant subsequent retrievals

---

## 🚀 Quick Start Guide

### Prerequisites

- **Python 3.11+** (tested on 3.11, 3.12)
- **Google AI Studio API key** (get from [aistudio.google.com/apikey](https://aistudio.google.com/apikey))
- **Windows/macOS/Linux** (cross-platform)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/suhailult777/LLM-assisted-PRA-COPREP-reporting-assistant.git
cd corep-assistant

# 2. Create virtual environment
python -m venv venv

# 3. Activate environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure API key
copy .env.example .env
# Edit .env and replace "your-gemini-api-key-here" with your actual key
```

### Running the Application

```bash
streamlit run app.py
```

The interface opens at **http://localhost:8501**

---

## 📖 User Guide

### 1. Select a Test Scenario

The sidebar provides 3 pre-built scenarios:

| Scenario                 | Description                | Tests                                                      |
| ------------------------ | -------------------------- | ---------------------------------------------------------- |
| **Simple Retail Bank**   | CET1 only, no deductions   | Basic field mapping, retained earnings, share capital      |
| **Bank with Deductions** | Goodwill, intangibles, DTA | Deduction logic (CRR Articles 36-38), negative adjustments |
| **Full Capital Stack**   | CET1 + AT1 + T2            | Complete hierarchy, Tier 1/Tier 2 structure                |

Or select **"-- Custom --"** to input your own scenario JSON.

### 2. Choose Retrieval Method

- **Auto (embeddings → keyword)** — _Recommended._ Uses Gemini Embedding 001 for semantic search, falls back to keyword matching if API fails.
- **Keyword only** — Simple bag-of-words scoring. No API calls, instant, always works.

### 3. Run Analysis

Click **"🔍 Analyse & Populate Template"**. The system will:

1. Retrieve top-6 relevant regulatory passages (~2-3s)
2. Run Gemini analysis (~10-20s depending on API speed)
3. Validate results against 6 arithmetic rules (~1s)

### 4. Review Results

The UI displays:

#### **Retrieved Regulatory Passages**

Expandable cards showing the CRR Articles, EBA instructions, and PRA rules used for reasoning.

#### **Populated Template**

Color-coded table of all 16 COREP C 01.00 fields:

- **Green background** = High confidence
- **Yellow background** = Medium confidence (judgment call)
- **Red background** = Low confidence (missing data)

#### **Validation Results**

Pass/fail status for each rule:

- ✅ **Green** = Rule passed
- ❌ **Red** = Rule failed with deviation details

#### **Audit Trail**

Per-field breakdown:

- **Reasoning** — Step-by-step logic (e.g., "Share capital £30k + premium £20k = £50k CET1 instruments")
- **Citations** — Specific regulations (e.g., "CRR Article 28", "EBA C01.00 r0040")
- **Confidence** — High/Medium/Low

### 5. Download Excel Report

Click **"📥 Download Excel Report"** to get a formatted workbook with 3 sheets:

| Sheet                  | Content                                                          |
| ---------------------- | ---------------------------------------------------------------- |
| **C 01.00 Own Funds**  | Populated template with color-coded confidence and cell comments |
| **Audit Trail**        | Reasoning and citations for every field                          |
| **Validation Results** | Pass/fail status with red/green highlighting                     |

---

## 📁 Project Structure

```
corep-assistant/
├── app.py                          # Streamlit UI (main entry point)
├── engine.py                       # Gemini LLM analysis engine
├── retrieval.py                    # RAG retrieval (embeddings + keyword)
├── validation.py                   # 6 intra-template validation rules
├── excel_export.py                 # Excel workbook generator (3 sheets)
├── models.py                       # Pydantic models (data validation + schemas)
├── requirements.txt                # Python dependencies (6 packages)
├── .env.example                    # API key template
├── .gitignore                      # Excludes venv, .env, cache
├── data/
│   ├── regulatory_corpus.json      # 28 regulatory chunks (CRR + EBA + PRA)
│   ├── template_c0100.json         # C 01.00 field definitions + formulas
│   ├── test_scenarios.json         # 3 pre-built test scenarios
│   ├── embeddings_cache.npy        # Cached embeddings (generated on first run)
│   └── embeddings_ids.json         # Chunk IDs for cache validation
├── outputs/                        # Excel exports (auto-created)
└── README.md                       # This file
```

### Key Files Explained

| File              | Purpose                                                               | Lines of Code    |
| ----------------- | --------------------------------------------------------------------- | ---------------- |
| `app.py`          | Streamlit interface with sidebar, results display, Excel download     | ~320             |
| `engine.py`       | Gemini client, prompt engineering, structured output parsing          | ~185             |
| `retrieval.py`    | Embedding generation, cosine similarity, keyword fallback             | ~225             |
| `validation.py`   | 6 validation rules (V001-V006) with tolerance checks                  | ~150             |
| `excel_export.py` | openpyxl formatting, 3-sheet workbook, color styling                  | ~180             |
| `models.py`       | Pydantic schemas (BankScenario, PopulatedField, AnalysisResult, etc.) | ~120             |
| **Total**         |                                                                       | **~1,180 lines** |

---

## 🔧 Technical Implementation

### LLM Configuration

**Model:** `gemini-2.5-flash`  
**Temperature:** 0.2 (deterministic but not completely frozen)  
**Max tokens:** 16,384 (with retry at 32,768 if truncated)  
**System instruction:**

```
You are a PRA regulatory reporting specialist with deep expertise in:
- The Capital Requirements Regulation (CRR 575/2013 as amended by CRR2)
- COREP reporting templates, specifically C 01.00 (Own Funds)
- EBA reporting instructions and validation rules
- PRA Rulebook requirements for UK-authorised firms
```

**Structured Output:**

```python
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=AnalysisResult,  # Pydantic model
    ...
)
```

This **eliminates JSON parsing errors** — Gemini's native structured output guarantees valid Pydantic models.

### RAG Retrieval Strategy

**28 curated regulatory chunks** covering:

- CRR Articles 26-92 (CET1, AT1, T2, deductions)
- EBA C 01.00 field instructions (row-by-row definitions)
- PRA Rulebook (UK-specific requirements)

**Two-tier retrieval:**

1. **Semantic (primary):** Gemini Embedding 001 → 768-dimensional vectors → cosine similarity
   - Cached to `data/embeddings_cache.npy` after first run
   - Batch size of 5 to avoid rate limits
2. **Keyword (fallback):** Bag-of-words with 3x boost for field ID matches (e.g., "r0040")

### Validation Rules

| Rule ID | Check               | Formula                                                         | Tolerance |
| ------- | ------------------- | --------------------------------------------------------------- | --------- |
| V001    | Own Funds = T1 + T2 | `r0010 = r0020 + r0500`                                         | ±0.5      |
| V002    | Tier 1 = CET1 + AT1 | `r0020 = r0030 + r0300`                                         | ±0.5      |
| V003    | CET1 net            | `r0030 = r0040 + r0100 + r0110 + r0130 - r0200 - r0210 - r0220` | ±0.5      |
| V004    | CET1 instruments    | `r0040 = r0050 + r0060 + r0070`                                 | ±0.5      |
| V005    | Non-negativity      | `r0010 >= 0`                                                    | N/A       |
| V006    | CET1 non-negativity | `r0030 >= 0`                                                    | N/A       |

**Tolerance:** ±0.5 allows for rounding differences (values in thousands GBP).

---

## 📊 Test Scenarios

### Scenario A: Simple Retail Bank

**Goal:** Test basic CET1 mapping without deductions

**Input:**

- Share capital: £30,000k
- Share premium: £20,000k
- Retained earnings: £45,000k
- AOCI: £2,000k
- Other reserves: £3,000k

**Expected CET1:** £100,000k  
**Expected Own Funds:** £100,000k (no AT1/T2)

**Validation:** All 6 rules should pass ✅

---

### Scenario B: Bank with Deductions

**Goal:** Test CRR Article 36-38 deduction logic

**Input:**

- CET1 instruments: £55,000k
- Retained earnings: £35,000k
- **Goodwill:** £8,000k (CRR Article 37)
- **Intangibles:** £3,000k (CRR Article 37(a))
- **DTA (future profit):** £2,000k (CRR Article 38)

**Expected CET1:** £81,500k (£94,500k gross - £13,000k deductions)  
**Expected Own Funds:** £81,500k

**Validation:** Tests deduction field signs (reported as positive, subtracted in formula)

---

### Scenario C: Full Capital Stack

**Goal:** Test complete Own Funds hierarchy

**Input:**

- CET1 instruments: £85,000k
- CET1 deductions: £8,500k
- **AT1 instruments:** £12,000k (CRR Articles 51-56)
- **T2 instruments:** £8,000k (CRR Articles 62-63)
- **T2 subordinated loans:** £10,000k

**Expected CET1:** £138,000k  
**Expected Tier 1:** £150,000k (£138k + £12k)  
**Expected Own Funds:** £168,000k (£150k + £18k)

**Validation:** Tests full formula chain (V001, V002, V003)

---

## 🎯 Key Features & Innovations

### 1. Guaranteed Valid Output

**Problem:** Traditional LLMs can hallucinate field IDs or produce invalid JSON.  
**Solution:** Gemini's `response_schema=PydanticModel` enforces the exact structure. No parsing errors.

### 2. Transparent Reasoning

**Problem:** "Black box" LLM outputs lack regulatory justification.  
**Solution:** Every field has explicit reasoning + CRR/EBA/PRA citations in the UI and Excel.

### 3. Confidence Scoring

**Problem:** Users can't tell when LLM is uncertain.  
**Solution:** High/Medium/Low confidence per field, color-coded. Red = review required.

### 4. Resilient Retrieval

**Problem:** Embedding APIs can fail or rate-limit.  
**Solution:** Automatic fallback to keyword matching. System always works.

### 5. Validation Safety Net

**Problem:** LLMs can make arithmetic errors.  
**Solution:** 6 post-hoc validation rules catch inconsistencies (e.g., "T1 ≠ CET1 + AT1").

---

## ⚙️ Technology Stack

| Component           | Technology              | Version | Why Chosen                                             |
| ------------------- | ----------------------- | ------- | ------------------------------------------------------ |
| **LLM**             | Google Gemini 2.5 Flash | Latest  | Native structured output, high speed, 2M token context |
| **Embeddings**      | Gemini Embedding 001    | Latest  | 768-dim vectors, matches LLM ecosystem                 |
| **Frontend**        | Streamlit               | 1.54.0  | Professional UI in pure Python, no HTML/CSS/JS needed  |
| **Data validation** | Pydantic                | 2.12.5  | Type safety, auto-validation, triples as Gemini schema |
| **Data processing** | Pandas                  | 2.3.3   | DataFrame manipulation for Excel export                |
| **Excel export**    | openpyxl                | 3.1.5   | Full formatting control (colors, comments, styles)     |
| **Environment**     | python-dotenv           | 1.0.0   | Secure API key management                              |
| **Numerics**        | NumPy                   | 2.4.2   | Cosine similarity for embeddings                       |

**Total dependencies:** 6 packages (+ their sub-dependencies)

---

## 📝 Deliverables

This repository provides:

1. ✅ **Full source code** — All 6 modules (~1,180 lines), fully commented
2. ✅ **Data files** — Regulatory corpus (28 chunks), template schema, 3 test scenarios
3. ✅ **This README** — Comprehensive documentation with architecture, usage, validation
4. ✅ **Setup files** — `requirements.txt`, `.env.example`, `.gitignore`
5. ✅ **Working prototype** — Run `streamlit run app.py` to test immediately

**Demo video:** (Add link if recorded)  
**Live deployment:** Not required per problem statement (code submission only)

---

## 🚧 Known Limitations

| Limitation                   | Impact                     | Mitigation / Future Work                                   |
| ---------------------------- | -------------------------- | ---------------------------------------------------------- |
| **Single template**          | Only C 01.00 covered       | Extend to C 02.00 (Capital Requirements), C 03.00 (Ratios) |
| **28-chunk corpus**          | Not comprehensive          | Add full EBA/PRA PDF pipeline with vector DB               |
| **No XBRL output**           | Excel only                 | Generate iXBRL for EIOPA/EBA submission systems            |
| **Session-only state**       | No persistence             | Add SQLite/PostgreSQL for audit history                    |
| **Single entity**            | No consolidation           | Support parent/subsidiary aggregation                      |
| **UK/PRA focus**             | Not ECB/SSM ready          | Add EU vs UK regulatory switching                          |
| **Prototype error handling** | Limited edge case coverage | Production-grade exception handling                        |

---

## 🔮 Future Enhancements

### Phase 2 (Short-term)

- [ ] Expand to C 02.00 and C 03.00 templates
- [ ] Add EBA DPM validation rules (cross-template checks)
- [ ] Vector database (Pinecone/ChromaDB) for full regulatory corpus
- [ ] XBRL/iXBRL output generation

### Phase 3 (Long-term)

- [ ] Multi-entity consolidation (parent/subsidiary aggregation)
- [ ] Integration with core banking systems (REST API)
- [ ] User authentication and role-based access control
- [ ] Audit log with versioning (track all report revisions)
- [ ] Multi-language support (German, French for ECB reporting)
- [ ] Advanced validation (consistency across time periods)

---

## 📄 License

This project is a prototype for demonstration purposes. All regulatory references (CRR, EBA, PRA) are © their respective copyright holders.

---

## 👨‍💻 Author

**Suhail Ult**  
GitHub: [@suhailult777](https://github.com/suhailult777)  
Repository: [LLM-assisted-PRA-COPREP-reporting-assistant](https://github.com/suhailult777/LLM-assisted-PRA-COPREP-reporting-assistant)

---

## 🙏 Acknowledgments

- **SuadeLabs/fire** — Open-source reference data for CRR capital tiers (Apache 2.0)
- **EBA** — COREP reporting framework and validation rules
- **PRA** — UK regulatory guidance for Own Funds reporting
- **Google Gemini** — Structured output and embedding APIs

---

## 📞 Support

For questions or issues:

1. Check the [GitHub Issues](https://github.com/suhailult777/LLM-assisted-PRA-COPREP-reporting-assistant/issues) page
2. Review the inline code comments in each module
3. Consult the validation rules in `validation.py` for arithmetic checks

**Setup issues?** Ensure `.env` has your Gemini API key and Python is 3.11+.  
**Runtime errors?** Check the Streamlit terminal output for stack traces.
