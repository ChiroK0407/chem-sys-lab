import client from "./client";

/** Returns list of all available fluid objects */
export async function getFluids() {
  const { data } = await client.get("/reference/fluids");
  return data;
}

/**
 * Returns detailed properties for one fluid at an optional temperature.
 * @param {string} fluidId
 * @param {number|null} temperatureC
 */
export async function getFluidDetail(fluidId, temperatureC) {
  const params = temperatureC != null ? { temperature_c: temperatureC } : {};
  const { data } = await client.get(`/reference/fluid/${fluidId}`, { params });
  return data;
}

/** Returns all HX service types with U-value ranges */
export async function getUValues() {
  const { data } = await client.get("/reference/u-values");
  return data;
}

/**
 * Suggest a U-value range based on stream phases.
 * @param {string} hotPhase  - "liquid" | "vapor" | "mixed"
 * @param {string} coldPhase - "liquid" | "vapor" | "mixed"
 */
export async function suggestU(hotPhase, coldPhase) {
  const { data } = await client.get("/reference/u-values/suggest", {
    params: { hot_phase: hotPhase, cold_phase: coldPhase },
  });
  return data;
}

/**
 * Returns saturation properties for a named steam grade.
 * @param {string} grade - "lp_steam" | "mp_steam" | "hp_steam"
 */
export async function getSteamGrade(grade) {
  const { data } = await client.get(`/reference/steam/${grade}`);
  return data;
}

import axios from "axios";

/**
 * Fetch the heat exchanger types catalog from backend using the unified client wrapper.
 * @returns {Promise<Array>} List of HX type dicts
 */
export async function getHXTypes() {
  const { data } = await client.get("/reference/hx-types"); // Clean interceptor routing
  return data;
}
