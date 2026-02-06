"""
COREP Assistant — Streamlit Application

Single-file Streamlit app providing:
  1. Scenario input (preset or custom JSON)
  2. Regulatory passage retrieval display
  3. Populated template table with confidence indicators
  4. Validation results (pass/fail)
  5. Audit trail with reasoning + citations
  6. Excel download
"""

from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from models import AnalysisResult, BankScenario, PopulatedField
from retrieval import SimpleRetriever
from engine import COREPAssistant
from validation import validate
from excel_export import generate_excel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

APP_DIR = pathlib.Path(__file__).parent
SCENARIOS_PATH = APP_DIR / "data" / "test_scenarios.json"

st.set_page_config(
    page_title="COREP Assistant",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Caching: initialise Gemini client, retriever, and engine once
# ---------------------------------------------------------------------------

@st.cache_resource
def get_gemini_client():
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


@st.cache_resource
def get_retriever():
    client = get_gemini_client()
    return SimpleRetriever(gemini_client=client)


@st.cache_resource
def get_engine():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    return COREPAssistant(api_key=api_key)


def load_test_scenarios() -> list[dict]:
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> tuple[str, dict]:
    """Render sidebar and return (query, scenario_dict)."""
    st.sidebar.title("🏦 COREP Assistant")
    st.sidebar.caption("LLM-Assisted PRA Regulatory Reporting")

    st.sidebar.markdown("---")

    # API key status
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        st.sidebar.success("Gemini API key loaded", icon="✅")
    else:
        st.sidebar.error("No API key found. Set GEMINI_API_KEY in .env", icon="🔑")
        entered_key = st.sidebar.text_input("Enter Gemini API key:", type="password")
        if entered_key:
            os.environ["GEMINI_API_KEY"] = entered_key
            st.rerun()

    st.sidebar.markdown("---")

    # Scenario selection
    scenarios = load_test_scenarios()
    scenario_names = ["-- Custom --"] + [s["name"] for s in scenarios]
    selected = st.sidebar.selectbox("Select test scenario:", scenario_names)

    if selected != "-- Custom --":
        idx = scenario_names.index(selected) - 1
        s = scenarios[idx]
        query = s["query"]
        scenario_data = s["scenario_data"]
        st.sidebar.info(f"**{s['name']}**\n\n{s['description']}")
    else:
        query = ""
        scenario_data = {
            "bank_name": "My Bank plc",
            "reporting_date": "2025-12-31",
            "currency": "GBP",
            "share_capital_nominal": 50000,
            "share_premium": 10000,
            "retained_earnings": 30000,
            "accumulated_oci": 0,
            "other_reserves": 5000,
            "goodwill": 0,
            "other_intangible_assets": 0,
            "deferred_tax_assets_future_profit": 0,
            "at1_instruments": 0,
            "t2_instruments": 0,
            "t2_subordinated_loans": 0,
        }

    st.sidebar.markdown("---")

    # Retrieval method
    method = st.sidebar.radio(
        "Retrieval method:",
        ["Auto (embeddings → keyword)", "Keyword only"],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Built for PRA COREP demonstration")

    retrieval_method = "auto" if "Auto" in method else "keyword"
    return query, scenario_data, retrieval_method


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

def render_main(default_query: str, default_scenario: dict, retrieval_method: str):
    st.title("LLM-Assisted COREP Reporting Assistant")
    st.caption("Prototype — Template C 01.00 (Own Funds)")

    # ── Input Section ──────────────────────────────────────────────────
    with st.container():
        st.subheader("1. Input Scenario")
        col1, col2 = st.columns([1, 1])

        with col1:
            query = st.text_area(
                "Query / Question:",
                value=default_query,
                height=100,
                placeholder="e.g., Calculate CET1 capital for a retail bank with share capital of £50m...",
            )

        with col2:
            scenario_json = st.text_area(
                "Scenario Data (JSON):",
                value=json.dumps(default_scenario, indent=2),
                height=250,
            )

    # Validate JSON
    try:
        scenario_dict = json.loads(scenario_json)
    except json.JSONDecodeError:
        st.error("Invalid JSON in scenario field. Please fix and try again.")
        return

    # ── Run button ─────────────────────────────────────────────────────
    run_pressed = st.button(
        "🔍 Analyse & Populate Template",
        type="primary",
        use_container_width=True,
    )

    if not run_pressed and "result" not in st.session_state:
        st.info("Select a scenario from the sidebar (or enter custom data) and click **Analyse**.")
        return

    if run_pressed:
        engine = get_engine()
        if engine is None:
            st.error("No Gemini API key configured. Cannot run analysis.")
            return

        retriever = get_retriever()
        scenario = BankScenario(**scenario_dict)

        with st.spinner("Retrieving regulatory passages..."):
            retrieved_docs = retriever.retrieve(query, top_k=6, method=retrieval_method)

        with st.spinner("Running Gemini analysis (10-20s)..."):
            result = engine.analyze(query, scenario, retrieved_docs)

        with st.spinner("Running validation checks..."):
            val_results = validate(result.fields)

        # Store in session
        st.session_state["result"] = result
        st.session_state["retrieved_docs"] = retrieved_docs
        st.session_state["val_results"] = val_results
        st.session_state["session_id"] = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # ── Display results ────────────────────────────────────────────────
    result: AnalysisResult = st.session_state["result"]
    retrieved_docs = st.session_state["retrieved_docs"]
    val_results = st.session_state["val_results"]

    # Warnings from LLM
    if result.warnings:
        for w in result.warnings:
            st.warning(w)

    # ── Retrieved Documents ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("2. Retrieved Regulatory Passages")
    for doc in retrieved_docs:
        with st.expander(f"📄 {doc['source']} — {doc['section_ref']}  (score: {doc.get('score', 'N/A')})"):
            st.markdown(doc["text"])

    # ── Populated Template ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("3. Populated Template — C 01.00 (Own Funds)")

    if result.fields:
        # Build display table
        rows = []
        for f in result.fields:
            rows.append({
                "Field ID": f.field_id,
                "Field Name": f.field_name,
                "Value (£000s)": f"{f.value:,.0f}",
                "Confidence": f.confidence,
            })

        import pandas as pd
        df = pd.DataFrame(rows)

        # Color-code confidence
        def _color_confidence(val):
            colors = {"high": "#c6efce", "medium": "#ffeb9c", "low": "#ffc7ce"}
            return f"background-color: {colors.get(val, '')}"

        styled = df.style.applymap(_color_confidence, subset=["Confidence"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.warning("No fields were populated. Check the LLM response.")

    # ── Validation Results ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("4. Validation Results")

    passed_count = sum(1 for v in val_results if v.passed)
    total_count = len(val_results)
    col_v1, col_v2, col_v3 = st.columns(3)
    col_v1.metric("Total Rules", total_count)
    col_v2.metric("Passed", passed_count)
    col_v3.metric("Failed", total_count - passed_count)

    for v in val_results:
        icon = "✅" if v.passed else "❌"
        label = f"{icon} **{v.rule_id}**: {v.description}"
        if v.passed:
            st.success(label)
        else:
            st.error(f"{label}\n\n{v.message}")

    # ── Audit Trail ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("5. Audit Trail")

    for f in result.fields:
        with st.expander(f"📋 {f.field_id} — {f.field_name} = {f.value:,.0f}"):
            st.markdown(f"**Reasoning:** {f.reasoning}")
            st.markdown(f"**Citations:** {', '.join(f.citations)}")
            st.markdown(f"**Confidence:** {f.confidence}")

    # ── Download Excel ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("6. Export")

    excel_buf = generate_excel(
        result.fields,
        val_results,
        st.session_state.get("session_id", "export"),
    )

    st.download_button(
        label="📥 Download Excel Report (C 01.00)",
        data=excel_buf,
        file_name=f"COREP_C0100_{st.session_state.get('session_id', 'export')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    query, scenario, method = render_sidebar()
    render_main(query, scenario, method)


if __name__ == "__main__":
    main()
else:
    main()
