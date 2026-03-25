import TooltipIcon from "./TooltipIcon";

function ActionButtonCard({
  title,
  tooltip,
  onClick,
  accent = "bg-white",
  disabled = false,
  secondaryAction = null,
}) {
  return (
    <div className={`currency-panel relative w-full rounded-3xl ${accent} p-6 shadow-soft ring-1 ring-borderSoft`}>
      <TooltipIcon text={tooltip} />
      <div className="lotus-wave h-5 w-28 rounded-full" />
      <h3 className="mt-4 text-xl font-semibold text-ink">{title}</h3>
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className="mt-6 w-full rounded-2xl bg-ink px-5 py-3 text-base font-semibold text-white transition hover:bg-clay disabled:cursor-not-allowed disabled:opacity-70"
      >
        {title}
      </button>
      {secondaryAction ? (
        <button
          type="button"
          onClick={secondaryAction.onClick}
          disabled={disabled}
          className="mt-3 w-full rounded-2xl bg-white/90 px-5 py-3 text-base font-semibold text-ink shadow-soft ring-1 ring-borderSoft transition hover:bg-[#fff4e6] disabled:cursor-not-allowed disabled:opacity-70"
        >
          {secondaryAction.label}
        </button>
      ) : null}
    </div>
  );
}

export default ActionButtonCard;
