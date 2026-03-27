from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from database.models import NonBankingTransaction, Transaction
from utils.merchant_rules import CATEGORIES


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def empty_dashboard_payload() -> dict:
    return {
        "summary": {
            "totalSpending": 0,
            "transactionsCount": 0,
            "averageDailySpend": 0,
            "totalIncome": 0,
            "highestSingleSpend": {"amount": 0, "merchant": "—"},
            "uniqueMerchantCount": 0,
        },
        "monthlySpending": [],
        "categoryBreakdown": [],
        "dailySpending": [],
        "topMerchants": [],
        "creditVsDebit": [],
        "weekdaySpending": [],
        "topCategories": [],
        "recurringMerchants": [],
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
    total_spending = 0.0
    total_credit = 0.0
    highest_spend_amount = 0.0
    highest_spend_merchant = "—"
    all_merchants: set[str] = set()

    monthly_spending: dict[str, float] = defaultdict(float)
    category_breakdown: dict[str, float] = defaultdict(float)
    daily_spending: dict[str, float] = defaultdict(float)
    merchant_totals: dict[str, float] = defaultdict(float)
    merchant_counts: dict[str, int] = defaultdict(int)
    weekday_totals: dict[int, float] = defaultdict(float)

    for transaction in transactions:
        date_str = transaction.transaction_date.isoformat()
        month_key = date_str[:7]
        all_merchants.add(transaction.merchant)

        if transaction.transaction_type == "debit":
            total_spending += transaction.amount
            monthly_spending[month_key] += transaction.amount
            category_breakdown[transaction.category] += transaction.amount
            daily_spending[date_str] += transaction.amount
            merchant_totals[transaction.merchant] += transaction.amount
            merchant_counts[transaction.merchant] += 1

            weekday_index = transaction.transaction_date.weekday()
            weekday_totals[weekday_index] += transaction.amount

            if transaction.amount > highest_spend_amount:
                highest_spend_amount = transaction.amount
                highest_spend_merchant = transaction.merchant
        elif transaction.transaction_type == "credit":
            total_credit += transaction.amount

    for transaction in non_banking_transactions:
        date_str = transaction.transaction_date.isoformat()
        month_key = date_str[:7]
        all_merchants.add(transaction.beneficiary)

        if transaction.transaction_type == "debit":
            total_spending += transaction.amount
            monthly_spending[month_key] += transaction.amount
            category_breakdown[transaction.category] += transaction.amount
            daily_spending[date_str] += transaction.amount
            merchant_totals[transaction.beneficiary] += transaction.amount
            merchant_counts[transaction.beneficiary] += 1

            weekday_index = transaction.transaction_date.weekday()
            weekday_totals[weekday_index] += transaction.amount

            if transaction.amount > highest_spend_amount:
                highest_spend_amount = transaction.amount
                highest_spend_merchant = transaction.beneficiary
        elif transaction.transaction_type == "credit":
            total_credit += transaction.amount

    average_daily_spend = total_spending / max(len(daily_spending), 1)
    top_merchants = sorted(merchant_totals.items(), key=lambda item: item[1], reverse=True)[:5]

    # Credit vs Debit breakdown
    credit_vs_debit = [
        {"name": "Income (Credits)", "value": round(total_credit, 2)},
        {"name": "Expenses (Debits)", "value": round(total_spending, 2)},
    ]

    # Weekday spending pattern
    weekday_spending = [
        {"day": DAY_NAMES[i], "amount": round(weekday_totals.get(i, 0), 2)}
        for i in range(7)
    ]

    # Top categories by spending
    sorted_categories = sorted(category_breakdown.items(), key=lambda item: item[1], reverse=True)[:7]
    top_categories = [{"name": name, "value": round(value, 2)} for name, value in sorted_categories]

    # Recurring merchants (3+ transactions)
    recurring_merchants = []
    for merchant, count in sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True):
        if count >= 3:
            total = merchant_totals[merchant]
            recurring_merchants.append({
                "merchant": merchant,
                "count": count,
                "total": round(total, 2),
                "average": round(total / count, 2),
            })
    recurring_merchants = recurring_merchants[:10]

    return {
        "summary": {
            "totalSpending": round(total_spending, 2),
            "transactionsCount": len(transactions) + len(non_banking_transactions),
            "averageDailySpend": round(average_daily_spend, 2),
            "totalIncome": round(total_credit, 2),
            "highestSingleSpend": {
                "amount": round(highest_spend_amount, 2),
                "merchant": highest_spend_merchant,
            },
            "uniqueMerchantCount": len(all_merchants),
        },
        "monthlySpending": [{"month": month, "amount": round(amount, 2)} for month, amount in sorted(monthly_spending.items())],
        "categoryBreakdown": [{"name": name, "value": round(value, 2)} for name, value in sorted(category_breakdown.items())],
        "dailySpending": [{"date": date, "amount": round(amount, 2)} for date, amount in sorted(daily_spending.items())],
        "topMerchants": [{"merchant": merchant, "amount": round(amount, 2)} for merchant, amount in top_merchants],
        "creditVsDebit": credit_vs_debit,
        "weekdaySpending": weekday_spending,
        "topCategories": top_categories,
        "recurringMerchants": recurring_merchants,
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
