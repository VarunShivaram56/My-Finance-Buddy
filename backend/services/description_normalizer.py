from __future__ import annotations

import re


COMMERCIAL_MARKERS = {
    "swiggy",
    "zomato",
    "amazon",
    "flipkart",
    "myntra",
    "uber",
    "ola",
    "netflix",
    "spotify",
    "youtube",
    "railways",
    "irctc",
    "bmtc",
    "metro",
    "mart",
    "store",
    "hotel",
    "restaurant",
    "cafe",
    "pharma",
    "hospital",
    "clinic",
    "dmart",
    "reliance",
    "bookmyshow",
    "pvr",
    "airtel",
    "jio",
    "bsnl",
    "electricity",
    "water",
    "gas",
    "broadband",
}


def build_description_signature(description: str) -> str:
    normalized = normalize_description_text(description)
    normalized = re.sub(r"\b\d+\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized[:160]


def normalize_description_text(description: str) -> str:
    text = (description or "").lower()
    text = re.sub(r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b", " ", text)
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
    text = re.sub(r"[a-z0-9._%+-]+@[a-z0-9.-]+", " ", text)
    text = re.sub(r"\b(?:upi|imps|neft|rtgs|txn|ref|utr|kblu|cwdr|nfs-cwdr|ecom|mc)\b", " ", text)
    text = re.sub(r"\b\d[\d,]*\.\d{2}\b", " ", text)
    text = re.sub(r"\b\d{6,}\b", " ", text)
    text = re.sub(r"[^a-z\s/&-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def looks_like_personal_transfer(description: str) -> bool:
    normalized = normalize_description_text(description)
    if not normalized:
        return False
    if any(marker in normalized for marker in COMMERCIAL_MARKERS):
        return False
    tokens = [token for token in normalized.split() if len(token) > 1]
    if not tokens or len(tokens) > 6:
        return False
    return sum(1 for token in tokens if token.isalpha()) >= 1
