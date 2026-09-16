import { useMutation } from "@tanstack/react-query";
import { solveHX } from "../api/units";

/**
 * TanStack mutation wrapper for the heat exchanger solver.
 *
 * Usage:
 *   const { mutate, isPending, isError, error, data } = useSolveHX();
 *   mutate({ payload, includeLog: true }, { onSuccess: (data) => ... });
 */
export function useSolveHX() {
  return useMutation({
    mutationFn: ({ payload, includeLog = true }) =>
      solveHX(payload, includeLog),
  });
}
