"use client";

import { useId, useState } from "react";

/**
 * Accessible "How this works" popover: a keyboard-focusable button that
 * toggles a short explanation. Closes on Escape or blur.
 */
export default function InfoTip({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className="relative inline-block">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
        onBlur={() => setOpen(false)}
        className="text-[11px] text-faint underline decoration-edge underline-offset-4 transition-colors hover:text-ink hover:decoration-muted focus:text-ink focus:outline-none focus-visible:border-b focus-visible:border-ink"
      >
        How this works
      </button>
      {open && (
        <span
          role="note"
          id={id}
          className="absolute right-0 top-full z-20 mt-2 block w-64 rounded-none border border-edge bg-surface-deep p-3 text-xs leading-relaxed text-muted"
        >
          {text}
        </span>
      )}
    </span>
  );
}
