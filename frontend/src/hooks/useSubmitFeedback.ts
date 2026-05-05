"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FeedbackAction } from "@/lib/types";

interface FeedbackPayload {
  thread_id: string;
  action: FeedbackAction;
  feedback: string;
  edited_content: string;
}

export function useSubmitFeedback() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: FeedbackPayload) =>
      api.post<{ thread_id: string; action: string }>(
        "/agent/feedback",
        payload,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["board"] });
    },
  });
}
