"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { POLL_INTERVAL_BOARD } from "@/lib/constants";
import type { KanbanBoard } from "@/lib/types";

export function useKanbanBoard() {
  return useQuery<KanbanBoard>({
    queryKey: ["board"],
    queryFn: () => api.get<KanbanBoard>("/board"),
    refetchInterval: POLL_INTERVAL_BOARD,
  });
}
