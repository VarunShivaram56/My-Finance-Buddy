import { useEffect, useRef, useState } from "react";

const PAGE_SIZE = 20;

function TransactionTable({ transactions, categories, onTypeChange, onCategoryChange, updatingId }) {
  const topScrollRef = useRef(null);
  const bottomScrollRef = useRef(null);
  const tableRef = useRef(null);
  const syncingRef = useRef(false);
  const [scrollWidth, setScrollWidth] = useState(0);
  const [showTopScrollbar, setShowTopScrollbar] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    const updateScrollMetrics = () => {
      if (!tableRef.current || !bottomScrollRef.current) {
        return;
      }

      const nextScrollWidth = tableRef.current.scrollWidth;
      const viewportWidth = bottomScrollRef.current.clientWidth;
      setScrollWidth(nextScrollWidth);
      setShowTopScrollbar(nextScrollWidth > viewportWidth + 8);
    };

    updateScrollMetrics();
    window.addEventListener("resize", updateScrollMetrics);
    return () => window.removeEventListener("resize", updateScrollMetrics);
  }, [transactions, categories]);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [transactions]);

  const syncHorizontalScroll = (source, target) => {
    if (!source || !target || syncingRef.current) {
      return;
    }

    syncingRef.current = true;
    target.scrollLeft = source.scrollLeft;
    window.requestAnimationFrame(() => {
      syncingRef.current = false;
    });
  };

  const visibleTransactions = transactions.slice(0, visibleCount);
  const hasMore = visibleCount < transactions.length;

  return (
    <div className="overflow-hidden rounded-3xl bg-white shadow-soft ring-1 ring-borderSoft">
      <div className="flex items-center justify-between border-b border-slate-100 bg-white/90 px-6 py-4">
        <h3 className="text-lg font-semibold text-ink">Banking Transactions</h3>
        <span className="rounded-full bg-skywash px-3 py-1 text-xs font-semibold text-[#9e5a2c]">
          {transactions.length} total
        </span>
      </div>
      {showTopScrollbar ? (
        <div className="border-b border-slate-100 bg-[#fffaf4] px-6 py-3">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-[#c58b58]">
            Scroll sideways to view all columns
          </div>
          <div
            ref={topScrollRef}
            onScroll={(event) => syncHorizontalScroll(event.currentTarget, bottomScrollRef.current)}
            className="transaction-scrollbar overflow-x-auto"
          >
            <div style={{ width: scrollWidth, height: 1 }} />
          </div>
        </div>
      ) : null}
      <div
        ref={bottomScrollRef}
        onScroll={(event) => syncHorizontalScroll(event.currentTarget, topScrollRef.current)}
        className="transaction-scrollbar overflow-x-auto"
      >
        <table ref={tableRef} className="min-w-[1100px] divide-y divide-slate-100">
          <thead className="bg-skywash">
            <tr>
              {["Date", "Merchant", "Description", "Amount", "Category", "Transaction Type"].map((column) => (
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
                  Upload a redacted statement to populate your dashboard.
                </td>
              </tr>
            ) : (
              visibleTransactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">{transaction.date}</td>
                  <td className="min-w-[14rem] px-6 py-4 text-sm font-medium text-ink">{transaction.merchant}</td>
                  <td className="min-w-[24rem] max-w-[30rem] px-6 py-4 text-sm leading-8 text-slate-600">
                    {transaction.description || "No description"}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">₹{transaction.amount.toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    <select
                      value={transaction.category}
                      disabled={updatingId === transaction.id}
                      onChange={(event) => onCategoryChange(transaction.id, event.target.value)}
                      className="w-64 max-w-full rounded-xl border border-borderSoft bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-[#dba168]"
                    >
                      {categories.map((category) => (
                        <option key={category} value={category}>
                          {category}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">
                    {transaction.type === "unknown" ? (
                      <select
                        value=""
                        disabled={updatingId === transaction.id}
                        onChange={(event) => onTypeChange(transaction.id, event.target.value)}
                        className="rounded-xl border border-borderSoft bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-[#dba168]"
                      >
                        <option value="">Select type</option>
                        <option value="debit">Debit</option>
                        <option value="credit">Credit</option>
                      </select>
                    ) : (
                      <span className="capitalize">{transaction.type}</span>
                    )}
                  </td>
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

export default TransactionTable;
