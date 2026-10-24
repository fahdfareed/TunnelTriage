import type {
  Finding,
  Group,
  Health,
  Memo,
  ParseResult,
  Plan,
  Curve,
  Validation,
  Tunnel,
  TunnelDetail,
} from "./types";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`/api${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

async function del<T>(path: string): Promise<T> {
  const r = await fetch(`/api${path}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export const api = {
  health: () => get<Health>("/health"),
  groups: () => get<Group[]>("/groups"),
  tunnels: () => get<Tunnel[]>("/tunnels"),
  tunnel: (id: string) => get<TunnelDetail>(`/tunnels/${id}`),
  dataNotes: () => get<Record<string, unknown>>("/data-notes"),
  config: () => get<Record<string, unknown>>("/config"),
  constants: () => get<Record<string, unknown>>("/constants"),
  plan: (budget: number, horizon?: number) =>
    post<Plan>("/plan", { budget, horizon }),
  validation: () => get<Validation>("/validation"),
  curve: () => get<Curve>("/curve"),
  findings: () => get<Finding[]>("/findings"),
  addFinding: (f: Partial<Finding>) =>
    post<{ finding: Finding; affected_row_key: string }>("/findings", f),
  removeFinding: (id: string) => del<{ ok: boolean }>(`/findings/${id}`),
  resetFindings: () => del<{ ok: boolean }>("/findings"),
  parse: (text: string) => post<ParseResult>("/findings/parse", { text }),
  memo: (plan_id: string) => post<Memo>("/memo", { plan_id }),
};
