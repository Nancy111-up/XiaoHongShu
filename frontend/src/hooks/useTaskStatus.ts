"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { POLL_INTERVAL_STATUS } from "@/lib/constants";
import type { AgentStatus } from "@/lib/types";

export function useTaskStatus(threadId: string | null) {
  return useQuery({
    queryKey: ["task-status", threadId],
    queryFn: () => api.get<AgentStatus>(`/agent/status/${threadId}`),
    enabled: !!threadId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (
        data?.status === "waiting_for_human" ||
        data?.status === "done"
      ) {
        return false;
      }
      return POLL_INTERVAL_STATUS;
    },
  });
}
