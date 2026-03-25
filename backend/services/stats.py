from __future__ import annotations

from collections import defaultdict

from database.models import NonBankingTransaction, Transaction
from utils.merchant_rules import CATEGORIES


def empty_dashboard_payload() -> dict:
    return {
        "summary": {
            "totalSpending": 0,
            "transactionsCount": 0,
            "averageDailySpend": 0,
            "savingsEstimate": 0,
        },
        "monthlySpending": [],
        "categoryBreakdown": [],
        "dailySpending": [],
        "topMerchants": [],
        "transactions": [],
        "nonBankTransactions": [],
        "insights": "",
        "supportedBanks": [],
        "availableCategories": CATEGORIES,
    }


def build_dashboard_payload(
    transactions: list[Transaction],
    insights: str = "",
    *,
    include_transactions: bool = True,
    non_banking_transactions: list[NonBankingTransaction] | None = None,
) -> dict:
    non_banking_transactions = non_banking_transactions or []
    total_spending = sum(t.amount for t in transactions if t.transaction_type == "debit")
    total_credit = sum(t.amount for t in transactions if t.transaction_type == "credit")
    monthly_spending: dict[str, float] = defaultdict(float)
    category_breakdown: dict[str, float] = defaultdict(float)
    daily_spending: dict[str, float] = defaultdict(float)
    merchant_totals: dict[str, float] = defaultdict(float)

    for transaction in transactions:
        date_str = transaction.transaction_date.isoformat()
        month_key = date_str[:7]
        if transaction.transaction_type == "debit":
            monthly_spending[month_key] += transaction.amount
            category_breakdown[transaction.category] += transaction.amount
            daily_spending[date_str] += transaction.amount
            merchant_totals[transaction.merchant] += transaction.amount

    for transaction in non_banking_transactions:
        date_str = transaction.transaction_date.isoformat()
        month_key = date_str[:7]
        if transaction.transaction_type == "debit":
            total_spending += transaction.amount
            monthly_spending[month_key] += transaction.amount
            category_breakdown[transaction.category] += transaction.amount
            daily_spending[date_str] += transaction.amount
            merchant_totals[transaction.beneficiary] += transaction.amount
        elif transaction.transaction_type == "credit":
            total_credit += transaction.amount

    average_daily_spend = total_spending / max(len(daily_spending), 1)
    top_merchants = sorted(merchant_totals.items(), key=lambda item: item[1], reverse=True)[:5]

    return {
        "summary": {
            "totalSpending": round(total_spending, 2),
            "transactionsCount": len(transactions) + len(non_banking_transactions),
            "averageDailySpend": round(average_daily_spend, 2),
            "savingsEstimate": round(total_credit - total_spending, 2),
        },
        "monthlySpending": [{"month": month, "amount": round(amount, 2)} for month, amount in sorted(monthly_spending.items())],
        "categoryBreakdown": [{"name": name, "value": round(value, 2)} for name, value in sorted(category_breakdown.items())],
        "dailySpending": [{"date": date, "amount": round(amount, 2)} for date, amount in sorted(daily_spending.items())],
        "topMerchants": [{"merchant": merchant, "amount": round(amount, 2)} for merchant, amount in top_merchants],
        "transactions": (
            [
                {
                    "id": transaction.id,
                    "date": transaction.transaction_date.isoformat(),
                    "merchant": transaction.merchant,
                    "amount": round(transaction.amount, 2),
                    "category": transaction.category,
                    "type": transaction.transaction_type,
                    "description": transaction.description,
                }
                for transaction in sorted(transactions, key=lambda item: item.transaction_date, reverse=True)
            ]
            if include_transactions
            else []
        ),
        "nonBankTransactions": (
            [
                {
                    "id": transaction.id,
                    "date": transaction.transaction_date.isoformat(),
                    "beneficiary": transaction.beneficiary,
                    "amount": round(transaction.amount, 2),
                    "category": transaction.category,
                    "type": transaction.transaction_type,
                    "description": transaction.description,
                }
                for transaction in sorted(non_banking_transactions, key=lambda item: item.transaction_date, reverse=True)
            ]
            if include_transactions
            else []
        ),
        "insights": insights,
        "supportedBanks": [],
        "availableCategories": CATEGORIES,
    }
