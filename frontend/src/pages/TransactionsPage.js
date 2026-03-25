import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import TransactionTable from "../components/TransactionTable";
import { useAuth } from "../context/AuthContext";
import {
  fetchTransactions,
  getFriendlyApiError,
  updateTransactionCategory,
  updateTransactionType,
} from "../services/api";

const EMPTY_DASHBOARD = {
  transactions: [],
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

  return (
    <div className="min-h-screen px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-7xl">
        <section className="currency-panel rounded-[2rem] border border-white/60 bg-white/75 px-6 py-10 shadow-soft backdrop-blur sm:px-10">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <span className="rounded-full bg-skywash px-4 py-2 text-sm font-medium text-[#9e5a2c]">
                Transaction review and category override
              </span>
              <h1 className="mt-5 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
                Transactions
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
                Review the backend categorization, adjust any transaction manually, and the same category will be
                applied to similar descriptions automatically.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <div className="inline-flex h-fit items-center rounded-2xl bg-white px-4 py-3 text-sm font-medium text-ink shadow-soft ring-1 ring-borderSoft">
                {user?.name}
              </div>
              <Link
                to="/"
                className="inline-flex h-fit items-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Back to Dashboard
              </Link>
              <Link
                to="/chatbot"
                className="inline-flex h-fit items-center rounded-2xl bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-clay"
              >
                Open Finance AI Assistant
              </Link>
              <button
                type="button"
                onClick={logout}
                className="inline-flex h-fit items-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Logout
              </button>
            </div>
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
        </section>

        <section className="mt-10 pb-8">
          <TransactionTable
            transactions={dashboard.transactions}
            categories={dashboard.availableCategories || []}
            onTypeChange={handleTypeChange}
            onCategoryChange={handleCategoryChange}
            updatingId={updatingTransactionId}
          />
        </section>
      </div>
    </div>
  );
}

export default TransactionsPage;
