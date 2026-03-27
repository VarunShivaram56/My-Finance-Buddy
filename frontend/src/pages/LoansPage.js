import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

import SummaryCard from "../components/SummaryCard";
import { useAuth } from "../context/AuthContext";
import {
  createLoan,
  deleteLoan,
  fetchLoans,
  getFriendlyApiError,
  updateLoan,
} from "../services/api";

const EMPTY_FORM = {
  loan_name: "",
  lender: "",
  principal_amount: "",
  interest_rate: "",
  tenure_months: "",
  emi_amount: "",
  start_date: "",
  notes: "",
};

function LoansPage() {
  const { user, logout } = useAuth();
  const [loans, setLoans] = useState([]);
  const [summary, setSummary] = useState({
    totalOutstanding: 0,
    monthlyEmiBurden: 0,
    totalLoansCount: 0,
    activeLoansCount: 0,
    completionRate: 0,
    totalInterestPayable: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingPayment, setEditingPayment] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState("");

  useEffect(() => {
    const loadLoans = async () => {
      try {
        const data = await fetchLoans();
        setLoans(data.loans);
        setSummary(data.summary);
      } catch (requestError) {
        setError(getFriendlyApiError(requestError, "Unable to load loans."));
      } finally {
        setLoading(false);
      }
    };
    loadLoans();
  }, []);

  const handleApplyResponse = (response) => {
    setLoans(response.loans);
    setSummary(response.summary);
    setStatusMessage(response.message);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await createLoan({
        ...form,
        principal_amount: Number(form.principal_amount),
        interest_rate: Number(form.interest_rate),
        tenure_months: Number(form.tenure_months),
        emi_amount: Number(form.emi_amount || 0),
      });
      handleApplyResponse(response);
      setForm(EMPTY_FORM);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to add loan."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (loanId) => {
    setError("");
    try {
      const response = await deleteLoan(loanId);
      handleApplyResponse(response);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to delete loan."));
    }
  };

  const handleMarkClosed = async (loanId) => {
    setError("");
    try {
      const response = await updateLoan(loanId, { status: "closed" });
      handleApplyResponse(response);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to update loan."));
    }
  };

  const handleRecordPayment = async (loanId) => {
    const amount = Number(paymentAmount);
    if (!amount || amount <= 0) return;
    setError("");
    try {
      const loan = loans.find((l) => l.id === loanId);
      const newTotalPaid = (loan?.totalPaid || 0) + amount;
      const response = await updateLoan(loanId, { total_paid: newTotalPaid });
      handleApplyResponse(response);
      setEditingPayment(null);
      setPaymentAmount("");
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to record payment."));
    }
  };

  return (
    <div className="min-h-screen px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <section className="currency-panel rounded-[2rem] border border-white/60 bg-white/75 px-6 py-10 shadow-soft backdrop-blur sm:px-10">
          <div className="flex flex-col items-center">
            <div className="flex w-full flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <span className="mx-auto w-fit rounded-full bg-skywash px-4 py-2 text-sm font-medium text-[#9e5a2c] sm:mx-0">
                Loan and liability tracking
              </span>
              <div className="inline-flex items-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft">
                {user?.name}
              </div>
            </div>

            <h1 className="mt-5 w-full text-center text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
              Loans & Liabilities
            </h1>
            <p className="mt-3 max-w-3xl text-center text-sm leading-7 text-slate-600">
              Track your active loans, EMI burden, and payoff progress in one place.
            </p>

            <div className="mt-8 flex w-full max-w-3xl flex-wrap items-center justify-center gap-3">
              <Link
                to="/"
                className="inline-flex min-w-[190px] items-center justify-center rounded-2xl bg-white px-6 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Back to Dashboard
              </Link>
              <Link
                to="/transactions"
                className="inline-flex min-w-[210px] items-center justify-center rounded-2xl bg-white px-6 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Manage Transactions
              </Link>
              <button
                type="button"
                onClick={logout}
                className="inline-flex min-w-[150px] items-center justify-center rounded-2xl bg-white px-6 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Logout
              </button>
            </div>

            {statusMessage ? (
              <div className="mt-6 w-full max-w-3xl rounded-2xl bg-[#fff7ee] px-4 py-3 text-sm text-ink">{statusMessage}</div>
            ) : null}
            {error ? (
              <div className="mt-4 w-full max-w-3xl rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>
            ) : null}
          </div>
        </section>

        {/* Stats */}
        <section className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            label="Total Outstanding"
            value={`₹${summary.totalOutstanding.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            hint={`${summary.activeLoansCount} active loan${summary.activeLoansCount !== 1 ? "s" : ""}`}
          />
          <SummaryCard
            label="Monthly EMI Burden"
            value={`₹${summary.monthlyEmiBurden.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            hint="Total monthly payments"
          />
          <SummaryCard
            label="Completion Rate"
            value={`${summary.completionRate}%`}
            hint="Across all active loans"
          />
          <SummaryCard
            label="Total Interest"
            value={`₹${summary.totalInterestPayable.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            hint="Estimated interest payable"
          />
        </section>

        {/* Add Loan Form */}
        <section className="mt-10 rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#c58b58]">Add New Loan</p>
          <form onSubmit={handleSubmit} className="mt-4 rounded-3xl bg-[#fffaf4] p-5 ring-1 ring-[#f4ddc2]">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Loan Name</span>
                <input
                  value={form.loan_name}
                  onChange={(e) => setForm((f) => ({ ...f, loan_name: e.target.value }))}
                  placeholder="e.g. Home Loan - SBI"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Lender</span>
                <input
                  value={form.lender}
                  onChange={(e) => setForm((f) => ({ ...f, lender: e.target.value }))}
                  placeholder="e.g. State Bank of India"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Principal Amount</span>
                <input
                  type="number"
                  min="1"
                  step="0.01"
                  value={form.principal_amount}
                  onChange={(e) => setForm((f) => ({ ...f, principal_amount: e.target.value }))}
                  placeholder="₹0.00"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Interest Rate (% p.a.)</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.interest_rate}
                  onChange={(e) => setForm((f) => ({ ...f, interest_rate: e.target.value }))}
                  placeholder="e.g. 8.5"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Tenure (Months)</span>
                <input
                  type="number"
                  min="1"
                  value={form.tenure_months}
                  onChange={(e) => setForm((f) => ({ ...f, tenure_months: e.target.value }))}
                  placeholder="e.g. 240"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">EMI Amount</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.emi_amount}
                  onChange={(e) => setForm((f) => ({ ...f, emi_amount: e.target.value }))}
                  placeholder="₹0.00"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Start Date</span>
                <input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Notes</span>
                <input
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="Optional notes"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                />
              </label>
            </div>
            <div className="mt-5 flex justify-end border-t border-[#f1dfcc] pt-5">
              <button
                type="submit"
                disabled={submitting}
                className="rounded-2xl bg-ink px-8 py-3 text-sm font-semibold text-white transition hover:bg-clay disabled:cursor-not-allowed disabled:opacity-70"
              >
                {submitting ? "Adding..." : "Add Loan"}
              </button>
            </div>
          </form>
        </section>

        {/* Loan Cards */}
        <section className="mt-10 pb-8">
          <p className="mb-6 text-sm font-semibold uppercase tracking-[0.18em] text-[#c58b58]">
            Your Loans ({loans.length})
          </p>

          {loading ? (
            <p className="text-sm text-slate-500">Loading loans...</p>
          ) : loans.length === 0 ? (
            <div className="rounded-3xl bg-white/90 p-8 shadow-soft ring-1 ring-borderSoft text-center">
              <p className="text-slate-500 text-sm">No loans added yet. Use the form above to track your first loan.</p>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2">
              {loans.map((loan) => (
                <div
                  key={loan.id}
                  className="currency-panel rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-ink">{loan.loanName}</h3>
                      <p className="mt-1 text-sm text-slate-500">{loan.lender}</p>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        loan.status === "active"
                          ? "bg-[#e8f5e9] text-[#2e7d32]"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {loan.status === "active" ? "Active" : "Closed"}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>Paid: ₹{loan.totalPaid.toLocaleString()}</span>
                      <span>{loan.completionPercentage}%</span>
                    </div>
                    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[#f2d6ba]">
                      <div
                        className="h-full rounded-full bg-[#e8a15b] transition-all duration-500"
                        style={{ width: `${Math.min(loan.completionPercentage, 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Details Grid */}
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-xs text-slate-400">Principal</span>
                      <p className="font-semibold text-ink">₹{loan.principalAmount.toLocaleString()}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">Interest Rate</span>
                      <p className="font-semibold text-ink">{loan.interestRate}% p.a.</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">EMI</span>
                      <p className="font-semibold text-ink">₹{loan.emiAmount.toLocaleString()}/mo</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">Remaining</span>
                      <p className="font-semibold text-ink">{loan.monthsRemaining} months</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">Outstanding</span>
                      <p className="font-semibold text-ink">₹{loan.remainingBalance.toLocaleString()}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">Total Interest</span>
                      <p className="font-semibold text-ink">₹{loan.totalInterest.toLocaleString()}</p>
                    </div>
                  </div>

                  {loan.notes ? (
                    <p className="mt-3 rounded-xl bg-[#fffaf4] px-3 py-2 text-xs text-slate-500 italic">{loan.notes}</p>
                  ) : null}

                  {/* Payment Entry */}
                  {editingPayment === loan.id ? (
                    <div className="mt-4 flex items-center gap-3">
                      <input
                        type="number"
                        min="1"
                        step="0.01"
                        value={paymentAmount}
                        onChange={(e) => setPaymentAmount(e.target.value)}
                        placeholder="Payment amount"
                        className="flex-1 rounded-xl border border-borderSoft bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-[#dba168]"
                      />
                      <button
                        type="button"
                        onClick={() => handleRecordPayment(loan.id)}
                        className="rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-clay"
                      >
                        Record
                      </button>
                      <button
                        type="button"
                        onClick={() => { setEditingPayment(null); setPaymentAmount(""); }}
                        className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-ink ring-1 ring-borderSoft hover:bg-[#fff4e6]"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : null}

                  {/* Action Buttons */}
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-[#f1dfcc] pt-4">
                    {loan.status === "active" ? (
                      <>
                        <button
                          type="button"
                          onClick={() => { setEditingPayment(loan.id); setPaymentAmount(""); }}
                          className="rounded-xl bg-white px-4 py-2 text-xs font-semibold text-ink ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
                        >
                          Record Payment
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMarkClosed(loan.id)}
                          className="rounded-xl bg-white px-4 py-2 text-xs font-semibold text-ink ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
                        >
                          Mark Closed
                        </button>
                      </>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => handleDelete(loan.id)}
                      className="rounded-xl bg-white px-4 py-2 text-xs font-semibold text-red-600 ring-1 ring-red-200 transition hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default LoansPage;
