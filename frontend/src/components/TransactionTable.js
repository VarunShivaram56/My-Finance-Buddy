import { useEffect, useRef, useState } from "react";

const ITEMS_PER_PAGE = 10;

function TransactionTable({ transactions, categories, onTypeChange, onCategoryChange, updatingId }) {
  const topScrollRef = useRef(null);
  const bottomScrollRef = useRef(null);
  const tableRef = useRef(null);
  const syncingRef = useRef(false);

  const [scrollWidth, setScrollWidth] = useState(0);
  const [showTopScrollbar, setShowTopScrollbar] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

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
  }, [transactions, categories, currentPage]);

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

  const totalPages = Math.ceil((transactions?.length || 0) / ITEMS_PER_PAGE);
  const visibleTransactions = (transactions || []).slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const renderPaginationButtons = () => {
    let pages = [];
    let start = Math.max(1, currentPage - 2);
    let end = Math.min(totalPages, currentPage + 2);

    if (start > 1) {
      pages.push(1);
      if (start > 2) pages.push("...");
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    if (end < totalPages) {
      if (end < totalPages - 1) pages.push("...");
      pages.push(totalPages);
    }

    return pages.map((p, idx) => {
      if (p === "...") {
        return (
          <span key={`ellipsis-${idx}`} className="flex h-8 w-8 items-center justify-center text-slate-400">
            ...
          </span>
        );
      }
      return (
        <button
          key={`page-${p}`}
          onClick={() => setCurrentPage(p)}
          className={`flex h-8 w-8 items-center justify-center rounded-lg text-sm font-semibold ${
            currentPage === p ? "bg-ink text-white" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          {p}
        </button>
      );
    });
  };

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
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-100 bg-[#fffaf4] px-6 py-4">
          <button
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((p) => p - 1)}
            className="rounded-xl px-4 py-2 text-sm font-semibold text-ink ring-1 ring-borderSoft disabled:opacity-50"
          >
            Previous
          </button>
          <div className="flex gap-2">{renderPaginationButtons()}</div>
          <button
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((p) => p + 1)}
            className="rounded-xl px-4 py-2 text-sm font-semibold text-ink ring-1 ring-borderSoft disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default TransactionTable;
