// Number formatting (SPEC §11.1): $64.7M, $850K, risk points no decimals, % 0 decimals.

export function money(n: number): string {
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
