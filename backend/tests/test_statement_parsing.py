import unittest

from services.parsing import parse_transaction_text
from services.pdf_extractor import (
    _parse_dual_date_statement_block,
    _parse_ledger_transaction_block,
    _parse_table_transaction_block,
)


class StatementParsingTests(unittest.TestCase):
    def test_canara_multiline_block_extracts_amount_and_credit_type(self):
        block = (
            "02-02-2026 UPI/CR/228540259397/GURURA J S/SBIN/**67575@YBL/PAYMENT "
            "//YBL657FF56278E949A59F12C06B9B20DE4A/02/02/2026 12:25:37 "
            "Chq: 228540259397 12,000.00 80,708.80"
        )

        parsed = _parse_ledger_transaction_block(block, prev_balance=68708.80)

        self.assertIsNotNone(parsed)
        formatted, balance = parsed
        self.assertEqual(balance, 80708.80)
        self.assertEqual(
            formatted,
            "02-02-2026 UPI/CR/228540259397/GURURA J S/SBIN/**67575@YBL/PAYMENT "
            "//YBL657FF56278E949A59F12C06B9B20DE4A/02/02/2026 12:25:37 12000.00 80708.80 CREDIT",
        )

    def test_sbi_upi_debit_extracts_counterparty_name(self):
        raw_text = (
            "02/02/2026 WDL TFR UPI/DR/228540259397/SHIVARAM/CNRB/shivaram19/Paym "
            "0097690162095 AT 05622 12,000.00 495.30 DEBIT"
        )

        transaction = parse_transaction_text(raw_text)

        self.assertEqual(transaction.date, "2026-02-02")
        self.assertEqual(transaction.amount, 12000.00)
        self.assertEqual(transaction.transaction_type, "debit")
        self.assertEqual(transaction.merchant, "SHIVARAM")

    def test_canara_upi_credit_extracts_counterparty_name(self):
        raw_text = (
            "02-02-2026 UPI/CR/228540259397/GURURA J S/SBIN/**67575@YBL/PAYMENT "
            "12,000.00 80,708.80 CREDIT"
        )

        transaction = parse_transaction_text(raw_text)

        self.assertEqual(transaction.date, "2026-02-02")
        self.assertEqual(transaction.amount, 12000.00)
        self.assertEqual(transaction.transaction_type, "credit")
        self.assertEqual(transaction.merchant, "GURURA J S")

    def test_sbi_table_block_merges_multiline_details(self):
        block = [
            ["02/02/2026", "02/02/2026", "WDL TFR", "-", "12,000.00", "", "495.30"],
            ["", "", "UPI/DR/228540259397/SHIVARAM/CNRB/shivaram19/Paym", "", "", "", ""],
            ["", "", "0097690162095 AT 05622", "", "", "", ""],
            ["", "", "HASSAN", "", "", "", ""],
        ]

        parsed = _parse_table_transaction_block(block, prev_balance=12495.30)

        self.assertIsNotNone(parsed)
        formatted, balance = parsed
        self.assertEqual(balance, 495.30)
        self.assertIn("SHIVARAM", formatted)
        self.assertTrue(formatted.endswith("12000.00 495.30 DEBIT"))

    def test_malformed_numeric_only_row_does_not_create_fake_merchant(self):
        raw_text = "28/02/2026 28/02/2026 - 30.00 - 68,455.30 30.00 68455.30 DEBIT"

        transaction = parse_transaction_text(raw_text)

        self.assertEqual(transaction.date, "2026-02-28")
        self.assertEqual(transaction.amount, 30.00)
        self.assertEqual(transaction.transaction_type, "debit")
        self.assertIsNone(transaction.merchant)

    def test_sbi_dual_date_text_block_keeps_details(self):
        block = [
            "02/02/2026 02/02/2026 WDL TFR - 12,000.00 - 495.30",
            "UPI/DR/228540259397/SHIVARAM/CNRB/shivaram19/Paym",
            "0097690162095 AT 05622",
            "HASSAN",
        ]

        parsed = _parse_dual_date_statement_block(block, prev_balance=12495.30)

        self.assertIsNotNone(parsed)
        formatted, balance = parsed
        self.assertEqual(balance, 495.30)
        self.assertIn("SHIVARAM", formatted)
        self.assertIn("HASSAN", formatted)
        self.assertTrue(formatted.endswith("12000.00 495.30 DEBIT"))


if __name__ == "__main__":
    unittest.main()
