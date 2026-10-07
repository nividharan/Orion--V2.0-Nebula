"""
🌌 Orion × Nebula Web Engine - Data Handler & Exporter
Handles schema validation, data sanitization, deduplication, and export to CSV/JSON.
"""

import os
import re
import csv
import json
import time
import hashlib
from typing import List, Dict, Any, Optional


class DataHandler:
    """Validates, cleans, deduplicates, and serializes extracted web datasets."""

    @staticmethod
    def clean_text(raw: Optional[str]) -> str:
        """Strips whitespace, replaces non-breaking spaces, and unescapes text."""
        if not raw:
            return ""
        s = raw.replace("\u00a0", " ").replace("\n", " ").replace("\r", " ")
        return re.sub(r'\s+', ' ', s).strip()

    @staticmethod
    def clean_currency(raw: Optional[str]) -> Optional[float]:
        """Extracts float number from currency strings like '$19.99' or '₹1,499.00'."""
        if not raw:
            return None
        match = re.search(r'[\d,]+(?:\.\d+)?', raw)
        if match:
            num_str = match.group(0).replace(",", "")
            try:
                return float(num_str)
            except ValueError:
                return None
        return None

    @staticmethod
    def deduplicate(records: List[Dict[str, Any]], key_fields: List[str]) -> List[Dict[str, Any]]:
        """Removes duplicates based on hash of designated key fields."""
        seen = set()
        deduped = []
        for r in records:
            composite = "|".join(str(r.get(k, "")).strip().lower() for k in key_fields)
            h = hashlib.sha256(composite.encode("utf-8")).hexdigest()
            if h not in seen:
                seen.add(h)
                deduped.append(r)
        return deduped

    @classmethod
    def export_json(cls, records: List[Dict[str, Any]], filepath: str) -> str:
        """Exports records to pretty-printed UTF-8 JSON with metadata."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        payload = {
            "timestamp": time.time(),
            "count": len(records),
            "data": records
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath

    @classmethod
    def export_csv(cls, records: List[Dict[str, Any]], filepath: str) -> str:
        """Exports records to UTF-8 CSV with headers."""
        if not records:
            return filepath
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fieldnames = list(records[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)
        return filepath
