from __future__ import annotations

from io import BytesIO
import re

import pdfplumber

from services.bank_profiles import CANARA_LEDGER_FAMILY, SBI_LEDGER_FAMILY, STANDARD_LEDGER_FAMILY, get_bank_profile


def extract_rows_from_pdf(file_bytes: bytes) -> list[list[str]]:
    rows: list[list[str]] = []
    seen: set[str] = set()
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    normalized = [str(cell).strip() if cell else "" for cell in row]
                    joined = " | ".join(cell for cell in normalized if cell).strip()
                    if any(normalized) and joined and joined not in seen:
                        rows.append(normalized)
                        seen.add(joined)

            # Many statement PDFs do not expose tables cleanly. Fall back to text lines.
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            for line in _extract_transaction_lines(text):
                if line not in seen:
                    rows.append([line])
                    seen.add(line)
    return rows


def extract_bank_rows(file_bytes: bytes, bank_name: str) -> list[list[str]]:
    profile = get_bank_profile(bank_name)
    if profile.extractor_family == STANDARD_LEDGER_FAMILY:
        return extract_standard_ledger_rows(file_bytes)
    if profile.extractor_family == CANARA_LEDGER_FAMILY:
        return extract_canara_bank_rows(file_bytes)
    if profile.extractor_family == SBI_LEDGER_FAMILY:
        return extract_sbi_bank_rows(file_bytes)
    return []


def extract_standard_ledger_rows(file_bytes: bytes) -> list[list[str]]:
    lines = _extract_pdf_lines(file_bytes)
    return _extract_multiline_ledger_transactions(lines)


def extract_karnataka_bank_rows(file_bytes: bytes) -> list[list[str]]:
    return extract_standard_ledger_rows(file_bytes)


def extract_canara_bank_rows(file_bytes: bytes) -> list[list[str]]:
    text_rows = _extract_canara_text_rows(file_bytes)
    if _has_meaningful_rows(text_rows):
        return text_rows

    table_rows = _extract_canara_table_rows(file_bytes)
    if table_rows:
        return table_rows

    lines = _extract_pdf_lines(file_bytes)
    return _extract_multiline_ledger_transactions(lines)


def extract_sbi_bank_rows(file_bytes: bytes) -> list[list[str]]:
    text_rows = _extract_sbi_text_rows(file_bytes)
    if _has_meaningful_rows(text_rows):
        return text_rows

    table_rows = _extract_sbi_table_rows(file_bytes)
    if table_rows:
        return table_rows

    lines = _extract_pdf_lines(file_bytes)
    return _extract_multiline_ledger_transactions(lines)


def _extract_pdf_lines(file_bytes: bytes) -> list[str]:
    lines: list[str] = []

    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            if text:
                lines.extend(text.splitlines())

    return lines


def _extract_multiline_ledger_transactions(lines: list[str]) -> list[list[str]]:
    transactions: list[list[str]] = []
    prev_balance: float | None = None
    date_pattern = r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_parts, prev_balance
        if not current_parts:
            return
        block = " ".join(current_parts)
        parsed = _parse_ledger_transaction_block(block, prev_balance)
        if parsed:
            formatted, balance = parsed
            transactions.append([formatted])
            prev_balance = balance
        current_parts = []

    for raw_line in lines:
        line = _normalize_line(raw_line)
        if not line:
            continue

        lowered = line.lower()
        if _looks_like_ledger_header(lowered):
            continue

        numbers = re.findall(r"\d{1,3}(?:,\d{3})*\.\d{2}", line)

        if "opening balance" in lowered:
            if numbers:
                prev_balance = float(numbers[-1].replace(",", ""))
            continue

        if re.search(date_pattern, line):
            flush_current()
            current_parts = [line]
            continue

        if current_parts and not _is_non_transaction_line(lowered):
            current_parts.append(line)
            continue

    flush_current()

    return transactions


def _parse_ledger_transaction_block(block: str, prev_balance: float | None) -> tuple[str, float] | None:
    date_pattern = r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
    numbers = re.findall(r"\d{1,3}(?:,\d{3})*\.\d{2}", block)
    if len(numbers) < 2:
        return None

    amount = float(numbers[-2].replace(",", ""))
    balance = float(numbers[-1].replace(",", ""))
    date_match = re.search(date_pattern, block)
    if not date_match:
        return None

    date_text = date_match.group()
    particulars = block.split(date_text, 1)[1].strip()
    particulars = re.sub(r"\s+\d{1,3}(?:,\d{3})*\.\d{2}\s+\d{1,3}(?:,\d{3})*\.\d{2}\s*$", "", particulars).strip()
    particulars = re.sub(r"\bChq:\s*\d+\b", "", particulars, flags=re.I).strip()
    particulars = re.sub(r"\b(?:cr|dr)\b\s*$", "", particulars, flags=re.I).strip(" -|")
    particulars = re.sub(r"\s+", " ", particulars).strip()
    if not particulars:
        return None

    transaction_type = "unknown"
    if prev_balance is not None:
        if balance < prev_balance:
            transaction_type = "debit"
        elif balance > prev_balance:
            transaction_type = "credit"
    if transaction_type == "unknown":
        transaction_type = _infer_type_from_text(block)

    formatted = f"{date_text} {particulars} {amount:.2f} {balance:.2f} {transaction_type.upper()}".strip()
    return formatted, balance


def _extract_canara_table_rows(file_bytes: bytes) -> list[list[str]]:
    rows: list[list[str]] = []
    prev_balance: float | None = None
    for block in _group_transaction_blocks(file_bytes, _is_canara_transaction_start):
        parsed = _parse_table_transaction_block(block, prev_balance)
        if not parsed:
            continue
        formatted, balance = parsed
        rows.append([formatted])
        prev_balance = balance
    return rows


def _extract_canara_text_rows(file_bytes: bytes) -> list[list[str]]:
    lines = _extract_pdf_lines(file_bytes)
    return _extract_single_date_statement_transactions(lines)


def _extract_sbi_table_rows(file_bytes: bytes) -> list[list[str]]:
    rows: list[list[str]] = []
    prev_balance: float | None = None
    for block in _group_transaction_blocks(file_bytes, _is_sbi_transaction_start):
        parsed = _parse_table_transaction_block(block, prev_balance)
        if not parsed:
            continue
        formatted, balance = parsed
        rows.append([formatted])
        prev_balance = balance
    return rows


def _extract_sbi_text_rows(file_bytes: bytes) -> list[list[str]]:
    lines = _extract_pdf_lines(file_bytes)
    return _extract_dual_date_statement_transactions(lines)


def _extract_dual_date_statement_transactions(lines: list[str]) -> list[list[str]]:
    transactions: list[list[str]] = []
    prev_balance: float | None = None
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_parts, prev_balance
        if not current_parts:
            return
        parsed = _parse_dual_date_statement_block(current_parts, prev_balance)
        if parsed:
            formatted, balance = parsed
            transactions.append([formatted])
            prev_balance = balance
        current_parts = []

    for raw_line in lines:
        line = _normalize_line(raw_line)
        if not line:
            continue
        lowered = line.lower()
        if _looks_like_ledger_header(lowered):
            continue
        if _looks_like_dual_date_start(line):
            flush_current()
            current_parts = [line]
            continue
        if current_parts and not _is_non_transaction_line(lowered):
            current_parts.append(line)

    flush_current()
    return transactions


def _extract_single_date_statement_transactions(lines: list[str]) -> list[list[str]]:
    transactions: list[list[str]] = []
    prev_balance: float | None = None
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_parts, prev_balance
        if not current_parts:
            return
        block = " ".join(current_parts)
        parsed = _parse_ledger_transaction_block(block, prev_balance)
        if parsed and _looks_like_meaningful_description(_description_from_formatted_transaction(parsed[0])):
            formatted, balance = parsed
            transactions.append([formatted])
            prev_balance = balance
        current_parts = []

    for raw_line in lines:
        line = _normalize_line(raw_line)
        if not line:
            continue
        lowered = line.lower()
        if _looks_like_ledger_header(lowered):
            continue
        if _looks_like_single_date_start(line):
            flush_current()
            current_parts = [line]
            continue
        if current_parts and not _is_non_transaction_line(lowered):
            current_parts.append(line)

    flush_current()
    return transactions


def _group_transaction_blocks(file_bytes: bytes, is_start) -> list[list[list[str]]]:
    blocks: list[list[list[str]]] = []
    current: list[list[str]] = []

    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    normalized = [str(cell).strip() if cell else "" for cell in row]
                    if not any(normalized):
                        continue
                    lowered = " ".join(normalized).lower()
                    if _looks_like_ledger_header(lowered):
                        continue

                    if is_start(normalized):
                        if current:
                            blocks.append(current)
                        current = [normalized]
                        continue

                    if current:
                        current.append(normalized)

    if current:
        blocks.append(current)

    return blocks


def _is_canara_transaction_start(row: list[str]) -> bool:
    return bool(row and _is_date_cell(row[0]) and _count_amount_cells(row) >= 1)


def _is_sbi_transaction_start(row: list[str]) -> bool:
    first_two = [cell for cell in row[:2] if cell]
    has_date = any(_is_date_cell(cell) for cell in first_two) or (len(row) > 2 and _is_date_cell(row[0]))
    return has_date and _count_amount_cells(row) >= 1


def _parse_table_transaction_block(block: list[list[str]], prev_balance: float | None) -> tuple[str, float] | None:
    date_text = _first_date_in_block(block)
    numeric_cells = _numeric_cells_in_block(block)
    particulars = _detail_text_from_block(block)
    if not date_text or len(numeric_cells) < 2 or not particulars:
        return None

    amount = float(numeric_cells[-2].replace(",", ""))
    balance = float(numeric_cells[-1].replace(",", ""))

    transaction_type = "unknown"
    if prev_balance is not None:
        if balance < prev_balance:
            transaction_type = "debit"
        elif balance > prev_balance:
            transaction_type = "credit"
    if transaction_type == "unknown":
        transaction_type = _infer_type_from_text(particulars)

    if transaction_type == "unknown":
        return None

    cleaned_particulars = re.sub(r"\s+", " ", particulars).strip(" -|")
    if not _looks_like_meaningful_description(cleaned_particulars):
        return None

    formatted = f"{date_text} {cleaned_particulars} {amount:.2f} {balance:.2f} {transaction_type.upper()}".strip()
    return formatted, balance


def _parse_dual_date_statement_block(lines: list[str], prev_balance: float | None) -> tuple[str, float] | None:
    if not lines:
        return None

    header = lines[0]
    match = re.match(
        r"^(?P<value>\d{2}[/-]\d{2}[/-]\d{4})\s+(?P<post>\d{2}[/-]\d{2}[/-]\d{4})\s+(?P<rest>.*)$",
        header,
    )
    if not match:
        return None

    date_text = match.group("value")
    header_rest = match.group("rest").strip()
    all_text = " ".join([header_rest] + lines[1:])
    numbers = re.findall(r"\d{1,3}(?:,\d{3})*\.\d{2}", all_text)
    if len(numbers) < 2:
        return None

    amount = float(numbers[-2].replace(",", ""))
    balance = float(numbers[-1].replace(",", ""))
    particulars = re.sub(r"\s*[-]?\s*\d{1,3}(?:,\d{3})*\.\d{2}\s*[-]?\s*\d{1,3}(?:,\d{3})*\.\d{2}\s*$", "", all_text).strip()
    particulars = re.sub(r"\s+", " ", particulars).strip(" -|")
    if not _looks_like_meaningful_description(particulars):
        return None

    transaction_type = "unknown"
    if prev_balance is not None:
        if balance < prev_balance:
            transaction_type = "debit"
        elif balance > prev_balance:
            transaction_type = "credit"
    if transaction_type == "unknown":
        transaction_type = _infer_type_from_text(particulars)
    if transaction_type == "unknown":
        return None

    formatted = f"{date_text} {particulars} {amount:.2f} {balance:.2f} {transaction_type.upper()}".strip()
    return formatted, balance


def _extract_transaction_lines(text: str) -> list[str]:
    transaction_lines: list[str] = []
    current_line = ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        if _looks_like_transaction_start(line):
            if current_line:
                transaction_lines.append(current_line)
            current_line = line
        elif current_line and not _looks_like_header(line):
            current_line = f"{current_line} {line}".strip()

    if current_line:
        transaction_lines.append(current_line)

    return transaction_lines


def _looks_like_transaction_start(line: str) -> bool:
    has_date = bool(
        re.search(
            r"\b(\d{2}[/-]\d{2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{2}\s+[A-Za-z]{3}\s+\d{2,4})\b",
            line,
        )
    )
    has_amount = bool(re.search(r"\d[\d,]*\.\d{2}\b", line))
    return has_date and has_amount


def _looks_like_dual_date_start(line: str) -> bool:
    return bool(
        re.match(r"^\d{2}[/-]\d{2}[/-]\d{4}\s+\d{2}[/-]\d{2}[/-]\d{4}\b", line)
        and re.search(r"\d{1,3}(?:,\d{3})*\.\d{2}", line)
    )


def _looks_like_single_date_start(line: str) -> bool:
    return bool(
        re.match(r"^\d{2}[/-]\d{2}[/-]\d{4}\b", line)
        and not _looks_like_dual_date_start(line)
        and re.search(r"\d{1,3}(?:,\d{3})*\.\d{2}", line)
    )


def _looks_like_header(line: str) -> bool:
    lowered = line.lower()
    return any(
        keyword in lowered
        for keyword in ["date", "description", "balance", "debit", "credit", "statement", "account", "opening"]
    )


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line or "").strip()


def _looks_like_ledger_header(lowered: str) -> bool:
    if "date" in lowered and "balance" in lowered:
        return True
    return any(
        phrase in lowered
        for phrase in [
            "transaction details",
            "account statement",
            "value date",
            "closing balance",
            "withdrawal deposit",
            "particulars",
            "instrument no",
            "branch name",
            "account no",
            "customer id",
            "statement summary",
            "page no",
        ]
    )


def _is_non_transaction_line(lowered: str) -> bool:
    return any(
        phrase in lowered
        for phrase in [
            "continued on next page",
            "page ",
            "branch:",
            "account number",
            "statement period",
            "generated on",
            "printed on",
            "this is a computer",
            "disclaimer",
            "total:",
            "grand total",
            "nominee",
        ]
    )


def _parse_amount_cell(value: str) -> float | None:
    if not _is_amount_cell(value):
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _is_amount_cell(value: str) -> bool:
    return bool(re.fullmatch(r"\d{1,3}(?:,\d{3})*\.\d{2}", (value or "").strip()))


def _is_date_cell(value: str) -> bool:
    return bool(re.fullmatch(r"\d{2}[/-]\d{2}[/-]\d{4}", (value or "").strip()))


def _count_amount_cells(row: list[str]) -> int:
    return sum(1 for cell in row if _is_amount_cell(cell))


def _first_date_in_block(block: list[list[str]]) -> str | None:
    for row in block:
        for cell in row:
            if _is_date_cell(cell):
                return cell
    return None


def _numeric_cells_in_block(block: list[list[str]]) -> list[str]:
    values: list[str] = []
    for row in block:
        for cell in row:
            if _is_amount_cell(cell):
                values.append(cell)
    return values


def _detail_text_from_block(block: list[list[str]]) -> str:
    details: list[str] = []
    for row in block:
        for cell in row:
            if not cell:
                continue
            if _is_date_cell(cell) or _is_amount_cell(cell):
                continue
            if cell.strip() == "-":
                continue
            if re.fullmatch(r"\d{6,}", cell):
                continue
            details.append(cell)

    text = " ".join(details)
    text = re.sub(r"\bChq:\s*\d+\b", "", text, flags=re.I)
    text = re.sub(r"\bInst(?:rument)?\s*(?:No\.?)?\s*\d+\b", "", text, flags=re.I)
    text = re.sub(r"\b\d{12,}\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _looks_like_meaningful_description(text: str) -> bool:
    alpha_count = sum(1 for char in text if char.isalpha())
    return alpha_count >= 3


def _description_from_formatted_transaction(formatted: str) -> str:
    text = re.sub(r"^\d{2}[/-]\d{2}[/-]\d{4}\s+", "", formatted).strip()
    text = re.sub(r"\s+\d{1,3}(?:,\d{3})*\.\d{2}\s+\d{1,3}(?:,\d{3})*\.\d{2}\s+(?:DEBIT|CREDIT|UNKNOWN)$", "", text)
    return text.strip()


def _has_meaningful_rows(rows: list[list[str]]) -> bool:
    meaningful = 0
    for row in rows:
        if not row:
            continue
        description = _description_from_formatted_transaction(row[0])
        if _looks_like_meaningful_description(description):
            meaningful += 1
    return meaningful >= max(1, len(rows) // 3) if rows else False


def _infer_type_from_text(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in [
        " cr", "credit", "deposit", "refund", "salary", "interest", "upi/cr",
        "neft cr", "rtgs cr", "imps cr", "inward", "credited", "cashback",
    ]):
        return "credit"
    if any(keyword in lowered for keyword in [
        " dr", "debit", "withdrawal", "purchase", "upi", "atm", "wdl tfr", "upi/dr",
        "neft dr", "rtgs dr", "imps dr", "pos", "ecom", "nfs", "cwdr", "nfs-cwdr",
        "ach d", "nach", "ecs", "si-", "auto debit", "card",
    ]):
        return "debit"
    return "unknown"
