"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useFitness(days = 90) {
  return useQuery({
    queryKey: ["fitness", days],
    queryFn: () => api.fitness.get(days),
    staleTime: 5 * 60_000,
  });
}
