import os
import uuid
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from core.extractor import extract_text
from core.pii_detector import detect_pii, count_findings
from core.risk_engine import compute_risk
from core.redactor import redact_text
from core.summarizer import generate_summary, answer_question
from core.rag_engine import index_document, query_document
from core.audit import log_action, read_log


st.set_page_config(
    page_title="Compliance Sentinel",
    page_icon="🛡️",
    layout="wide",
)

if "documents" not in st.session_state:
    st.session_state.documents = {}
if "current_doc_id" not in st.session_state:
    st.session_state.current_doc_id = None

st.title("🛡️ Compliance Sentinel")
st.caption("Sensitive Data Detection & Compliance Assistant")

tab_upload, tab_summary, tab_chat, tab_audit = st.tabs(
    ["Upload & Scan", "Compliance Summary", "Ask Questions", "Audit Log"]
)

# ─── TAB 1: Upload & Scan ───
with tab_upload:
    st.header("Document Upload & PII Scan")

    uploaded_file = st.file_uploader(
        "Upload a document (PDF, TXT, CSV)",
        type=["pdf", "txt", "csv"],
        key="file_uploader",
    )

    use_spacy = st.checkbox("Enable spaCy NER (supplementary)", value=False)

    if uploaded_file and st.button("Scan Document", type="primary"):
        file_bytes = uploaded_file.read()

        with st.spinner("Extracting text..."):
            raw_text, source_type, count = extract_text(file_bytes, uploaded_file.name)

        if not raw_text.strip():
            st.error("No text could be extracted from the document.")
        else:
            with st.spinner("Detecting sensitive data..."):
                findings = detect_pii(raw_text, use_spacy=use_spacy)
                risk = compute_risk(findings)
                redacted = redact_text(raw_text, findings)

            doc_id = str(uuid.uuid4())[:8]
            st.session_state.documents[doc_id] = {
                "filename": uploaded_file.name,
                "raw_text": raw_text,
                "redacted_text": redacted,
                "findings": findings,
                "risk": risk,
                "source_type": source_type,
                "count": count,
            }
            st.session_state.current_doc_id = doc_id

            log_action(
                action="scan",
                doc_id=doc_id,
                filename=uploaded_file.name,
                risk_level=risk["level"],
                details=count_findings(findings),
            )

            st.success(f"Document scanned! Doc ID: `{doc_id}`")

    # Show results if a document is loaded
    doc_id = st.session_state.current_doc_id
    if doc_id and doc_id in st.session_state.documents:
        doc = st.session_state.documents[doc_id]

        st.divider()

        # Document picker for multi-doc
        if len(st.session_state.documents) > 1:
            options = {
                k: v["filename"] for k, v in st.session_state.documents.items()
            }
            selected = st.selectbox(
                "Select document:",
                options=list(options.keys()),
                format_func=lambda x: f"{options[x]} ({x})",
                index=list(options.keys()).index(doc_id),
                key="doc_picker",
            )
            if selected != doc_id:
                st.session_state.current_doc_id = selected
                st.rerun()
            doc = st.session_state.documents[selected]
            doc_id = selected

        risk = doc["risk"]
        findings = doc["findings"]

        # Risk badge
        color_map = {"Low": "green", "Medium": "orange", "High": "red"}
        level = risk["level"]
        st.markdown(
            f"### Risk Level: :{color_map[level]}[{level}] "
            f"(Score: {risk['score']})"
        )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("PII Findings Summary")
            if findings:
                summary = count_findings(findings)
                st.table(
                    [{"Type": k, "Count": v} for k, v in summary.items()]
                )
            else:
                st.info("No sensitive data detected.")

        with col2:
            st.subheader("Risk Breakdown")
            if risk["breakdown"]:
                st.table(risk["breakdown"])

        with st.expander("Redacted Text Preview"):
            st.code(doc["redacted_text"][:3000], language=None)

        with st.expander("Raw Text Preview (first 1000 chars)"):
            st.code(doc["raw_text"][:1000], language=None)


# ─── TAB 2: Compliance Summary ───
with tab_summary:
    st.header("AI Compliance Summary")

    doc_id = st.session_state.current_doc_id
    if not doc_id or doc_id not in st.session_state.documents:
        st.info("Upload and scan a document first.")
    else:
        doc = st.session_state.documents[doc_id]
        st.caption(f"Document: **{doc['filename']}** (ID: `{doc_id}`)")

        if st.button("Generate Summary", type="primary"):
            with st.spinner("Generating compliance summary with Gemini..."):
                try:
                    summary = generate_summary(
                        redacted_text=doc["redacted_text"],
                        findings_summary=count_findings(doc["findings"]),
                        risk_level=doc["risk"]["level"],
                    )
                    doc["summary"] = summary

                    log_action(
                        action="summary",
                        doc_id=doc_id,
                        filename=doc["filename"],
                        risk_level=doc["risk"]["level"],
                    )
                except Exception as e:
                    st.error(f"Error generating summary: {e}")
                    summary = None

            if summary:
                st.markdown(summary)

        if "summary" in doc:
            st.markdown("---")
            st.markdown(doc["summary"])


# ─── TAB 3: Ask Questions (RAG) ───
with tab_chat:
    st.header("Ask Questions About Your Document")

    doc_id = st.session_state.current_doc_id
    if not doc_id or doc_id not in st.session_state.documents:
        st.info("Upload and scan a document first.")
    else:
        doc = st.session_state.documents[doc_id]
        st.caption(f"Document: **{doc['filename']}** (ID: `{doc_id}`)")

        if "indexed" not in doc:
            if st.button("Index Document for RAG", type="primary"):
                with st.spinner("Chunking and embedding document..."):
                    try:
                        n_chunks = index_document(doc_id, doc["redacted_text"])
                        doc["indexed"] = True
                        st.success(f"Indexed {n_chunks} chunks.")
                    except Exception as e:
                        st.error(f"Indexing error: {e}")

        if doc.get("indexed"):
            if "chat_history" not in doc:
                doc["chat_history"] = []

            for msg in doc["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            question = st.chat_input("Ask a question about the document...")
            if question:
                with st.chat_message("user"):
                    st.markdown(question)
                doc["chat_history"].append({"role": "user", "content": question})

                with st.spinner("Searching document and generating answer..."):
                    try:
                        chunks = query_document(doc_id, question)
                        answer = answer_question(question, chunks, doc_id)
                    except Exception as e:
                        answer = f"Error: {e}"

                with st.chat_message("assistant"):
                    st.markdown(answer)
                doc["chat_history"].append(
                    {"role": "assistant", "content": answer}
                )

                log_action(
                    action="query",
                    doc_id=doc_id,
                    filename=doc["filename"],
                    risk_level=doc["risk"]["level"],
                )


# ─── TAB 4: Audit Log ───
with tab_audit:
    st.header("Audit Log")

    entries = read_log()
    if not entries:
        st.info("No audit entries yet.")
    else:
        st.dataframe(
            entries,
            use_container_width=True,
            column_config={
                "timestamp": st.column_config.DatetimeColumn("Timestamp"),
                "action": "Action",
                "doc_id": "Doc ID",
                "filename": "Filename",
                "risk_level": "Risk Level",
            },
        )
