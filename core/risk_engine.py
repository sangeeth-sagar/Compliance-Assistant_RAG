from typing import Dict, List


WEIGHTS = {
    "Aadhaar": 5,
    "PAN": 5,
    "Credit_Card": 5,
    "Bank_Account": 5,
    "API_Key": 5,
    "IFSC": 5,
    "Phone_IN": 2,
    "Phone_Generic": 2,
    "Employee_ID": 2,
    "Email": 1,
    "spacy_PERSON": 1,
    "spacy_ORG": 1,
    "Confidential_Info": 3,
}

THRESHOLDS = {
    "Low": (0, 5),
    "Medium": (6, 20),
    "High": (21, float("inf")),
}


def compute_risk(findings: Dict[str, List]) -> Dict:
    counts = {k: len(v) for k, v in findings.items()}
    score = sum(counts.get(k, 0) * w for k, w in WEIGHTS.items())

    if score <= 5:
        level = "Low"
    elif score <= 20:
        level = "Medium"
    else:
        level = "High"

    breakdown = []
    for pii_type, weight in WEIGHTS.items():
        cnt = counts.get(pii_type, 0)
        if cnt > 0:
            breakdown.append({
                "type": pii_type,
                "count": cnt,
                "weight": weight,
                "points": cnt * weight,
            })
    breakdown.sort(key=lambda x: x["points"], reverse=True)

    return {
        "score": score,
        "level": level,
        "breakdown": breakdown,
        "total_findings": sum(counts.values()),
    }
