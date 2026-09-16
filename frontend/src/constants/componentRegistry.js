export const COMPONENT_REGISTRY = {
  // ── CORE UNIT OPERATIONS ──
  PUMP: {
    label: "Centrifugal Pump",
    category: "Core Units",
    endpoint: "/solve/pump",
    ports: { inlets: ["feed"], outlets: ["outlet"] },
    idPrefix: "P-"
  },
  HEAT_EXCHANGER: {
    label: "Heat Exchanger",
    category: "Core Units",
    endpoint: "/solve/heat-exchanger",
    ports: { inlets: ["hot", "cold"], outlets: ["hot_out", "cold_out"] },
    idPrefix: "E-"
  },
  MIXER: {
    label: "Adiabatic Stream Mixer",
    category: "Core Units",
    endpoint: "/solve/mixer",
    // Mixers dynamically accept N streams, but map to static handles for baseline auto-layout
    ports: { inlets: ["inlet_1", "inlet_2"], outlets: ["outlet"] }, 
    idPrefix: "MX-"
  },
  SPLITTER: {
    label: "Stream Splitter",
    category: "Core Units",
    endpoint: "/solve/splitter",
    ports: { inlets: ["feed"], outlets: ["overhead", "bottoms"] },
    idPrefix: "SP-"
  },
  CSTR: {
    label: "Continuous Stirred Tank Reactor",
    category: "Core Units",
    endpoint: "/solve/cstr",
    ports: { inlets: ["feed"], outlets: ["outlet"] },
    idPrefix: "R-CSTR-"
  },
  PFR: {
    label: "Plug Flow Reactor",
    category: "Core Units",
    endpoint: "/solve/pfr",
    ports: { inlets: ["feed"], outlets: ["outlet"] },
    idPrefix: "R-PFR-"
  },

  // ── HYDROCARBON RECOVERY STACK ──
  HC_FEED: {
    label: "Purge Feed / Boundary",
    category: "HC Recovery",
    endpoint: "/api/hc-recovery/feed",
    ports: { inlets: [], outlets: ["outlet"] },
    idPrefix: "FEED-"
  },
  ADSORPTION: {
    label: "Adsorption Bed (VPSA/TSA)",
    category: "HC Recovery",
    endpoint: "/api/hc-recovery/adsorption",
    ports: { inlets: ["feed"], outlets: ["product", "tail_gas"] },
    idPrefix: "ADS-"
  },
  CONDENSATION: {
    label: "Cryogenic Condensation Unit",
    category: "HC Recovery",
    endpoint: "/api/hc-recovery/condensation",
    ports: { inlets: ["feed"], outlets: ["liquid_out", "gas_out"] },
    idPrefix: "COND-"
  },
  MEMBRANE: {
    label: "Membrane Separator Stage",
    category: "HC Recovery",
    endpoint: "/api/hc-recovery/membrane",
    ports: { inlets: ["feed"], outlets: ["permeate", "retentate"] },
    idPrefix: "MEMB-"
  }
};