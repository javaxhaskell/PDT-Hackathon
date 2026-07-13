const STEPS: { title: string; body: string }[] = [
  {
    title: "Pick two rivals",
    body: "Two stocks that usually move together — think Royal Caribbean vs Carnival, or Coke vs Pepsi.",
  },
  {
    title: "Spot the gap",
    body: "If they normally travel together but have drifted unusually far apart, something interesting is happening.",
  },
  {
    title: "Check the history",
    body: "We replay one simple, unchanged rule on past data it has never seen — after estimated fees — to see if betting on the gap closing actually worked.",
  },
  {
    title: "Get a paper trade",
    body: "If every check passes, you get a suggested paper trade sized to your money and risk comfort — plus an AI read of recent headlines. Nothing is ever really traded.",
  },
];

export default function HowItWorks() {
  return (
    <section
      aria-label="How it works"
      className="rounded-xl border border-edge bg-surface p-6"
    >
      <h2 className="text-sm font-semibold text-ink">
        How it works — the 30-second version
      </h2>
      <ol className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STEPS.map((step, i) => (
          <li key={step.title} className="rounded-lg bg-surface-deep p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-pos-text">
              <span className="flex h-6 w-6 items-center justify-center rounded-full border border-pos/50 font-mono text-xs">
                {i + 1}
              </span>
              {step.title}
            </p>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              {step.body}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
