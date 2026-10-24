import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";

export type Status = "pass" | "watch" | "held";

const CONFIG: Record<
  Status,
  { label: string; Icon: typeof CheckCircle2; bg: string; fg: string }
> = {
  pass: {
    label: "Pass",
    Icon: CheckCircle2,
    bg: "bg-pass-soft",
    fg: "text-pass",
  },
  watch: {
    label: "Watch",
    Icon: AlertTriangle,
    bg: "bg-watch-soft",
    fg: "text-watch",
  },
  held: {
    label: "Held",
    Icon: ShieldAlert,
    bg: "bg-held-soft",
    fg: "text-held",
  },
};

export function StatusPill({
  status,
  label,
}: {
  status: Status;
  label?: string;
}) {
  const { label: defaultLabel, Icon, bg, fg } = CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-sm font-medium ${bg} ${fg}`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span>{label ?? defaultLabel}</span>
    </span>
  );
}
