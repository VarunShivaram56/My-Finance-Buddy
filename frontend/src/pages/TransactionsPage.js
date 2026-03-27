import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import NonBankingTransactionTable from "../components/NonBankingTransactionTable";
import TransactionTable from "../components/TransactionTable";
import { useAuth } from "../context/AuthContext";
import {
  createNonBankingTransaction,
  fetchTransactions,
  getFriendlyApiError,
  updateTransactionCategory,
  updateTransactionType,
} from "../services/api";

const EMPTY_DASHBOARD = {
  transactions: [],
  nonBankTransactions: [],
  availableCategories: [],
};
const DASHBOARD_CACHE_KEY = "finance_dashboard_summary";
const TRANSACTIONS_CACHE_KEY = "finance_transactions_page";

function TransactionsPage() {
  const { user, logout } = useAuth();
  const [dashboard, setDashboard] = useState(EMPTY_DASHBOARD);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [updatingTransactionId, setUpdatingTransactionId] = useState(null);
  const [creatingManualTransaction, setCreatingManualTransaction] = useState(false);
  const [activeTab, setActiveTab] = useState("banking");
  const [manualTransactionForm, setManualTransactionForm] = useState({
    transactionDate: "",
    beneficiary: "",
    description: "",
    transactionType: "debit",
    category: "Others / Uncategorized",
    amount: "",
  });

  useEffect(() => {
    const cachedTransactions = sessionStorage.getItem(TRANSACTIONS_CACHE_KEY);
    if (cachedTransactions) {
      try {
        setDashboard(JSON.parse(cachedTransactions));
        setLoading(false);
      } catch (error) {
        sessionStorage.removeItem(TRANSACTIONS_CACHE_KEY);
      }
    }

    const loadDashboard = async () => {
      try {
        const data = await fetchTransactions();
        setDashboard(data);
        sessionStorage.setItem(TRANSACTIONS_CACHE_KEY, JSON.stringify(data));
      } catch (requestError) {
        setError(getFriendlyApiError(requestError, "Unable to load transactions right now."));
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

  const handleTypeChange = async (transactionId, transactionType) => {
    if (!transactionType) {
      return;
    }

    setUpdatingTransactionId(transactionId);
    setError("");
    try {
      const response = await updateTransactionType(transactionId, transactionType);
      setDashboard(response.dashboard);
      sessionStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify({
        ...response.dashboard,
        transactions: [],
      }));
      sessionStorage.setItem(TRANSACTIONS_CACHE_KEY, JSON.stringify(response.dashboard));
      setStatusMessage(response.message);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to update transaction type."));
    } finally {
      setUpdatingTransactionId(null);
    }
  };

  const handleCategoryChange = async (transactionId, category) => {
    if (!category) {
      return;
    }

    setUpdatingTransactionId(transactionId);
    setError("");
    try {
      const response = await updateTransactionCategory(transactionId, category);
      setDashboard(response.dashboard);
      sessionStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify({
        ...response.dashboard,
        transactions: [],
      }));
      sessionStorage.setItem(TRANSACTIONS_CACHE_KEY, JSON.stringify(response.dashboard));
      setStatusMessage(response.message);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to update transaction category."));
    } finally {
      setUpdatingTransactionId(null);
    }
  };

  const handleManualTransactionSubmit = async (event) => {
    event.preventDefault();
    setCreatingManualTransaction(true);
    setError("");
    try {
      const response = await createNonBankingTransaction({
        ...manualTransactionForm,
        amount: Number(manualTransactionForm.amount),
      });
      setDashboard(response.dashboard);
      sessionStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify({
        ...response.dashboard,
        transactions: [],
        nonBankTransactions: [],
      }));
      sessionStorage.setItem(TRANSACTIONS_CACHE_KEY, JSON.stringify(response.dashboard));
      setStatusMessage(response.message);
      setManualTransactionForm({
        transactionDate: "",
        beneficiary: "",
        description: "",
        transactionType: "debit",
        category: "Others / Uncategorized",
        amount: "",
      });
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to add non-banking transaction."));
    } finally {
      setCreatingManualTransaction(false);
    }
  };

  return (
    <div className="min-h-screen px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-7xl">
        <section className="currency-panel rounded-[2rem] border border-white/60 bg-white/75 px-6 py-10 shadow-soft backdrop-blur sm:px-10">
          <div className="flex flex-col items-center">
            <div className="flex w-full flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <span className="mx-auto w-fit rounded-full bg-skywash px-4 py-2 text-sm font-medium text-[#9e5a2c] sm:mx-0">
                Transaction review and category override
              </span>
              <div className="inline-flex items-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft">
                {user?.name}
              </div>
            </div>

            <h1 className="mt-5 w-full text-center text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
              Transactions
            </h1>
            <p className="mt-3 max-w-3xl text-center text-sm leading-7 text-slate-600">
              Review the backend categorization, adjust any transaction manually, and the same category will be
              applied to similar descriptions automatically.
            </p>

            <div className="mt-8 flex w-full max-w-3xl flex-wrap items-center justify-center gap-3">
              <Link
                to="/"
                className="inline-flex min-w-[190px] items-center justify-center rounded-2xl bg-white px-6 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Back to Dashboard
              </Link>
              <Link
                to="/loans"
                className="inline-flex min-w-[200px] items-center justify-center rounded-2xl bg-white px-6 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Loans & Liabilities
              </Link>
              <Link
                to="/chatbot"
                className="inline-flex min-w-[230px] items-center justify-center rounded-2xl bg-ink px-6 py-3 text-sm font-semibold text-white transition hover:bg-clay"
              >
                Open Finance AI Assistant
              </Link>
              <button
                type="button"
                onClick={logout}
                className="inline-flex min-w-[150px] items-center justify-center rounded-2xl bg-white px-6 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Logout
              </button>
            </div>

          <div className="mt-8 rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft">
            <p className="text-sm leading-7 text-slate-600">
              {loading
                ? "Loading transactions..."
                : "Use the category dropdown to fix classification. Similar descriptions will be updated together."}
            </p>
            {statusMessage ? (
              <div className="mt-4 rounded-2xl bg-[#fff7ee] px-4 py-3 text-sm text-ink">{statusMessage}</div>
            ) : null}
            {error ? <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div> : null}
          </div>
          </div>
        </section>

        <section className="mt-10 pb-8">
          {/* Tab Toggle */}
          <div className="mb-8 flex gap-3">
            <button
              type="button"
              onClick={() => setActiveTab("banking")}
              className={`rounded-2xl px-6 py-3 text-sm font-semibold transition ${
                activeTab === "banking"
                  ? "bg-ink text-white shadow-soft"
                  : "bg-white text-ink shadow-soft ring-1 ring-borderSoft hover:bg-[#fff4e6]"
              }`}
            >
              Banking Transactions ({dashboard.transactions?.length || 0})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("nonBanking")}
              className={`rounded-2xl px-6 py-3 text-sm font-semibold transition ${
                activeTab === "nonBanking"
                  ? "bg-ink text-white shadow-soft"
                  : "bg-white text-ink shadow-soft ring-1 ring-borderSoft hover:bg-[#fff4e6]"
              }`}
            >
              Non-Banking ({(dashboard.nonBankTransactions || []).length})
            </button>
          </div>

          {/* Non-Banking: Add Form + Table */}
          {activeTab === "nonBanking" ? (
            <>
              <div className="mb-8 rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft">
                <div className="flex flex-col gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#c58b58]">
                      Add Cash or Offline Transaction
                    </p>
                    <p className="mt-2 text-sm leading-7 text-slate-600">
                      Add a transaction that did not appear in your bank statement, such as cash spending or cash income.
                    </p>
                  </div>

                  <form onSubmit={handleManualTransactionSubmit} className="rounded-3xl bg-[#fffaf4] p-5 ring-1 ring-[#f4ddc2]">
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
                    <label className="grid gap-2 text-sm text-slate-600 xl:col-span-2">
                      <span className="font-medium text-ink">Date</span>
                      <input
                        type="date"
                        value={manualTransactionForm.transactionDate}
                        onChange={(event) =>
                          setManualTransactionForm((current) => ({ ...current, transactionDate: event.target.value }))
                        }
                        className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                        required
                      />
                    </label>

                    <label className="grid gap-2 text-sm text-slate-600 xl:col-span-3">
                      <span className="font-medium text-ink">Beneficiary</span>
                      <input
                        value={manualTransactionForm.beneficiary}
                        onChange={(event) =>
                          setManualTransactionForm((current) => ({ ...current, beneficiary: event.target.value }))
                        }
                        placeholder="Name of beneficiary"
                        className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                        required
                      />
                    </label>

                    <label className="grid gap-2 text-sm text-slate-600 xl:col-span-3">
                      <span className="font-medium text-ink">Description</span>
                      <input
                        value={manualTransactionForm.description}
                        onChange={(event) =>
                          setManualTransactionForm((current) => ({ ...current, description: event.target.value }))
                        }
                        placeholder="Optional description"
                        className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                      />
                    </label>

                    <label className="grid gap-2 text-sm text-slate-600 xl:col-span-2">
                      <span className="font-medium text-ink">Type</span>
                      <select
                        value={manualTransactionForm.transactionType}
                        onChange={(event) =>
                          setManualTransactionForm((current) => ({ ...current, transactionType: event.target.value }))
                        }
                        className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                      >
                        <option value="debit">Debit</option>
                        <option value="credit">Credit</option>
                      </select>
                    </label>

                    <label className="grid gap-2 text-sm text-slate-600 xl:col-span-2">
                      <span className="font-medium text-ink">Category</span>
                      <select
                        value={manualTransactionForm.category}
                        onChange={(event) =>
                          setManualTransactionForm((current) => ({ ...current, category: event.target.value }))
                        }
                        className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                      >
                        {(dashboard.availableCategories || []).map((category) => (
                          <option key={category} value={category}>
                            {category}
                          </option>
                        ))}
                      </select>
                    </label>
                    </div>

                    <div className="mt-5 flex flex-col gap-4 border-t border-[#f1dfcc] pt-5 sm:flex-row sm:items-end sm:justify-between">
                      <label className="grid gap-2 text-sm text-slate-600 sm:min-w-[240px]">
                        <span className="font-medium text-ink">Amount</span>
                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={manualTransactionForm.amount}
                          onChange={(event) =>
                            setManualTransactionForm((current) => ({ ...current, amount: event.target.value }))
                          }
                          placeholder="0.00"
                          className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                          required
                        />
                      </label>

                      <div className="flex flex-col gap-2 sm:items-end">
                        <p className="text-xs uppercase tracking-[0.18em] text-[#c58b58]">Manual entry</p>
                        <button
                          type="submit"
                          disabled={creatingManualTransaction}
                          className="rounded-2xl bg-ink px-8 py-3 text-sm font-semibold text-white transition hover:bg-clay disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          {creatingManualTransaction ? "Adding..." : "Add Transaction"}
                        </button>
                      </div>
                    </div>
                  </form>
                </div>
              </div>
              <NonBankingTransactionTable transactions={dashboard.nonBankTransactions || []} />
            </>
          ) : (
            <TransactionTable
              transactions={dashboard.transactions}
              categories={dashboard.availableCategories || []}
              onTypeChange={handleTypeChange}
              onCategoryChange={handleCategoryChange}
              updatingId={updatingTransactionId}
            />
          )}
        </section>
      </div>
    </div>
  );
}

export default TransactionsPage;
