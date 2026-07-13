import { EDUCATIONAL_DISCLAIMER } from "@/lib/copy";

export default function WarningsFooter({ warnings }: { warnings: string[] }) {
  // The backend is the single source of warnings (it always includes the
  // standard list); the frontend adds only its permanent disclaimer.
  return (
    <footer
      aria-label="Warnings and assumptions"
      className="rounded-xl border border-edge bg-surface-deep p-5"
    >
      <h3 className="text-xs font-semibold uppercase tracking-widest text-muted">
        Warnings and assumptions
      </h3>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-xs leading-relaxed text-muted">
        {warnings.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
      <p className="mt-4 border-t border-edge pt-3 text-xs font-semibold leading-relaxed text-warn-text">
        {EDUCATIONAL_DISCLAIMER}
      </p>
    </footer>
  );
}
