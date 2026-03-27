from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


DATE_PATTERNS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%d %b %Y",
    "%d %b %y",
    "%d %B %Y",
    "%d-%m-%y",
    "%d/%m/%Y",
)
AMOUNT_PATTERN = re.compile(r"[-+]?\d[\d,]*\.\d{2}")


@dataclass
class ParsedTransaction:
    date: str | None
    merchant: str | None
    amount: float | None
    transaction_type: str | None
    description: str
    raw_text: str
    confidence: float


def normalize_transaction_rows(rows: list[list[str]]) -> list[str]:
    cleaned_rows = []
    for row in rows:
        if not any(row):
            continue
        text = " | ".join(cell for cell in row if cell).strip()
        if not text or _is_non_transaction_row(text):
            continue
        cleaned_rows.append(text)
    return cleaned_rows


def _is_non_transaction_row(text: str) -> bool:
    lowered = text.lower()
    return any(
        keyword in lowered
        for keyword in [
            "opening balance",
            "closing balance",
            "page ",
            "date particulars",
            "transaction details",
            "account summary",
            "balance brought forward",
        ]
    )


def _parse_date(text: str) -> str | None:
    matches = re.findall(
        r"\b(\d{2}[/-]\d{2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b",
        text,
    )
    for candidate in matches:
        cleaned = candidate.strip(",")
        for fmt in DATE_PATTERNS:
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _parse_amounts(text: str) -> list[float]:
    values = []
    scrubbed = re.sub(
        r"\b(\d{2}[/-]\d{2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b",
        " ",
        text,
    )
    for match in AMOUNT_PATTERN.findall(scrubbed.replace("CR", "").replace("DR", "")):
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue
    return values


def _parse_type(text: str, amount: float | None) -> str | None:
    lowered = text.lower()
    if any(keyword in lowered for keyword in [
        " cr", "credit", "deposit", "salary", "refund", "interest", "upi/cr",
        "neft cr", "rtgs cr", "imps cr", "inward", "credited", "cashback",
    ]):
        return "credit"
    if any(
        keyword in lowered
        for keyword in [
            " dr", "debit", "withdrawal", "purchase", "upi", "cwdr", "atm", "pos", "card",
            "wdl tfr", "upi/dr", "neft dr", "rtgs dr", "imps dr", "ecom", "nfs",
            "nfs-cwdr", "ach d", "nach", "ecs", "si-", "auto debit",
        ]
    ):
        return "debit"
    return "unknown" if amount is not None else None


def _parse_merchant(text: str, date: str | None, amount: float | None) -> str | None:
    working = text
    date_match = re.search(
        r"\b(\d{2}[/-]\d{2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b",
        working,
    )
    if date_match:
        working = working[date_match.end():].strip()

    # Some malformed extracted rows repeat the date a second time before the narration.
    working = re.sub(r"^\b\d{2}[/-]\d{2}[/-]\d{2,4}\b\s*", "", working).strip()

    # Drop trailing numeric columns such as withdrawal/deposit amount and running balance.
    working = re.sub(r"\s+\d[\d,]*\.\d{2}\s+\d[\d,]*\.\d{2}\s*$", "", working)
    working = re.sub(r"\s+\d[\d,]*\.\d{2}\s*$", "", working)
    working = re.sub(r"\b(?:debit|credit)\b\s*$", "", working, flags=re.I).strip()

    upi_candidate = _extract_upi_counterparty(working)
    if upi_candidate:
        return upi_candidate

    neft_candidate = _extract_neft_rtgs_beneficiary(working)
    if neft_candidate:
        return neft_candidate

    parenthetical_matches = re.findall(r"\(([A-Za-z][A-Za-z .&-]{2,})\)?", working)
    if parenthetical_matches:
        return parenthetical_matches[-1].strip(" :-")

    working = re.sub(
        r"\b(?:upi|imps|neft|rtgs|credit|debit|cr|dr|pos|atm|txn|ref|utr|to|by|wdl|tfr|paym|payment|paid)\b[: -]*",
        " ",
        working,
        flags=re.I,
    )
    working = re.sub(r"\b\d{6,}\b", " ", working)
    working = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", " ", working)
    working = re.sub(r"[:|()]+", " ", working)
    working = re.sub(r"/+", " ", working)
    working = re.sub(r"\b(?:sbin|cnrb|ptyes|ptybi|oksbi|ybl|yesb|utib|at)\b", " ", working, flags=re.I)
    working = re.sub(r"\b[a-z]{2,5}\d{4,}\b", " ", working, flags=re.I)
    working = re.sub(r"\s+", " ", working).strip(" -:")
    if not _looks_like_merchant_text(working):
        return None
    return working[:255]


def _extract_upi_counterparty(text: str) -> str | None:
    match = re.search(r"upi/(?:dr|cr)/\d+/([^/|]+)", text, flags=re.I)
    if not match:
        return None

    candidate = match.group(1)
    candidate = re.sub(r"[^A-Za-z\s.&-]", " ", candidate)
    candidate = re.sub(r"\b(?:sbin|cnrb|ptyes|ptybi|oksbi|ybl|yesb|utib|ioba|bkid|hdfc|icic|kkbk|punb)\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -:/")
    if len(candidate) < 2:
        return None
    return candidate[:255]


def _extract_neft_rtgs_beneficiary(text: str) -> str | None:
    """Extract beneficiary from NEFT/RTGS/IMPS narration patterns."""
    for pattern in [
        r"(?:neft|rtgs|imps)[-/\s]*(?:dr|cr)?[-/\s]*(?:\d+[-/\s]*)*/([^/|]+)",
        r"(?:neft|rtgs|imps)\s+(?:to|from)\s+([A-Za-z][A-Za-z .'&-]{2,})",
    ]:
        match = re.search(pattern, text, flags=re.I)
        if match:
            candidate = match.group(1).strip()
            candidate = re.sub(r"\b\d{6,}\b", " ", candidate)
            candidate = re.sub(r"\s+", " ", candidate).strip(" -:/")
            if len(candidate) >= 2 and _looks_like_merchant_text(candidate):
                return candidate[:255]
    return None


def _looks_like_merchant_text(text: str) -> bool:
    if not text:
        return False
    if len(re.findall(r"[A-Za-z]", text)) < 2:
        return False
    if re.fullmatch(r"[-\d\s.,/]+", text):
        return False
    return True


def parse_transaction_text(raw_text: str) -> ParsedTransaction:
    date = _parse_date(raw_text)
    amounts = _parse_amounts(raw_text)
    amount = amounts[-2] if len(amounts) >= 2 else (amounts[-1] if amounts else None)
    transaction_type = _parse_type(raw_text, amount)
    merchant = _parse_merchant(raw_text, date, amount)

    confidence = 0.15
    for field in [date, merchant, amount]:
        if field is not None:
            confidence += 0.25
    if transaction_type and transaction_type != "unknown":
        confidence += 0.2
    elif transaction_type == "unknown":
        confidence += 0.1
    if merchant is None:
        confidence = min(confidence, 0.55)

    return ParsedTransaction(
        date=date,
        merchant=merchant,
        amount=abs(amount) if amount is not None else None,
        transaction_type=transaction_type,
        description=raw_text,
        raw_text=raw_text,
        confidence=min(confidence, 0.95),
    )
