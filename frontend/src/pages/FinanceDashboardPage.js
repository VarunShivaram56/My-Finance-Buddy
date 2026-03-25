import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import ActionButtonCard from "../components/ActionButtonCard";
import ChartsGrid from "../components/ChartsGrid";
import SummaryCard from "../components/SummaryCard";
import { useAuth } from "../context/AuthContext";
import TypewriterQuotes from "../components/TypewriterQuotes";
import UploadStatusCard from "../components/UploadStatusCard";
import {
  fetchDashboard,
  getFriendlyApiError,
  resetFinancialData,
  uploadStatement,
} from "../services/api";

const EMPTY_DASHBOARD = {
  summary: {
    totalSpending: 0,
    transactionsCount: 0,
    averageDailySpend: 0,
    savingsEstimate: 0,
  },
  monthlySpending: [],
  categoryBreakdown: [],
  dailySpending: [],
  topMerchants: [],
  transactions: [],
  insights: "",
  supportedBanks: [],
  availableCategories: [],
};
const DASHBOARD_CACHE_KEY = "finance_dashboard_summary";
const TRANSACTIONS_CACHE_KEY = "finance_transactions_page";

function FinanceDashboardPage() {
  const { user, logout } = useAuth();
  const [dashboard, setDashboard] = useState(EMPTY_DASHBOARD);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [activeStep, setActiveStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [resetting, setResetting] = useState(false);
  const [selectedBank, setSelectedBank] = useState("karnataka_bank");
  const fileInputRef = useRef(null);
  const processingIntervalRef = useRef(null);
  const processingStartedRef = useRef(false);

  useEffect(() => {
    const cachedDashboard = sessionStorage.getItem(DASHBOARD_CACHE_KEY);
    if (cachedDashboard) {
      try {
        setDashboard(JSON.parse(cachedDashboard));
        setLoading(false);
      } catch (error) {
        sessionStorage.removeItem(DASHBOARD_CACHE_KEY);
      }
    }

    const loadDashboard = async () => {
      try {
        const data = await fetchDashboard();
        setDashboard(data);
        sessionStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(data));
      } catch (err) {
        setError("Unable to load dashboard data. Start the backend and try again.");
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();

    return () => {
      if (processingIntervalRef.current) {
        clearInterval(processingIntervalRef.current);
      }
    };
  }, []);

  const startProcessingUpdates = () => {
    if (processingIntervalRef.current) {
      clearInterval(processingIntervalRef.current);
    }

    processingStartedRef.current = true;

    const phases = [
      { progress: 18, step: 0, message: "PDF uploaded successfully. The backend is receiving your statement." },
      { progress: 42, step: 1, message: "The backend is cleaning rows and validating transaction details." },
      { progress: 72, step: 2, message: "The backend is processing and analyzing merchants, categories, and spend patterns." },
      { progress: 92, step: 3, message: "The dashboard is being prepared with charts and insights." },
    ];

    let phaseIndex = 0;
    setStatusMessage(phases[0].message);
    setActiveStep(phases[0].step);
    setProgress((current) => Math.max(current, phases[0].progress));

    processingIntervalRef.current = setInterval(() => {
      phaseIndex += 1;
      if (phaseIndex >= phases.length) {
        clearInterval(processingIntervalRef.current);
        processingIntervalRef.current = null;
        return;
      }

      setStatusMessage(phases[phaseIndex].message);
      setActiveStep(phases[phaseIndex].step);
      setProgress((current) => Math.max(current, phases[phaseIndex].progress));
    }, 1600);
  };

  const handleFileSelection = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setUploading(true);
    setError("");
    setActiveStep(0);
    setProgress(0);
    setStatusMessage("Preparing your statement for upload.");
    processingStartedRef.current = false;

    try {
      const response = await uploadStatement(file, selectedBank, (progressEvent) => {
        if (!progressEvent.total) {
          return;
        }
        const uploadProgress = Math.min(25, Math.round((progressEvent.loaded / progressEvent.total) * 25));
        setProgress(uploadProgress);
        setActiveStep(0);
        setStatusMessage("Uploading the redacted PDF to the backend.");
        if (uploadProgress >= 25 && !processingStartedRef.current) {
          startProcessingUpdates();
        }
      });

      if (processingIntervalRef.current) {
        clearInterval(processingIntervalRef.current);
        processingIntervalRef.current = null;
      }

      processingStartedRef.current = false;
      setActiveStep(3);
      setProgress(100);
      setStatusMessage(
        `Statement processed successfully. ${response.parsedCount} transactions were analyzed and your dashboard is ready.`
      );
      setDashboard(response.dashboard);
      sessionStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(response.dashboard));
      sessionStorage.removeItem(TRANSACTIONS_CACHE_KEY);
    } catch (err) {
      if (processingIntervalRef.current) {
        clearInterval(processingIntervalRef.current);
        processingIntervalRef.current = null;
      }
      processingStartedRef.current = false;
      setProgress(0);
      setStatusMessage("The upload could not be completed.");
      setError(getFriendlyApiError(err, "Upload failed. Please try another PDF."));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const openRedactionTool = () => {
    window.open("https://www.ilovepdf.com/redact-pdf", "_blank", "noopener,noreferrer");
  };

  const openUnlockTool = () => {
    window.open("https://www.ilovepdf.com/unlock_pdf", "_blank", "noopener,noreferrer");
  };

  const handleResetData = async () => {
    setResetting(true);
    setError("");
    try {
      const response = await resetFinancialData();
      setDashboard(response.dashboard);
      sessionStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(response.dashboard));
      sessionStorage.removeItem(TRANSACTIONS_CACHE_KEY);
      setStatusMessage(response.message);
      setProgress(0);
      setActiveStep(0);
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "Unable to reset data right now."));
    } finally {
      setResetting(false);
    }
  };

  const supportedBanks = dashboard.supportedBanks?.length
    ? dashboard.supportedBanks
    : [
        { key: "karnataka_bank", label: "Karnataka Bank" },
        { key: "canara_bank", label: "Canara Bank" },
        { key: "sbi_bank", label: "SBI Bank" },
      ];

  return (
    <div className="min-h-screen px-4 py-8 sm:px-8">
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={handleFileSelection}
      />

      <div className="mx-auto max-w-7xl">
        <section className="currency-panel rounded-[2rem] border border-white/60 bg-white/75 px-6 py-14 shadow-soft backdrop-blur sm:px-10">
          <div className="mx-auto flex max-w-4xl flex-col items-center">
            <div className="flex w-full flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <span className="mx-auto w-fit rounded-full bg-skywash px-4 py-2 text-sm font-medium text-[#9e5a2c] sm:mx-0">
                Local-first statement intelligence
              </span>
              <div className="inline-flex items-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft">
                {user?.name}
              </div>
            </div>
            <h1 className="mt-6 text-center text-4xl font-semibold tracking-tight text-ink sm:text-6xl">
              My Finance Buddy
            </h1>
            <div className="mt-6">
              <TypewriterQuotes />
            </div>

            <div className="mt-8 flex w-full max-w-3xl flex-wrap items-center justify-center gap-3">
              <Link
                to="/transactions"
                className="inline-flex min-w-[210px] items-center justify-center rounded-2xl bg-white px-6 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6]"
              >
                Manage Transactions
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

            <div className="mt-8 w-full max-w-3xl rounded-3xl bg-white/85 p-5 shadow-soft ring-1 ring-borderSoft">
              <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div className="flex-1">
                  <label className="text-sm font-semibold uppercase tracking-[0.18em] text-[#c58b58]">
                    Select Your Bank
                  </label>
                  <select
                    value={selectedBank}
                    onChange={(event) => setSelectedBank(event.target.value)}
                    className="mt-3 w-full rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  >
                    {supportedBanks.map((bank) => (
                      <option key={bank.key} value={bank.key}>
                        {bank.label}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="max-w-xl text-sm leading-6 text-slate-500">
                  Upload a redacted statement from any supported bank while keeping the same private local-first flow.
                </p>
              </div>
            </div>

            <div className="mt-10 grid w-full max-w-4xl gap-6 md:grid-cols-2">
              <ActionButtonCard
                title={uploading ? "Uploading..." : "Upload Redacted PDF"}
                tooltip="Upload a bank statement that has already been redacted to ensure your financial privacy."
                onClick={() => fileInputRef.current?.click()}
                accent="bg-gradient-to-br from-white to-[#fff2df]"
                disabled={uploading}
              />
              <ActionButtonCard
                title="Redact PDF"
                tooltip="Mask private details like account numbers and personal information before uploading your statement."
                onClick={openRedactionTool}
                accent="bg-gradient-to-br from-white to-[#fff7ee]"
                disabled={uploading}
                secondaryAction={{
                  label: "Unlock Locked PDF",
                  onClick: openUnlockTool,
                }}
              />
            </div>

            <UploadStatusCard
              status={statusMessage}
              activeStep={activeStep}
              progress={progress}
              uploading={uploading}
            />

            <div className="mt-8 text-center text-sm text-slate-500">
              {loading ? "Loading dashboard..." : "Rule-based extraction runs first. LLM agents are used only when confidence is low."}
            </div>
            {error ? <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div> : null}
          </div>
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            label="Total Spending"
            value={`Rs ${dashboard.summary.totalSpending.toFixed(2)}`}
            hint="Total debit transactions"
          />
          <SummaryCard
            label="Transactions Count"
            value={dashboard.summary.transactionsCount}
            hint="Parsed and stored rows"
          />
          <SummaryCard
            label="Average Daily Spend"
            value={`Rs ${dashboard.summary.averageDailySpend.toFixed(2)}`}
            hint="Across active spending days"
          />
          <SummaryCard
            label="Savings Estimate"
            value={`Rs ${dashboard.summary.savingsEstimate.toFixed(2)}`}
            hint="Credits minus debits"
          />
        </section>

        <section className="mt-10">
          <ChartsGrid dashboard={dashboard} />
        </section>

        <section className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={handleResetData}
            disabled={resetting}
            className="rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6] disabled:cursor-not-allowed disabled:opacity-70"
          >
            {resetting ? "Resetting..." : "Reset My Financial Data"}
          </button>
        </section>

        {dashboard.insights ? (
          <section className="currency-panel mt-10 rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft">
            <h3 className="text-lg font-semibold text-ink">AI Insights</h3>
            <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">{dashboard.insights}</div>
          </section>
        ) : null}
      </div>
    </div>
  );
}

export default FinanceDashboardPage;
