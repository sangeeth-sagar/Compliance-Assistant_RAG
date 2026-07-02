from typing import Dict, List, Any


def redact_text(raw_text: str, findings: Dict[str, List[Dict[str, Any]]]) -> str:
    spans = []
    for pii_type, matches in findings.items():
        for m in matches:
            spans.append({
                "start": m["start"],
                "end": m["end"],
                "type": m["type"],
            })

    if not spans:
        return raw_text

    # Sort spans by start (ascending), then end (descending)
    spans.sort(key=lambda x: (x["start"], -x["end"]))

    merged_spans = []
    current = spans[0]
    for next_span in spans[1:]:
        if next_span["start"] < current["end"]:
            # Overlap: extend end of current span if next span ends later
            if next_span["end"] > current["end"]:
                current["end"] = next_span["end"]
        else:
            merged_spans.append(current)
            current = next_span
    merged_spans.append(current)

    result = []
    pos = 0
    for span in merged_spans:
        if pos < span["start"]:
            result.append(raw_text[pos:span["start"]])
        result.append(f"[REDACTED_{span['type']}]")
        pos = span["end"]

    if pos < len(raw_text):
        result.append(raw_text[pos:])

    return "".join(result)
