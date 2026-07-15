"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useFitness(athleteId: string | undefined, days = 90) {
  return useQuery({
    queryKey: ["fitness", athleteId, days],
    queryFn: () => api.fitness.get(athleteId!, days),
    enabled: !!athleteId,
    staleTime: 5 * 60_000,
  });
}
