from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BankProfile:
    key: str
    label: str
    extractor_family: str


STANDARD_LEDGER_FAMILY = "standard_ledger"
CANARA_LEDGER_FAMILY = "canara_ledger"
SBI_LEDGER_FAMILY = "sbi_ledger"


SUPPORTED_BANK_PROFILES: dict[str, BankProfile] = {
    "karnataka_bank": BankProfile(
        key="karnataka_bank",
        label="Karnataka Bank",
        extractor_family=STANDARD_LEDGER_FAMILY,
    ),
    "canara_bank": BankProfile(
        key="canara_bank",
        label="Canara Bank",
        extractor_family=CANARA_LEDGER_FAMILY,
    ),
    "sbi_bank": BankProfile(
        key="sbi_bank",
        label="SBI Bank",
        extractor_family=SBI_LEDGER_FAMILY,
    ),
}


def get_bank_profile(bank_name: str | None) -> BankProfile:
    normalized = (bank_name or "").strip().lower()
    if normalized in SUPPORTED_BANK_PROFILES:
        return SUPPORTED_BANK_PROFILES[normalized]
    return SUPPORTED_BANK_PROFILES["karnataka_bank"]


def get_supported_banks_payload() -> list[dict[str, str]]:
    return [
        {"key": profile.key, "label": profile.label}
        for profile in SUPPORTED_BANK_PROFILES.values()
    ]
