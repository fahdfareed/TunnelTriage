import type { Plan } from "../types";

export interface PlanDiff {
  entered: string[];
  left: string[];
  moved: { label: string; delta: number }[];
}

// Compare two plans by action_id for the re-plan diff (SPEC §8.4).
export function computeDiff(prev: Plan | null, next: Plan): PlanDiff {
  const emptyDiff = { entered: [], left: [], moved: [] };
  if (!prev) return emptyDiff;
  const prevRank: Record<string, { rank: number; label: string }> = {};
  prev.funded.forEach((i) =>
    (prevRank[i.action_id] = { rank: i.rank, label: `${i.tunnel_name} · ${i.element_name}` })
  );
  const nextRank: Record<string, { rank: number; label: string }> = {};
  next.funded.forEach((i) =>
    (nextRank[i.action_id] = { rank: i.rank, label: `${i.tunnel_name} · ${i.element_name}` })
  );

  const entered = next.funded
    .filter((i) => !(i.action_id in prevRank))
    .map((i) => `${i.tunnel_name} · ${i.element_name}`);
  const left = prev.funded
    .filter((i) => !(i.action_id in nextRank))
    .map((i) => `${i.tunnel_name} · ${i.element_name}`);
  const moved: { label: string; delta: number }[] = [];
  for (const id of Object.keys(nextRank)) {
    if (id in prevRank) {
      const delta = prevRank[id].rank - nextRank[id].rank;
      if (Math.abs(delta) >= 3) moved.push({ label: nextRank[id].label, delta });
    }
  }
  return { entered, left, moved };
}

export function DiffBanner({ diff }: { diff: PlanDiff | null }) {
  if (!diff) return null;
  if (!diff.entered.length && !diff.left.length && !diff.moved.length) return null;
  return (
    <div className="banner info">
      <strong>Plan changed</strong>
      {diff.entered.length > 0 && <div>Entered: {diff.entered.join("; ")}</div>}
      {diff.left.length > 0 && <div>Left: {diff.left.join("; ")}</div>}
      {diff.moved.length > 0 && (
        <div>
          Moved:{" "}
          {diff.moved
            .map((m) => `${m.label} (${m.delta > 0 ? "↑" : "↓"}${Math.abs(m.delta)})`)
            .join("; ")}
        </div>
      )}
    </div>
  );
}
