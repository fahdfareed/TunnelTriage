// Number formatting (SPEC §11.1): $64.7M, $850K, risk points no decimals, % 0 decimals.

export function money(n: number): string {
  if (Math.abs(n) >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${Math.round(n / 1_000)}K`;
  return `$${Math.round(n)}`;
}

export function moneyRange(low: number, high: number): string {
  return `${money(low)}-${money(high)}`;
}

export function riskPoints(n: number): string {
  return `${Math.round(n).toLocaleString()} risk points`;
}

export function pct(n: number): string {
  return `${Math.round(n)}%`;
}

export function num(n: number): string {
  return Math.round(n).toLocaleString();
}

// Condition colours (SPEC §11.3). Always pair with a label/tooltip.
export const CS_COLORS = ["#2e7d32", "#9ccc65", "#ffa726", "#c62828"];
export const CS_LABELS = ["Good", "Fair", "Poor", "Severe"];

const REASON_TEXT: Record<string, string> = {
  HIGH_CS4_SHARE: "10%+ of the element is severe",
  HIGH_TRAFFIC: "high traffic",
  UNDER_WATER: "under water",
  OVERHEAD_ELEMENT: "overhead element",
  NEW_FINDING: "new field finding",
  SAFETY_FLOOR: "safety-critical, funded first",
};

// Plain-English "why this first?" for a plan line.
export function whyText(codes: string[]): string {
  const parts = codes.map((c) => REASON_TEXT[c] ?? c.replace(/_/g, " ").toLowerCase());
  return parts.length ? parts.join(", ") : "highest risk reduction per dollar";
}

function csvCell(v: string | number): string {
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function downloadCsv(filename: string, rows: (string | number)[][]) {
  const body = rows.map((r) => r.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([body], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// "THOMAS P. TIP ONEILL JR TUNNEL - 93NB" -> "Thomas P. Tip Oneill Jr Tunnel"
export function tunnelLabel(name: string): string {
  return name
    .replace(/\s+-\s+\w+$/, "")
    .toLowerCase()
    .replace(/\b[a-z]/g, (c) => c.toUpperCase())
    .replace(/\bI-(\d+)/gi, "I-$1")
    .replace(/\b(Eb|Wb|Nb|Sb)\b/g, (m) => m.toUpperCase());
}
