import { useState, useEffect } from "react";

const PAGE_SIZE = 20;

function NonBankingTransactionTable({ transactions }) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [transactions]);

  const visibleTransactions = transactions.slice(0, visibleCount);
  const hasMore = visibleCount < transactions.length;

  return (
    <div className="overflow-hidden rounded-3xl bg-white shadow-soft ring-1 ring-borderSoft">
      <div className="flex items-center justify-between border-b border-slate-100 bg-white/90 px-6 py-4">
        <h3 className="text-lg font-semibold text-ink">Non-Banking Transactions</h3>
        <span className="rounded-full bg-skywash px-3 py-1 text-xs font-semibold text-[#9e5a2c]">
          {transactions.length} total
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100">
          <thead className="bg-skywash">
            <tr>
              {["Date", "Beneficiary", "Description", "Amount", "Category", "Transaction Type"].map((column) => (
                <th
                  key={column}
                  className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.18em] text-[#9e5a2c]"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {visibleTransactions.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-6 py-8 text-center text-slate-500">
                  Add a manual cash transaction to keep offline spending or income in one place.
                </td>
              </tr>
            ) : (
              visibleTransactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">{transaction.date}</td>
                  <td className="min-w-[14rem] px-6 py-4 text-sm font-medium text-ink">{transaction.beneficiary}</td>
                  <td className="min-w-[22rem] max-w-[30rem] px-6 py-4 text-sm leading-8 text-slate-600">
                    {transaction.description || "No description"}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">₹{transaction.amount.toFixed(2)}</td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">{transaction.category}</td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600 capitalize">{transaction.type}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {hasMore ? (
        <div className="border-t border-slate-100 bg-[#fffaf4] px-6 py-4 text-center">
          <button
            type="button"
            onClick={() => setVisibleCount((count) => count + PAGE_SIZE)}
            className="rounded-2xl bg-ink px-8 py-3 text-sm font-semibold text-white transition hover:bg-clay"
          >
            Show More ({transactions.length - visibleCount} remaining)
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default NonBankingTransactionTable;
