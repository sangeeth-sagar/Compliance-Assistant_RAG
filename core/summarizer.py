import os
import google.generativeai as genai


def _get_model():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set. Add it to your .env file.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-3.1-flash-lite")


def generate_summary(
    redacted_text: str,
    findings_summary: dict,
    risk_level: str,
) -> str:
    model = _get_model()

    prompt = f"""You are a data compliance and security expert. Analyze the following document
content (which has been redacted to remove sensitive data) along with the PII scan results.

## Redacted Document Content:
{redacted_text[:8000]}

## PII Detection Summary:
- Risk Level: {risk_level}
- Findings: {findings_summary}

Based on this information, provide a structured compliance report with these sections:

### Compliance Observations
What types of sensitive data were found? Is this typical for the document type?

### Security Risks
What are the specific risks associated with this data being exposed?

### Suggested Remediation Steps
Actionable recommendations to reduce risk and improve compliance.

Format as clean Markdown. Be specific and actionable."""

    response = model.generate_content(prompt)
    return response.text


def summarize_chat_history(messages: list[dict]) -> str:
    if not messages:
        return ""
    model = _get_model()
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:500]}"
        for m in messages
    )
    prompt = f"""Summarize the following conversation about a compliance document into a
concise running summary that captures key topics discussed, questions asked, and conclusions
reached. Keep it under 300 words.

## Conversation:
{transcript}

## Summary:"""
    response = model.generate_content(prompt)
    return response.text


def answer_question(
    question: str,
    context_chunks: list,
    doc_id: str,
    chat_history: list[dict] | None = None,
    memory_summary: str | None = None,
    findings: dict | None = None,
) -> str:
    model = _get_model()

    context = "\n\n---\n\n".join(context_chunks)

    findings_section = ""
    if findings:
        findings_section += "\n\n## Detected Sensitive Information (PII) Findings in this Document:\n"
        for pii_type, matches in findings.items():
            if matches:
                findings_section += f"- {pii_type}:\n"
                values = [m.get("value") for m in matches if m.get("value")]
                for val in sorted(set(values)):
                    findings_section += f"  * {val}\n"

    history_section = ""
    if memory_summary:
        history_section += f"\n\n## Prior Conversation Summary:\n{memory_summary}"
    if chat_history:
        turns = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:300]}"
            for m in chat_history
        )
        history_section += f"\n\n## Recent Conversation:\n{turns}"

    prompt = f"""You are a compliance assistant. Answer the user's question based on the retrieved document context below. 

The document has been redacted to replace sensitive identifiers with placeholder tags like [REDACTED_*]. 
To help you answer questions about what sensitive data exists or what was redacted, you have been provided with a list of the detected PII findings from the database under the 'Detected Sensitive Information (PII) Findings' section.

If the user asks general questions about the document content, answer based on the retrieved document context. 
If the user asks specific questions about the redacted sensitive data (e.g. "What email addresses are there?", "What sensitive data was found?", "How many email addresses are present?"), refer to the detected PII findings section.

Never guess or invent information. If the answer cannot be answered from the retrieved context or the detected findings, say "The answer was not found in the document."

## Retrieved Document Context:
{context}
{findings_section}
{history_section}

## Question:
{question}

## Answer:"""

    response = model.generate_content(prompt)
    return response.text
