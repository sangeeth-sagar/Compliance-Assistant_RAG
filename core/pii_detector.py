import re
from typing import Dict, List, Any


def _verhoeff_check(num_str: str) -> bool:
    d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
    ]
    p = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
    ]
    try:
        c = 0
        for i, digit in enumerate(reversed(num_str)):
            c = d[c][p[i % 8][int(digit)]]
        return c == 0
    except (ValueError, IndexError):
        return False


def _luhn_check(num_str: str) -> bool:
    digits = [int(d) for d in num_str if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


PATTERNS: Dict[str, Any] = {
    "Aadhaar": {
        "regex": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
        "filter": lambda m: _verhoeff_check(m.replace(" ", "")),
    },
    "PAN": {
        "regex": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    },
    "Email": {
        "regex": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    },
    "Phone_IN": {
        "regex": re.compile(r"\b[6-9]\d{9}\b"),
    },
    "Phone_Generic": {
        "regex": re.compile(r"\+?\d[\d\-\s]{8,14}\d"),
    },
    "Credit_Card": {
        "regex": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "filter": lambda m: _luhn_check(re.sub(r"[\s-]", "", m)),
    },
    "IFSC": {
        "regex": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    },
    "Bank_Account": {
        "regex": re.compile(
            r"(?i)(?:account|a/c)\s*[:#]?\s*\b(\d{9,18})\b"
        ),
        "group": 1,
    },
    "API_Key": {
        "regex": re.compile(
            r"(?:AIza[0-9A-Za-z\-_]{35}|sk-[A-Za-z0-9]{20,}|"
            r"(?:[aA][pP][iI][_-]?[kK][eE][yY]|[sS][eE][cC][rR][eE][tT]|[pP][aA][sS][sS][wW][oO][rR][dD])\s*[:=]\s*\S+)"
        ),
    },
    "Employee_ID": {
        "regex": re.compile(r"\bEMP-?\d{4,6}\b", re.IGNORECASE),
    },
    "Confidential_Info": {
        "regex": re.compile(
            r"(?i)\b(?:confidential|proprietary|internal\s+use\s+only|trade\s+secret|restricted|nda\s+protected)\b"
        ),
    },
}

SPACY_LABELS = {"PERSON", "ORG"}


def detect_pii(text: str, use_spacy: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    findings: Dict[str, List[Dict[str, Any]]] = {}

    for pii_type, config in PATTERNS.items():
        pattern = config["regex"]
        filt = config.get("filter")
        group = config.get("group")
        matches = []
        for m in pattern.finditer(text):
            value = m.group(group) if group else m.group(0)
            start = m.start(group) if group else m.start(0)
            end = m.end(group) if group else m.end(0)
            if filt and not filt(value):
                continue
            matches.append({
                "value": value,
                "start": start,
                "end": end,
                "type": pii_type,
            })
        if matches:
            findings[pii_type] = matches

    if use_spacy:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in SPACY_LABELS:
                    label = f"spacy_{ent.label_}"
                    if label not in findings:
                        findings[label] = []
                    findings[label].append({
                        "value": ent.text,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "type": label,
                        "confidence": "low",
                    })
        except Exception:
            pass

    return findings


def count_findings(findings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
    return {k: len(v) for k, v in findings.items()}
