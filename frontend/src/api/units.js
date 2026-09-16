import client from "./client";

/**
 * Solve a heat exchanger (sizing or rating).
 * @param {object} payload  - HeatExchangerRequest body
 * @param {boolean} includeLog - whether to include calculation_log in response
 */
export async function solveHX(payload, includeLog = true) {
  const { data } = await client.post(
    `/solve/heat-exchanger?include_log=${includeLog}`,
    payload
  );
  return data;
}

/**
 * Parameter sweep over a single variable.
 * @param {object} payload - ScenarioSweepRequest body
 */
export async function scenarioSweep(payload) {
  const { data } = await client.post("/solve/scenario/sweep", payload);
  return data;
}
