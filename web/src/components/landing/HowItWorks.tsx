const STEPS = [
  {
    n: 1,
    hash: "#/trial",
    title: "The trial, alive",
    description: "Wearables against personal baselines",
  },
  {
    n: 2,
    hash: "#/checkpoint",
    title: "The checkpoint",
    description: "Every claim through 7 checks",
  },
  {
    n: 3,
    hash: "#/seal",
    title: "Sign and seal",
    description: "Human signature on a tamper-evident chain",
  },
  {
    n: 4,
    hash: "#/verified",
    title: "How this was verified",
    description: "Every number recomputed",
  },
  {
    n: 5,
    hash: "#/proof",
    title: "Proof it works",
    description: "Measured on recorded runs",
  },
];

export function HowItWorks() {
  return (
    <section className="mt-16">
      <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {STEPS.map((step) => (
          <a
            key={step.n}
            href={step.hash}
            className="flex flex-col rounded-lg border border-line bg-card p-4 hover:border-accent"
          >
            <div className="flex items-center gap-2">
              <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft font-mono text-sm font-semibold text-accent">
                {step.n}
              </span>
              <span className="font-medium text-text">{step.title}</span>
            </div>
            <p className="mt-2 text-sm text-muted">{step.description}</p>
          </a>
        ))}
      </div>
    </section>
  );
}
