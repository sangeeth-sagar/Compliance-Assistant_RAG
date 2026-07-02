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


def answer_question(
    question: str,
    context_chunks: list,
    doc_id: str,
) -> str:
    model = _get_model()

    context = "\n\n---\n\n".join(context_chunks)

    prompt = f"""You are a compliance assistant. Answer the user's question ONLY based on the
retrieved document context below. The document has been redacted — [REDACTED_*] tags represent
removed sensitive data. Never guess or invent information. If the answer is not in the context,
say "The answer was not found in the document."

## Retrieved Context:
{context}

## Question:
{question}

## Answer:"""

    response = model.generate_content(prompt)
    return response.text
