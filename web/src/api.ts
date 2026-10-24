// Tiny fetch client for the TrialPulse API. Sends the current role in the
// X-Role header. Throws an Error with the server's `detail` on non-2xx; never
// fabricates data.

import { getRole } from "./role";
import type {
  AuditEntry,
  AuditVerify,
  Clock,
  Health,
  Metrics,
  RunRecord,
  RunSummary,
  Trial,
} from "./types";

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (body && typeof body.detail === "string") {
      return body.detail;
    }
    return `${res.status} ${res.statusText}`;
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: { "X-Role": getRole() },
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return (await res.json()) as T;
}

export async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Role": getRole(),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return (await res.json()) as T;
}

export function health(): Promise<Health> {
  return getJSON<Health>("/api/health");
}

export function trial(): Promise<Trial> {
  return getJSON<Trial>("/api/trial");
}

export function clock(): Promise<Clock> {
  return getJSON<Clock>("/api/clock");
}

// The participant time series for a given day (metrics, bands and diary).
export function participantSeries(pid: string, day: number): Promise<unknown> {
  return getJSON<unknown>(
    `/api/participants/${encodeURIComponent(pid)}/series?day=${day}`,
  );
}

export function runs(): Promise<RunSummary[]> {
  return getJSON<RunSummary[]>("/api/runs");
}

export function run(caseId: string): Promise<RunRecord> {
  return getJSON<RunRecord>(`/api/runs/${encodeURIComponent(caseId)}`);
}

export function negativeControl(caseId: string): Promise<unknown> {
  return getJSON<unknown>(
    `/api/negative-control/${encodeURIComponent(caseId)}`,
  );
}

export function metrics(): Promise<Metrics> {
  return getJSON<Metrics>("/api/metrics");
}

export function audit(reportId?: string): Promise<AuditEntry[]> {
  const path = reportId
    ? `/api/audit?report_id=${encodeURIComponent(reportId)}`
    : "/api/audit";
  return getJSON<AuditEntry[]>(path);
}

export function auditVerify(): Promise<AuditVerify> {
  return getJSON<AuditVerify>("/api/audit/verify");
}

export function sign(body: unknown): Promise<AuditEntry> {
  return postJSON<AuditEntry>("/api/audit/sign", body);
}

export function tamper(entryId: string): Promise<AuditVerify> {
  return postJSON<AuditVerify>("/api/audit/tamper", { entry_id: entryId });
}
