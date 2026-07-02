import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

AUDIT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
AUDIT_FILE = os.path.join(AUDIT_DIR, "audit.jsonl")


def _ensure_dir():
    os.makedirs(AUDIT_DIR, exist_ok=True)


def log_action(
    action: str,
    doc_id: str,
    filename: str,
    risk_level: str = "",
    details: Optional[Dict] = None,
):
    _ensure_dir()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "doc_id": doc_id,
        "filename": filename,
        "risk_level": risk_level,
    }
    if details:
        entry["details"] = details
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_log() -> List[Dict]:
    if not os.path.exists(AUDIT_FILE):
        return []
    entries = []
    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries
