const STEPS: { title: string; body: string }[] = [
  {
    title: "Pick two rivals",
    body: "Two stocks that usually move together, like Coke and Pepsi.",
  },
  {
    title: "Spot the gap",
    body: "Flag when the pair has drifted unusually far apart.",
  },
  {
    title: "Check the history",
    body: "Replay one fixed rule on unseen past data, after estimated fees.",
  },
  {
    title: "Get a paper trade",
    body: "If every check passes, a paper trade is sized to your budget and risk; nothing is ever traded.",
  },
];

export default function HowItWorks() {
  return (
    <section
      aria-label="How it works"
      className="rounded-none border border-edge bg-surface p-6"
    >
      <h2 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
        How it works
      </h2>
      <ol className="mt-5 grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {STEPS.map((step, i) => (
          <li key={step.title} className="border-t border-edge pt-3">
            <p className="flex items-baseline gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-ink">
              <span className="font-mono text-faint">0{i + 1}</span>
              {step.title}
            </p>
            <p className="mt-2 text-[13px] leading-relaxed text-muted">
              {step.body}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
