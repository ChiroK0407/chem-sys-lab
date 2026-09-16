/**
 * frontend/src/hooks/useHXTypes.js
 * * Caches equipment mechanical reference metadata boundaries globally.
 */

import { useQuery } from "@tanstack/react-query";
import { getHXTypes } from "../api/reference";

/**
 * TanStack query hook wrapping the heat exchanger metadata lookup.
 * Operates with an infinite stale duration since design rules are static constants.
 */
export function useHXTypes() {
  return useQuery({
    queryKey: ["hx-types"],
    queryFn: getHXTypes,
    staleTime: Infinity,
    cacheTime: Infinity,
    retry: 2,
    refetchOnWindowFocus: false,
  });
}