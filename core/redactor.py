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

    spans.sort(key=lambda x: x["start"])

    non_overlapping = []
    last_end = 0
    for span in spans:
        if span["start"] >= last_end:
            non_overlapping.append(span)
            last_end = span["end"]

    result = []
    pos = 0
    for span in non_overlapping:
        if pos < span["start"]:
            result.append(raw_text[pos:span["start"]])
        result.append(f"[REDACTED_{span['type']}]")
        pos = span["end"]

    if pos < len(raw_text):
        result.append(raw_text[pos:])

    return "".join(result)
