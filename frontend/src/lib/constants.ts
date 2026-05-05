export type ColumnId = "inspiration" | "in_progress" | "pending_review" | "done";

export const COLUMNS: Record<ColumnId, { title: string }> = {
  inspiration: { title: "AI 灵感池" },
  in_progress: { title: "AI 创作中" },
  pending_review: { title: "待人工审核" },
  done: { title: "已完成归档" },
};

export const COLUMN_ORDER: ColumnId[] = [
  "inspiration",
  "in_progress",
  "pending_review",
  "done",
];

export const TASK_STATUS_MAP: Record<string, string> = {
  in_progress: "创作中",
  waiting_for_human: "待审核",
  done: "已完成",
  cancelled: "已取消",
  failed: "失败",
};

export const POLL_INTERVAL_BOARD = 3000;
export const POLL_INTERVAL_STATUS = 2000;
