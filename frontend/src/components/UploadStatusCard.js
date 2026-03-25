function UploadStatusCard({ status, activeStep, progress, uploading }) {
  if (!status) {
    return null;
  }

  return (
    <div className="currency-panel mt-6 w-full max-w-3xl rounded-3xl border border-[#f2d6ba] bg-white/85 p-5 shadow-soft">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#b97740]">Statement Status</p>
          <p className="mt-2 text-base text-ink">{status}</p>
        </div>
        <div className="rounded-full bg-[#fff1df] px-4 py-2 text-sm font-medium text-[#9e5a2c]">
          {uploading ? `${progress}%` : "Ready"}
        </div>
      </div>

      <div className="mt-4 h-3 overflow-hidden rounded-full bg-[#f8e5d0]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[#e8a15b] via-[#c26c32] to-[#8f9b57] transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-4">
        {[
          "Uploading PDF",
          "Cleaning rows",
          "Analyzing transactions",
          "Preparing dashboard",
        ].map((step, index) => {
          const isActive = index === activeStep;
          const isComplete = index < activeStep || (!uploading && progress === 100);
          return (
            <div
              key={step}
              className={`rounded-2xl px-3 py-3 text-sm ${
                isComplete
                  ? "bg-[#fff1df] text-[#9e5a2c]"
                  : isActive
                    ? "bg-[#fbe6ce] text-ink"
                    : "bg-[#fffaf4] text-slate-500"
              }`}
            >
              {step}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default UploadStatusCard;
