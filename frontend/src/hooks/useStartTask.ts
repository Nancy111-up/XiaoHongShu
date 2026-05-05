"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface StartResponse {
  thread_id: string;
}

export function useStartTask() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (topic: string) =>
      api.post<StartResponse>("/agent/start", { topic }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["board"] });
    },
  });
}
