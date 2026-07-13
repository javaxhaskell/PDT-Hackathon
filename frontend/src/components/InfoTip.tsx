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
        className="rounded-full border border-edge px-2 py-0.5 text-xs text-muted transition-colors hover:border-muted hover:text-ink focus:outline-none focus:ring-2 focus:ring-pos-bright"
      >
        How this works
      </button>
      {open && (
        <span
          role="note"
          id={id}
          className="absolute right-0 top-full z-20 mt-2 block w-64 rounded-lg border border-edge bg-surface-deep p-3 text-xs leading-relaxed text-ink shadow-xl"
        >
          {text}
        </span>
      )}
    </span>
  );
}
