export interface Health {
  ok: boolean;
  data_year: number;
  n_tunnels: number;
  n_rows: number;
  n_scored_rows: number;
  dictionary_source: string;
  llm_provider: string;
}

export interface Group {
  group_id: string;
  name: string;
  lat: number | null;
  lon: number | null;
  segments: string[];
  adt_max: number;
  risk_now: number;
}

export interface Tunnel {
  tunnel_number: string;
  name: string;
  year_built: number;
  year_rehab: number;
  adt: number;
  adtt: number;
  length_ft: number;
  under_water: boolean;
  lat: number | null;
  lon: number | null;
  last_inspection_date: string | null;
  inspection_interval_months: number;
  group_id: string;
  risk_now?: number;
}

export interface ElementRow {
  key: string;
  element_number: number;
  epn: number;
  total: number;
  cs: [number, number, number, number];
  shares: [number, number, number, number];
  dq_flags: string[];
  scored: boolean;
  element_name: string;
  category: string;
  criticality: number;
  risk_now: number;
}

export interface ForecastPoint {
  year: number;
  risk: number;
}

export interface TunnelDetail {
  tunnel: Tunnel;
  elements: ElementRow[];
  forecast: ForecastPoint[];
}

export interface PlanItem {
  action_id: string;
  rank: number;
  tunnel_number: string;
  tunnel_name: string;
  group_id: string;
  element_number: number;
  element_name: string;
  action: string;
  qty: number;
  cost_point: number;
  cost_low: number;
  cost_high: number;
  benefit: number;
  benefit_per_million: number;
  risk_now_row: number;
  reason_codes: string[];
}

export interface Waiting {
  cost_now: number;
  cost_in_2y: number;
  cost_increase_pct: number;
  extra_risk_2y: number;
  note: string;
}

export interface GroupPlan {
  group_id: string;
  risk_now: number;
  risk_now_after: number;
  funded_cost: number;
}

export interface Plan {
  plan_id: string;
  budget: number;
  horizon: number;
  solver: string;
  funded: PlanItem[];
  unfunded_top: PlanItem[];
  unfunded_by_group: Record<string, PlanItem[]>;
  total_cost_point: number;
  total_cost_low: number;
  total_cost_high: number;
  program_cost_point: number;
  risk_now: number;
  risk_now_after: number;
  risk_h_floor: number;
  n_rows_no_action: number;
  n_rows_scored: number;
  risk_h_do_nothing: number;
  risk_h_with_plan: number;
  risk_reduction_pct: number;
  by_group: GroupPlan[];
  forced_unmet: string[];
  waiting: Waiting;
}

export interface Finding {
  finding_id: string;
  tunnel_number: string;
  element_number: number;
  epn: number;
  quantity: number;
  condition_state: number;
  source: string;
  note: string;
  created_at: string;
}

export interface ParseResult {
  proposal: {
    tunnel_number: string | null;
    element_number: number | null;
    quantity: number;
    condition_state: number;
    note: string;
  };
  tunnel_candidates: { tunnel_number: string; label: string; score: number }[];
  element_candidates: { element_number: number; label: string; score: number }[];
  used_llm: boolean;
}

export interface Memo {
  markdown: string;
  source: string;
  warnings: string[];
}

export interface Curve {
  points: { budget: number; risk_now_after: number }[];
  risk_now: number;
}

export interface Validation {
  contract: { contract: string; title: string; bid_opening: string; source: string; scope_tunnels: string[]; items_note: string };
  bid: {
    office_estimate: number; low_bid: number; second_bid: number;
    low_bid_vs_estimate_pct: number; second_bid_vs_estimate_pct: number;
    program_total: number; program_over_bid_pct: number;
    mobilization_low_bid: number; mobilization_pct_of_bid: number; mobilization_two_bid_avg: number;
    bidders_who_bid: number; eligible_bidders: number;
  };
  assumed_bid_range: { low: number; high: number };
  unit_rates: {
    unit_type: string; tier: string; state: string; our_rate: number; observed_median: number;
    observed_min: number; observed_max: number; n_items: number; ratio: number;
  }[];
  spend_by_category: { category: string; amount: number }[];
  backtest: {
    backlog_severe_all: number; backlog_poor_and_severe_all: number; program_5yr_anchor: number; need_10yr_anchor: number;
    model_cost_severe_only: number; model_cost_poor_and_severe: number; severe_only_ratio_to_bid: number;
    plan_budget: number; plan_funded_total: number; scope_share_of_funded_pct: number;
    scope_funded: Record<string, number>; top5_funded_groups: string[]; scope_tunnels_in_top5: number;
    scope_tunnels_funded: number; callahan_ceiling_panels_good_pct: number | null; callahan_contract_spend: number; callahan_model_funded: number;
    contract: { scope_tunnels: string[]; low_bid: number };
  };
  assumptions: { cost_scale: number; mobilization_pct: number; program_overheads: Record<string, number> };
}
