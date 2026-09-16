/**
 * frontend/src/api/hcRecovery.js
 * * Client abstraction layer for the Hydrocarbon Recovery Technology Assessment Platform.
 * Routes serialization streams directly to the FastAPI backend controllers.
 */

import client from './client';

/**
 * @typedef {Object} FeedInputPayload
 * @property {number} flowrate_kmol_hr - Gaseous mixture total molar flowrate (kmol/hr).
 * @property {number} pressure_MPa - Feed static header pressure drop limit (MPa).
 * @property {number} temperature_C - Vent gas exit stream temperature (°C).
 * @property {number} x_N2 - Molar composition fraction of Nitrogen carrier gas [0.0 - 1.0].
 * @property {number} x_C3H6 - Molar composition fraction of Propylene monomer [0.0 - 1.0].
 * @property {number} x_C3H8 - Molar composition fraction of Propane saturated alkane [0.0 - 1.0].
 */

/**
 * Sends stream properties to be checked against physical constraints and to calculate potential flare mass loss metrics.
 * * @async
 * @function characterizeFeed
 * @param {FeedInputPayload} payload - The feedstock configuration matrix parameters.
 * @returns {Promise<Object>} The characterized stream layout maps and yearly metric tonnage loss projections.
 */
export const characterizeFeed = async (payload) => {
  const response = await client.post('/api/hc-recovery/feed', payload);
  return response.data;
};

/**
 * Executes a vapor-liquid equilibrium (VLE) sweep across the target condenser chill loop bounds.
 * * @async
 * @function simulateCondensation
 * @param {Object} payload
 * @param {FeedInputPayload} payload.feed - Base validated stream composition sub-model.
 * @param {number} payload.T_min_C - Chiller target lowest operating temperature point (°C).
 * @param {number} payload.T_max_C - Chiller highest sweep evaluation temperature point (°C).
 * @param {number} payload.P_bar - Absolute condensation processing pressure (bar).
 * @returns {Promise<Object>} Swept charting rows, optimal thermodynamic recovery node, and phase splits.
 */
export const simulateCondensation = async (payload) => {
  const response = await client.post('/api/hc-recovery/condensation', payload);
  return response.data;
};

/**
 * Simulates multi-component competitive fixed-bed adsorption capacities using the Extended Langmuir Isotherm engine.
 * * @async
 * @function simulateAdsorption
 * @param {Object} payload
 * @param {FeedInputPayload} payload.feed - Core purge stream feed model mapping.
 * @param {number} payload.pressure_bar - Solid column bed adsorption pressure threshold (bar).
 * @param {'activated_carbon'|'zeolite_13x'|'molecular_sieve_5a'} payload.adsorbent - Targeted active core media token.
 * @param {number} payload.adsorbent_mass_kg - Absolute raw active bed media mass charge (kg).
 * @returns {Promise<Object>} Equilibrium loadings (mol/kg), estimated yield conversions, and pressure sweeps.
 */
export const simulateAdsorption = async (payload) => {
  const response = await client.post('/api/hc-recovery/adsorption', payload);
  return response.data;
};

/**
 * Evaluates transport mass transfer flows across a polymeric solution-diffusion gas separation stage.
 * * @async
 * @function simulateMembrane
 * @param {Object} payload
 * @param {FeedInputPayload} payload.feed - Incoming raw process feedstock specifications.
 * @param {'polyimide'|'cellulose_acetate'} payload.membrane - Sieve material polymer matrix selection token.
 * @param {number} payload.P_feed_bar - Shell side compression feed inlet operating boundary (bar).
 * @param {number} payload.P_permeate_bar - Low pressure tube permeate vacuum discharge point (bar).
 * @param {number} payload.area_m2 - Active surface boundary layer total footprint area (m²).
 * @returns {Promise<Object>} Permeate fluxes, retentate residuals, final stage cut, and area tracking curves.
 */
export const simulateMembrane = async (payload) => {
  const response = await client.post('/api/hc-recovery/membrane', payload);
  return response.data;
};

/**
 * Runs all three separate chemical engines in parallel to assemble cross-technology attribute metrics.
 * * @async
 * @function compareTechnologies
 * @param {Object} payload
 * @param {FeedInputPayload} payload.feed - Primary base stream layout blueprint reference.
 * @param {number} payload.condensation_T_C - Chiller working target node setpoint.
 * @param {number} payload.condensation_P_bar - Chiller static running pressure metric.
 * @param {number} payload.adsorption_pressure_bar - Fixed-bed adsorber loop threshold.
 * @param {number} payload.adsorption_mass_kg - Solid media inventory loading parameter.
 * @param {number} payload.membrane_area_m2 - Polymer active surface matrix thickness skin footprint sizing.
 * @param {number} payload.membrane_P_feed_bar - Membrane feed layout structural head booster pressure.
 * @param {number} payload.membrane_P_permeate_bar - Membrane permeate line sweep discharge draw.
 * @returns {Promise<Object>} Normalized multi-variable score arrays optimized for radar chart ingestion.
 */
export const compareTechnologies = async (payload) => {
  const response = await client.post('/api/hc-recovery/compare', payload);
  return response.data;
};