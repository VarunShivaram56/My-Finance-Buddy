import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { askFinanceAssistant, getFriendlyApiError } from "../services/api";

function ChatbotPage() {
  const { user, logout } = useAuth();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("rag");
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!query.trim()) {
      return;
    }

    const nextQuestion = query.trim();
    setLoading(true);
    setError("");
    setWarning("");
    setCurrentQuestion(nextQuestion);
    setAnswer("");

    try {
      const response = await askFinanceAssistant(nextQuestion, mode);
      setAnswer(response.answer);
      setWarning(response.warning || "");
      setQuery("");
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, "The finance assistant could not answer right now."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <section className="currency-panel rounded-[2rem] border border-white/60 bg-white/75 px-6 py-10 shadow-soft backdrop-blur sm:px-10">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <span className="rounded-full bg-skywash px-4 py-2 text-sm font-medium text-[#9e5a2c]">
                Finance AI with RAG and general chat
              </span>
              <h1 className="mt-5 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
                Finance AI Assistant
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
                Choose retrieval mode for answers grounded in your uploaded data, or general mode for normal LLM chat.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <div className="inline-flex h-fit items-center rounded-2xl bg-white px-4 py-3 text-sm font-medium text-ink shadow-soft ring-1 ring-borderSoft">
                {user?.name}
              </div>
              <Link
                to="/"
                className="inline-flex h-fit items-center rounded-2xl bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-clay"
              >
                Back to Dashboard
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
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end">
              <div className="w-full sm:max-w-xs">
                <label className="text-sm font-semibold uppercase tracking-[0.18em] text-[#c58b58]">
                  Chat Mode
                </label>
                <select
                  value={mode}
                  onChange={(event) => setMode(event.target.value)}
                  className="mt-3 w-full rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                >
                  <option value="rag">RAG Mode</option>
                  <option value="general">General Mode</option>
                </select>
              </div>
              <p className="text-sm leading-6 text-slate-500">
                RAG mode uses your financial data as context. General mode behaves like a normal AI assistant.
              </p>
            </div>

            <div className="grid gap-6">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#c58b58]">User Question</p>
                <div className="mt-3 min-h-16 rounded-2xl bg-[#fffaf4] px-4 py-4 text-sm text-slate-700">
                  {currentQuestion || "Ask a question to get a fresh answer."}
                </div>
              </div>

              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#c58b58]">AI Response</p>
                <div className="mt-3 min-h-40 rounded-2xl bg-[#fffaf4] px-4 py-4 text-sm leading-7 text-slate-700">
                  {loading
                    ? mode === "rag"
                      ? "Retrieving your finance data and preparing an answer..."
                      : "Preparing a general AI response..."
                    : answer || "No answer yet."}
                </div>
              </div>
            </div>

            {error ? <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div> : null}
            {warning ? <div className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-700">{warning}</div> : null}

            <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4 sm:flex-row">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ask about your finances..."
                className="flex-1 rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
              />
              <button
                type="submit"
                disabled={loading}
                className="rounded-2xl bg-ink px-6 py-3 text-sm font-semibold text-white transition hover:bg-clay disabled:cursor-not-allowed disabled:opacity-70"
              >
                Ask AI
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}

export default ChatbotPage;
