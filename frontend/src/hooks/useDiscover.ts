"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { TopicCardData } from "@/lib/types";

export function useDiscover() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (keyword?: string) =>
      api.post<TopicCardData[]>("/agent/discover", { keyword }),
    onSuccess: (cards) => {
      qc.setQueryData<TopicCardData[]>(["inspiration"], cards);
    },
  });
}
