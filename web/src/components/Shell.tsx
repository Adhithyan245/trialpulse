import { useEffect, useState, type ReactNode } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { health } from "../api";
import { useRole } from "../role";
import type { Role } from "../types";

const SCENES: { hash: string; n: number; label: string }[] = [
  { hash: "#/trial", n: 1, label: "The trial, alive" },
  { hash: "#/checkpoint", n: 2, label: "The checkpoint" },
  { hash: "#/seal", n: 3, label: "Sign and seal" },
  { hash: "#/verified", n: 4, label: "How this was verified" },
  { hash: "#/proof", n: 5, label: "Proof it works" },
];

const ROLES: { id: Role; label: string }[] = [
  { id: "monitor", label: "Monitor" },
  { id: "coordinator", label: "Coordinator" },
  { id: "safety_reviewer", label: "Safety reviewer" },
];

type ThemePref = "light" | "dark" | "system";
const THEME_KEY = "trialpulse.theme";

function readThemePref(): ThemePref {
  try {
    const raw = localStorage.getItem(THEME_KEY);
    if (raw === "light" || raw === "dark" || raw === "system") {
      return raw;
    }
  } catch {
    // ignore
  }
  return "system";
}

function applyTheme(pref: ThemePref): void {
  const root = document.documentElement;
  if (pref === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", pref);
  }
}

function useCurrentHash(): string {
  const [hash, setHash] = useState(() => window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

function ModeBadge() {
  const [mode, setMode] = useState<"live" | "replay" | null>(null);
  useEffect(() => {
    let active = true;
    health()
      .then((h) => {
        if (active) setMode(h.mode);
      })
      .catch(() => {
        if (active) setMode(null);
      });
    return () => {
      active = false;
    };
  }, []);

  if (mode === null) return null;
  const text = mode === "live" ? "Live AI" : "Recorded runs";
  return (
    <span className="inline-flex items-center rounded-full border border-line px-2 py-0.5 font-mono text-xs text-muted">
      {text}
    </span>
  );
}

function ThemeToggle() {
  const [pref, setPref] = useState<ThemePref>(() => readThemePref());

  useEffect(() => {
    applyTheme(pref);
    try {
      localStorage.setItem(THEME_KEY, pref);
    } catch {
      // ignore
    }
  }, [pref]);

  const options: { id: ThemePref; Icon: typeof Sun; title: string }[] = [
    { id: "light", Icon: Sun, title: "Light theme" },
    { id: "dark", Icon: Moon, title: "Dark theme" },
    { id: "system", Icon: Monitor, title: "System theme" },
  ];

  return (
    <div className="inline-flex items-center gap-1" role="group" aria-label="Theme">
      {options.map(({ id, Icon, title }) => (
        <button
          key={id}
          type="button"
          title={title}
          aria-label={title}
          aria-pressed={pref === id}
          onClick={() => setPref(id)}
          className={`rounded-md p-1.5 ${
            pref === id
              ? "bg-accent text-white"
              : "text-muted hover:text-text"
          }`}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </button>
      ))}
    </div>
  );
}

function Wordmark() {
  return (
    <a href="#/" className="flex items-center gap-2 font-semibold tracking-tight">
      <span className="inline-block h-2.5 w-2.5 rounded-full bg-accent" aria-hidden="true" />
      <span>TrialPulse</span>
    </a>
  );
}

function RoleSwitcher() {
  const { role, setRole } = useRole();
  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label="Role">
      {ROLES.map((r) => (
        <button
          key={r.id}
          type="button"
          aria-pressed={role === r.id}
          onClick={() => setRole(r.id)}
          className={`rounded-md px-2.5 py-1 text-sm ${
            role === r.id
              ? "bg-accent text-white"
              : "text-slate-300 hover:bg-white/10"
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}

function NavLinks({ currentHash }: { currentHash: string }) {
  return (
    <nav className="flex flex-col gap-1" aria-label="Scenes">
      {SCENES.map((s) => {
        const active = currentHash === s.hash;
        return (
          <a
            key={s.hash}
            href={s.hash}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm ${
              active ? "bg-white/15 text-white" : "text-slate-300 hover:bg-white/10"
            }`}
          >
            <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-white/30 font-mono text-xs">
              {s.n}
            </span>
            <span>{s.label}</span>
          </a>
        );
      })}
    </nav>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const currentHash = useCurrentHash();

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Navigation: left column on desktop, top bar under 768px. */}
      <header className="flex flex-col gap-4 bg-ink p-4 text-white md:w-64 md:shrink-0">
        <div className="flex items-center justify-between">
          <Wordmark />
          <div className="md:hidden">
            <ThemeToggle />
          </div>
        </div>
        <NavLinks currentHash={currentHash} />
        <div className="flex flex-col gap-3 border-t border-white/10 pt-3">
          <RoleSwitcher />
          <div className="flex items-center justify-between">
            <ModeBadge />
            <div className="hidden md:block">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Working area. */}
      <div className="flex min-w-0 flex-1 flex-col bg-surface">
        <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-line bg-watch-soft px-4 py-1.5 text-sm text-watch">
          <span className="inline-block h-2 w-2 rounded-full bg-watch" aria-hidden="true" />
          <span className="font-medium">Synthetic data</span>
        </div>
        <main className="min-w-0 flex-1 p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
