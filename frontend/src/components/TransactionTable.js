function TransactionTable({ transactions, categories, onTypeChange, onCategoryChange, updatingId }) {
  return (
    <div className="overflow-hidden rounded-3xl bg-white shadow-soft ring-1 ring-borderSoft">
      <div className="border-b border-slate-100 bg-white/90 px-6 py-4">
        <h3 className="text-lg font-semibold text-ink">Transactions</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100">
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
            {transactions.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-6 py-8 text-center text-slate-500">
                  Upload a redacted statement to populate your dashboard.
                </td>
              </tr>
            ) : (
              transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">{transaction.date}</td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-ink">{transaction.merchant}</td>
                  <td className="min-w-[26rem] px-6 py-4 text-sm text-slate-600">{transaction.description || "No description"}</td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600">Rs {transaction.amount.toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    <select
                      value={transaction.category}
                      disabled={updatingId === transaction.id}
                      onChange={(event) => onCategoryChange(transaction.id, event.target.value)}
                      className="w-56 rounded-xl border border-borderSoft bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-[#dba168]"
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
    </div>
  );
}

export default TransactionTable;
