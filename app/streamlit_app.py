"""Streamlit UI for the Data Analysis Agent (bonus: UI + streaming).

Run:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os
import sys
import tempfile

import streamlit as st

# Make the src/ package importable when run via `streamlit run`.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from data_analysis_agent.config import get_settings  # noqa: E402
from data_analysis_agent.runner import DataAnalysisAgent  # noqa: E402

st.set_page_config(page_title="Data Analysis Agent", page_icon="📊", layout="wide")
st.title("📊 Data Analysis Agent")
st.caption("Upload a CSV, ask a question, and watch the agent reason, code, and analyze.")

settings = get_settings()
if not settings.has_api_key:
    st.error("No API key found. Copy `.env.example` to `.env` and set AZURE_AI_API_KEY.")
    st.stop()


@st.cache_resource
def _get_agent() -> DataAnalysisAgent:
    return DataAnalysisAgent(use_memory=True)


def _persist_upload(uploaded) -> str:
    tmp_dir = tempfile.gettempdir()
    path = os.path.join(tmp_dir, uploaded.name)
    with open(path, "wb") as fh:
        fh.write(uploaded.getbuffer())
    return path


# --- Session state ---------------------------------------------------------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = _get_agent().new_thread_id()

with st.sidebar:
    st.header("Session")
    st.write(f"Model: `{settings.model}`")
    st.write(f"Thread: `{st.session_state.thread_id}`")
    if st.button("New session"):
        st.session_state.thread_id = _get_agent().new_thread_id()
        st.rerun()

uploaded = st.file_uploader("Upload a CSV", type=["csv"])
query = st.text_input("Your analysis question", placeholder="Which region sells most?")
clarifications = st.text_area(
    "Optional clarifications (skips the clarify step)", height=68
)
run = st.button("Run analysis", type="primary", disabled=not (uploaded and query))

if run:
    csv_path = _persist_upload(uploaded)
    agent = _get_agent()

    st.subheader("Agent trace")
    trace_box = st.container()
    final: dict = {}

    with st.spinner("Agent working..."):
        for node_name, output in agent.stream(
            csv_path,
            query,
            thread_id=st.session_state.thread_id,
            clarifications=clarifications or "(Proceed with best assumptions.)"
            if not clarifications
            else clarifications,
        ):
            for event in output.get("trace", []):
                trace_box.markdown(
                    f"**[{event['phase']}] {event['step']}** — {event['detail']}"
                )
                if event["step"] == "codegen" and event["data"].get("code"):
                    with trace_box.expander("Generated code"):
                        st.code(event["data"]["code"], language="python")
            final.update(output)

    if final.get("needs_user_input"):
        st.warning("The agent needs clarification:")
        for q in final.get("pending_questions", []):
            st.markdown(f"- {q}")
        st.info("Answer in the clarifications box above and run again.")
    else:
        st.subheader("Result")
        st.markdown(final.get("final_response", "(no response)"))

        artifacts_dir = settings.artifacts_dir
        if os.path.isdir(artifacts_dir):
            imgs = [f for f in os.listdir(artifacts_dir) if f.endswith((".png", ".jpg"))]
            for img in imgs:
                st.image(os.path.join(artifacts_dir, img))
