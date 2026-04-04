import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from "recharts";

import SummaryCard from "../components/SummaryCard";
import { useAuth } from "../context/AuthContext";
import {
  createLoan,
  deleteLoan,
  fetchLoans,
  getFriendlyApiError,
  updateLoan,
  fetchAssets,
  createAsset,
  deleteAsset,
} from "../services/api";

const PIE_COLORS = ["#e8a15b", "#f3c48d", "#c26c32", "#f7ddb9", "#8f9b57", "#d98a48", "#a3704a", "#bfa679"];

const EMPTY_LOAN_FORM = {
  loan_name: "",
  lender: "",
  principal_amount: "",
  interest_rate: "",
  tenure_months: "",
  emi_amount: "",
  start_date: "",
  notes: "",
};

const EMPTY_ASSET_FORM = {
  asset_name: "",
  purchase_price: "",
  purchase_year: "",
  rate_per_year: "",
  asset_type: "appreciating",
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
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  
  const [submittingLoan, setSubmittingLoan] = useState(false);
  const [loanForm, setLoanForm] = useState(EMPTY_LOAN_FORM);
  const [editingPayment, setEditingPayment] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState("");

  const [submittingAsset, setSubmittingAsset] = useState(false);
  const [assetForm, setAssetForm] = useState(EMPTY_ASSET_FORM);

  useEffect(() => {
    const p = Number(loanForm.principal_amount);
    const r = Number(loanForm.interest_rate) / 12 / 100;
    const n = Number(loanForm.tenure_months);
    if (p > 0 && r > 0 && n > 0) {
      const emi = (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
      setLoanForm(f => ({ ...f, emi_amount: emi.toFixed(2) }));
    } else if (p > 0 && r === 0 && n > 0) {
      setLoanForm(f => ({ ...f, emi_amount: (p / n).toFixed(2) }));
    }
  }, [loanForm.principal_amount, loanForm.interest_rate, loanForm.tenure_months]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [loanRes, assetRes] = await Promise.all([
          fetchLoans().catch(() => ({ loans: [], summary: {} })),
          fetchAssets().catch(() => ({ assets: [] }))
        ]);
        setLoans(loanRes.loans || []);
        if (loanRes.summary) setSummary(loanRes.summary);
        setAssets(assetRes.assets || []);
      } catch (requestError) {
        setError(getFriendlyApiError(requestError, "Unable to load data."));
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleLoanApplyResponse = (response) => {
    setLoans(response.loans);
    setSummary(response.summary);
    setStatusMessage(response.message || "Loans updated.");
  };

  const handleLoanSubmit = async (event) => {
    event.preventDefault();
    setSubmittingLoan(true);
    setError("");
    try {
      const response = await createLoan({
        ...loanForm,
        principal_amount: Number(loanForm.principal_amount),
        interest_rate: Number(loanForm.interest_rate),
        tenure_months: Number(loanForm.tenure_months),
        emi_amount: Number(loanForm.emi_amount || 0),
      });
      handleLoanApplyResponse(response);
      setLoanForm(EMPTY_LOAN_FORM);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to add loan."));
    } finally {
      setSubmittingLoan(false);
    }
  };

  const handleLoanDelete = async (loanId) => {
    setError("");
    try {
      const response = await deleteLoan(loanId);
      handleLoanApplyResponse(response);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to delete loan."));
    }
  };

  const handleLoanMarkClosed = async (loanId) => {
    setError("");
    try {
      const response = await updateLoan(loanId, { status: "closed" });
      handleLoanApplyResponse(response);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to update loan."));
    }
  };

  const handleLoanRecordPayment = async (loanId) => {
    const amount = Number(paymentAmount);
    if (!amount || amount <= 0) return;
    setError("");
    try {
      const loan = loans.find((l) => l.id === loanId);
      const newTotalPaid = (loan?.totalPaid || 0) + amount;
      const response = await updateLoan(loanId, { total_paid: newTotalPaid });
      handleLoanApplyResponse(response);
      setEditingPayment(null);
      setPaymentAmount("");
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to record payment."));
    }
  };

  const handleAssetSubmit = async (event) => {
    event.preventDefault();
    setSubmittingAsset(true);
    setError("");
    try {
      const rate = Number(assetForm.rate_per_year || 0);
      const finalRate = assetForm.asset_type === "depreciating" ? -Math.abs(rate) : Math.abs(rate);
      const payload = { ...assetForm };
      delete payload.asset_type;
      
      const response = await createAsset({
        ...payload,
        purchase_price: Number(assetForm.purchase_price),
        purchase_year: Number(assetForm.purchase_year),
        rate_per_year: finalRate,
      });
      setAssets(response.assets || []);
      setStatusMessage("Asset added successfully.");
      setAssetForm(EMPTY_ASSET_FORM);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to add asset."));
    } finally {
      setSubmittingAsset(false);
    }
  };

  const handleAssetDelete = async (assetId) => {
    setError("");
    try {
      const response = await deleteAsset(assetId);
      setAssets(response.assets || []);
      setStatusMessage("Asset deleted successfully.");
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to delete asset."));
    }
  };

  const currentYear = new Date().getFullYear();
  const enrichedAssets = assets.map(asset => {
    let years = currentYear - asset.purchase_year;
    if (years < 0) years = 0;
    const factor = Math.pow(1 + asset.rate_per_year / 100, years);
    const currentValue = asset.purchase_price * factor;
    return { ...asset, currentValue, years };
  });

  const totalAssetsValue = enrichedAssets.reduce((sum, a) => sum + (a.currentValue || 0), 0);
  const totalLiabilitiesValue = summary?.totalOutstanding || 0;

  const netWorthData = [
    { name: "Total Assets", value: totalAssetsValue, fill: "#8f9b57" },
    { name: "Total Liabilities", value: totalLiabilitiesValue, fill: "#e8a15b" }
  ].filter(d => d.value > 0);

  const assetDistributionData = enrichedAssets.map((a, i) => ({
    name: a.asset_name,
    value: Math.round(a.currentValue),
    fill: PIE_COLORS[i % PIE_COLORS.length]
  })).filter(d => d.value > 0);

  return (
    <div className="min-h-screen px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <section className="currency-panel rounded-[2rem] border border-white/60 bg-white/75 px-6 py-10 shadow-soft backdrop-blur sm:px-10">
          <div className="flex flex-col items-center">
            <div className="flex w-full flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <span className="mx-auto w-fit rounded-full bg-skywash px-4 py-2 text-sm font-medium text-[#9e5a2c] sm:mx-0">
                Asset and liability tracking
              </span>
              <div className="inline-flex items-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft">
                {user?.name}
              </div>
            </div>

            <h1 className="mt-5 w-full text-center text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
              Assets & Liabilities
            </h1>
            <p className="mt-3 max-w-3xl text-center text-sm leading-7 text-slate-600">
              Track your active loans, map your assets (appreciating and depreciating), and stay ahead of your net worth.
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

        {/* Portfolio Visualizations */}
        {!loading && (netWorthData.length > 0 || assetDistributionData.length > 0) && (
          <section className="mt-10 grid gap-6 md:grid-cols-2">
            {netWorthData.length > 0 && (
              <div className="currency-panel rounded-3xl bg-white/90 p-5 shadow-soft ring-1 ring-borderSoft">
                <h3 className="mb-4 text-lg font-semibold text-ink">Assets vs Liabilities</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={netWorthData}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={90}
                        label={({ name, value }) => `₹${value.toLocaleString()}`}
                        labelLine={false}
                      >
                        {netWorthData.map((d, i) => <Cell key={d.name} fill={d.fill} />)}
                      </Pie>
                      <RechartsTooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            
            {assetDistributionData.length > 0 && (
              <div className="currency-panel rounded-3xl bg-white/90 p-5 shadow-soft ring-1 ring-borderSoft">
                <h3 className="mb-4 text-lg font-semibold text-ink">Asset Distribution</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={assetDistributionData}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={90}
                        label={({ name }) => name}
                      >
                       {assetDistributionData.map((d, i) => <Cell key={d.name} fill={d.fill} />)}
                      </Pie>
                      <RechartsTooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </section>
        )}

        {/* Stats */}
        <section className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            label="Total Outstanding"
            value={`₹${(summary?.totalOutstanding || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            hint={`${summary?.activeLoansCount || 0} active loan${summary?.activeLoansCount !== 1 ? "s" : ""}`}
          />
          <SummaryCard
            label="Monthly EMI Burden"
            value={`₹${(summary?.monthlyEmiBurden || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            hint="Total monthly payments"
          />
          <SummaryCard
            label="Total Assets Value"
            value={`₹${totalAssetsValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            hint="Based on current estimated value"
          />
          <SummaryCard
            label="Net Worth"
            value={`₹${(totalAssetsValue - totalLiabilitiesValue).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            hint="Assets minus liabilities"
          />
        </section>

        {/* Add Asset Form */}
        <section className="mt-10 rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#8f9b57]">Add New Asset</p>
          <form onSubmit={handleAssetSubmit} className="mt-4 rounded-3xl bg-[#f7f9f2] p-5 ring-1 ring-[#e0e5ce]">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Asset Name</span>
                <input
                  value={assetForm.asset_name}
                  onChange={(e) => setAssetForm((f) => ({ ...f, asset_name: e.target.value }))}
                  placeholder="e.g. Real Estate, Car, Gold"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#a0ad62] focus:ring-2 focus:ring-[#d5e0a6]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Purchase Price</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={assetForm.purchase_price}
                  onChange={(e) => setAssetForm((f) => ({ ...f, purchase_price: e.target.value }))}
                  placeholder="₹0.00"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#a0ad62] focus:ring-2 focus:ring-[#d5e0a6]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Purchase Year</span>
                <input
                  type="number"
                  min="1900"
                  max="2100"
                  value={assetForm.purchase_year}
                  onChange={(e) => setAssetForm((f) => ({ ...f, purchase_year: e.target.value }))}
                  placeholder="e.g. 2020"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#a0ad62] focus:ring-2 focus:ring-[#d5e0a6]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Asset Type</span>
                <select
                  value={assetForm.asset_type}
                  onChange={(e) => setAssetForm((f) => ({ ...f, asset_type: e.target.value }))}
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#a0ad62] focus:ring-2 focus:ring-[#d5e0a6]"
                >
                  <option value="appreciating">Appreciating</option>
                  <option value="depreciating">Depreciating</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Rate (% per year)</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={assetForm.rate_per_year}
                  onChange={(e) => setAssetForm((f) => ({ ...f, rate_per_year: e.target.value }))}
                  placeholder="e.g. 5.5"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#a0ad62] focus:ring-2 focus:ring-[#d5e0a6]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600 xl:col-span-2">
                <span className="font-medium text-ink">Notes</span>
                <input
                  value={assetForm.notes}
                  onChange={(e) => setAssetForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="Optional notes"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#a0ad62] focus:ring-2 focus:ring-[#d5e0a6]"
                />
              </label>
            </div>
            <div className="mt-5 flex justify-end border-t border-[#e0e5ce] pt-5">
              <button
                type="submit"
                disabled={submittingAsset}
                className="rounded-2xl bg-[#8f9b57] px-8 py-3 text-sm font-semibold text-white transition hover:bg-[#a0ad62] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {submittingAsset ? "Adding..." : "Add Asset"}
              </button>
            </div>
          </form>
        </section>

        {/* Assets Cards */}
        {assets.length > 0 && (
          <section className="mt-10 pb-4">
            <p className="mb-6 text-sm font-semibold uppercase tracking-[0.18em] text-[#8f9b57]">
              Your Assets ({assets.length})
            </p>
            <div className="grid gap-6 md:grid-cols-2">
              {enrichedAssets.map((asset) => (
                <div key={asset.id} className="currency-panel rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-ink">{asset.asset_name}</h3>
                      <p className="mt-1 text-sm text-slate-500">Bought in {asset.purchase_year}</p>
                    </div>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-xs text-slate-400">Purchase Price</span>
                      <p className="font-semibold text-ink">₹{asset.purchase_price.toLocaleString()}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">Return Rate</span>
                      <p className={`font-semibold ${asset.rate_per_year >= 0 ? 'text-[#2e7d32]' : 'text-red-600'}`}>
                        {asset.rate_per_year}% p.a.
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">Today's Est. Value</span>
                      <p className="font-semibold text-[#8f9b57]">₹{asset.currentValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">Holding Period</span>
                      <p className="font-semibold text-ink">{asset.years} years</p>
                    </div>
                  </div>
                  {asset.notes && <p className="mt-3 rounded-xl bg-[#f7f9f2] px-3 py-2 text-xs text-slate-500 italic">{asset.notes}</p>}
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-[#f1dfcc] pt-4">
                    <button
                      type="button"
                      onClick={() => handleAssetDelete(asset.id)}
                      className="rounded-xl bg-white px-4 py-2 text-xs font-semibold text-red-600 ring-1 ring-red-200 transition hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Add Loan Form */}
        <section className="mt-10 rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#c58b58]">Add New Loan</p>
          <form onSubmit={handleLoanSubmit} className="mt-4 rounded-3xl bg-[#fffaf4] p-5 ring-1 ring-[#f4ddc2]">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Loan Name</span>
                <input
                  value={loanForm.loan_name}
                  onChange={(e) => setLoanForm((f) => ({ ...f, loan_name: e.target.value }))}
                  placeholder="e.g. Home Loan - SBI"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Lender</span>
                <input
                  value={loanForm.lender}
                  onChange={(e) => setLoanForm((f) => ({ ...f, lender: e.target.value }))}
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
                  value={loanForm.principal_amount}
                  onChange={(e) => setLoanForm((f) => ({ ...f, principal_amount: e.target.value }))}
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
                  value={loanForm.interest_rate}
                  onChange={(e) => setLoanForm((f) => ({ ...f, interest_rate: e.target.value }))}
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
                  value={loanForm.tenure_months}
                  onChange={(e) => setLoanForm((f) => ({ ...f, tenure_months: e.target.value }))}
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
                  value={loanForm.emi_amount}
                  onChange={(e) => setLoanForm((f) => ({ ...f, emi_amount: e.target.value }))}
                  placeholder="₹0.00"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Start Date</span>
                <input
                  type="date"
                  value={loanForm.start_date}
                  onChange={(e) => setLoanForm((f) => ({ ...f, start_date: e.target.value }))}
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-slate-600">
                <span className="font-medium text-ink">Notes</span>
                <input
                  value={loanForm.notes}
                  onChange={(e) => setLoanForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="Optional notes"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                />
              </label>
            </div>
            <div className="mt-5 flex justify-end border-t border-[#f1dfcc] pt-5">
              <button
                type="submit"
                disabled={submittingLoan}
                className="rounded-2xl bg-ink px-8 py-3 text-sm font-semibold text-white transition hover:bg-clay disabled:cursor-not-allowed disabled:opacity-70"
              >
                {submittingLoan ? "Adding..." : "Add Loan"}
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
            <div className="rounded-3xl bg-white/90 p-8 text-center shadow-soft ring-1 ring-borderSoft">
              <p className="text-sm text-slate-500">No loans added yet. Use the form above to track your first loan.</p>
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

                  {loan.notes && (
                    <p className="mt-3 rounded-xl bg-[#fffaf4] px-3 py-2 text-xs italic text-slate-500">{loan.notes}</p>
                  )}

                  {/* Payment Entry */}
                  {editingPayment === loan.id && (
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
                        onClick={() => handleLoanRecordPayment(loan.id)}
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
                  )}

                  {/* Action Buttons */}
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-[#f1dfcc] pt-4">
                    {loan.status === "active" && (
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
                          onClick={() => handleLoanMarkClosed(loan.id)}
                          className="rounded-xl bg-white px-4 py-2 text-xs font-semibold text-ink ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
                        >
                          Mark Closed
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      onClick={() => handleLoanDelete(loan.id)}
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
