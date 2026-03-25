function SummaryCard({ label, value, hint }) {
  return (
    <div className="currency-panel rounded-3xl bg-white/90 p-5 shadow-soft ring-1 ring-borderSoft">
      <p className="text-sm font-medium uppercase tracking-[0.18em] text-[#c58b58]">{label}</p>
      <h3 className="mt-4 text-3xl font-semibold text-ink">{value}</h3>
      <p className="mt-2 text-sm text-slate-500">{hint}</p>
    </div>
  );
}

export default SummaryCard;
