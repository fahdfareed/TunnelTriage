"""Budget anchors (SPEC §3.5) and source URLs (SPEC §17).

Every figure here is a published public number, not a TunnelTriage computation.
Values labelled "approx." are read from charts in the cited documents.
"""

BUDGET_ANCHORS = {
    "cip_fy27_31_tunnels_total": 370_000_000,
    "cip_fy27_31_tunnels_per_year": 74_000_000,
    "contract_tunnel_preservation_2025_program": 64_727_001,
    "contract_cana_2026_program": 128_482_140,
    "contract_ups_2025_program": 21_598_325,
    "contract_four_tunnels_2022": 15_300_000,
    "mhs_10yr_need_2024": 1_950_000_000,
    "bid_vs_estimate_low": -0.32,
    "bid_vs_estimate_high": 0.35,
}

ANCHOR_LABELS = {
    "cip_fy27_31_tunnels_total": "Tunnels program, FY27-31 draft capital plan (approx., read from chart)",
    "cip_fy27_31_tunnels_per_year": "~1 year of the tunnels program (370M / 5)",
    "contract_tunnel_preservation_2025_program": "Tunnel Preservation within MHS Tunnels program budget (bid $52,182,001)",
    "contract_cana_2026_program": "CANA Tunnel & Vent Building Rehab program budget (bid $103,174,700)",
    "contract_ups_2025_program": "Central Artery UPS replacement program budget",
    "contract_four_tunnels_2022": "2022 four-tunnel repair contract",
    "mhs_10yr_need_2024": "10-year need, whole Metropolitan Highway System, all asset types",
    "bid_vs_estimate_low": "Lowest observed bid vs. MassDOT estimate (UPS contract)",
    "bid_vs_estimate_high": "Highest observed bid vs. MassDOT estimate (CANA contract)",
}

SOURCES = {
    "nti_inventory_service": "https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/NTAD_National_Tunnel_Inventory/FeatureServer",
    "nti_element_service": "https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/NTAD_National_Tunnel_Inventory_Element_Data/FeatureServer",
    "nti_element_catalog": "https://catalog.data.gov/dataset/national-tunnel-inventory-element-data1",
    "nti_data_dictionary": "https://doi.org/10.21949/1529051",
    "snti_spec": "https://www.fhwa.dot.gov/bridge/inspection/tunnel/snti/hif15006.pdf",
    "snti_inventory_element": "https://www.fhwa.dot.gov/bridge/inspection/tunnel/snti/inventory_element.pdf",
    "tunnels_by_state_2025": "https://www.fhwa.dot.gov/bridge/inspection/tunnel/inventory/tunnelsbystate2025.cfm",
    "nti_yearly_downloads": "https://www.fhwa.dot.gov/bridge/inspection/tunnel/inventory/download.cfm",
    "massdot_inspection_policy": "https://www.mass.gov/doc/p-25-002-tunnel-inspection-and-testing-program/download",
    "cip_fy27_31": "https://www.mass.gov/doc/draft-fy27-31-capital-investment-plan-presented-to-the-cpc-on-may-13-2026/download",
    "tunnel_preservation_summary": "https://www.mass.gov/doc/staff-summary-for-the-tunnel-preservation-within-mhs-tunnels-presented-to-the-cpc-on-september-10-2025/download",
    "cana_summary": "https://www.mass.gov/doc/staff-summary-for-the-boston-cana-tunnel-and-vent-building-rehabilitation-submitted-to-the-massdot-board-on-september-23-2026/download",
    "ups_summary": "https://www.mass.gov/doc/staff-summary-for-the-boston-ups-system-replacements-in-the-central-artery-tunnels-presented-to-the-cpc-on-november-12-2025/download",
    "mhs_triennial_2024": "https://www.mass.gov/doc/2024-metropolitan-highway-system-triennial-report-presented-at-the-massdot-board-meeting-on-march-19-2025/download",
    "four_tunnels_2022": "https://www.nbcboston.com/news/local/state-to-address-declining-conditions-in-boston-highway-tunnels/2867536/",
}

# ArcGIS layer endpoints used by fetch.py
INVENTORY_LAYER = SOURCES["nti_inventory_service"] + "/0"
ELEMENT_LAYER = SOURCES["nti_element_service"] + "/1"

DATA_YEAR = 2025
