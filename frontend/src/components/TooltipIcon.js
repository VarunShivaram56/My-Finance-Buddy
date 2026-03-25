import { useState } from "react";
import { FiHelpCircle } from "react-icons/fi";

function TooltipIcon({ text }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="absolute right-3 top-3"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="rounded-full bg-white/90 p-1 text-slate-500 shadow-sm ring-1 ring-slate-200 transition hover:text-slate-700"
        aria-label="More information"
      >
        <FiHelpCircle size={16} />
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-2 w-64 rounded-xl bg-ink px-3 py-2 text-sm text-white shadow-soft">
          {text}
        </div>
      )}
    </div>
  );
}

export default TooltipIcon;
