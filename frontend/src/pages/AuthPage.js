import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { getFriendlyApiError } from "../services/api";

function AuthPage() {
  const { isAuthenticated, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={location.state?.from?.pathname || "/"} replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await register(form);
      } else {
        await login({ email: form.email, password: form.password });
      }
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (requestError) {
      setError(getFriendlyApiError(requestError, `Unable to ${mode} right now.`));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen px-4 py-10 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <section className="currency-panel rounded-[2rem] border border-white/60 bg-white/75 px-6 py-10 shadow-soft backdrop-blur sm:px-10">
          <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="flex flex-col justify-center">
              <span className="w-fit rounded-full bg-skywash px-4 py-2 text-sm font-medium text-[#9e5a2c]">
                Private finance workspace
              </span>
              <h1 className="mt-6 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
                My Finance Buddy
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
                Sign in to keep your transactions private. Each user can access only their own uploaded statements,
                dashboard, and chat context.
              </p>
            </div>

            <div className="rounded-3xl bg-white/90 p-6 shadow-soft ring-1 ring-borderSoft">
              <div className="flex gap-3">
                {[
                  { id: "login", label: "Login" },
                  { id: "register", label: "Register" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => {
                      setMode(tab.id);
                      setError("");
                    }}
                    className={`rounded-2xl px-4 py-2 text-sm font-semibold transition ${
                      mode === tab.id ? "bg-ink text-white" : "bg-[#fff4e6] text-ink"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <form onSubmit={handleSubmit} className="mt-6 grid gap-4">
                {mode === "register" ? (
                  <input
                    value={form.name}
                    onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                    placeholder="Full name"
                    className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                  />
                ) : null}
                <input
                  value={form.email}
                  onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                  placeholder="Email address"
                  type="email"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                />
                <input
                  value={form.password}
                  onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                  placeholder="Password"
                  type="password"
                  className="rounded-2xl border border-borderSoft bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-[#dba168] focus:ring-2 focus:ring-[#f7d6ae]"
                />

                {error ? <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div> : null}

                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-2xl bg-ink px-6 py-3 text-sm font-semibold text-white transition hover:bg-clay disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {loading ? "Please wait..." : mode === "register" ? "Create Account" : "Login"}
                </button>
              </form>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default AuthPage;
