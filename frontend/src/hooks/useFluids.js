import { useQuery } from "@tanstack/react-query";
import { getFluids, getFluidDetail } from "../api/reference";

/**
 * Fetches and caches the full list of available fluids.
 * staleTime: Infinity — fluid list never changes at runtime.
 */
export function useFluids() {
  return useQuery({
    queryKey: ["fluids"],
    queryFn: getFluids,
    staleTime: Infinity,
  });
}

/**
 * Fetches properties for a single fluid at an optional temperature.
 * Only runs when fluidId is non-null.
 *
 * @param {string|null} fluidId
 * @param {number|null} temperatureC
 */
export function useFluidDetail(fluidId, temperatureC) {
  return useQuery({
    queryKey: ["fluid", fluidId, temperatureC],
    queryFn: () => getFluidDetail(fluidId, temperatureC),
    enabled: !!fluidId,
    staleTime: 60000,
  });
}
