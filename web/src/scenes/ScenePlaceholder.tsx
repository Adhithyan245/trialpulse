import type { ReactNode } from "react";

export function ScenePlaceholder({
  n,
  title,
  purpose,
  children,
}: {
  n: number;
  title: string;
  purpose: string;
  children?: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center gap-2 font-mono text-sm text-muted">
        Scene {n}
      </div>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-3 text-muted">{purpose}</p>
      {children}
      <p className="mt-6 rounded-md border border-dashed border-line bg-card p-4 text-sm text-muted">
        Built in the next task.
      </p>
    </div>
  );
}
