"use client";

import { Badge } from "@/components/ui/Badge";
import { TASK_STATUS_MAP } from "@/lib/constants";
import type { TaskData } from "@/lib/types";

interface TaskCardProps {
  task: TaskData;
  onClick?: () => void;
  isSelected?: boolean;
}

export function TaskCard({ task, onClick, isSelected }: TaskCardProps) {
  const statusLabel = TASK_STATUS_MAP[task.status] || task.status;
  const isPending = task.column === "pending_review";
  const isDone = task.column === "done";
  const isFailed = task.status === "failed";

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border px-4 py-3 transition-all hover:shadow-md ${
        isSelected
          ? "border-stone-400 ring-2 ring-stone-200 bg-white"
          : isFailed
            ? "border-red-200 bg-red-50/50 hover:border-red-300"
            : "border-stone-200 bg-white hover:border-stone-300"
      }`}
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-stone-800 line-clamp-1">
          {task.user_input}
        </h4>
        <Badge
          variant={
            isFailed ? "error" : isDone ? "success" : isPending ? "warning" : "default"
          }
        >
          {statusLabel}
        </Badge>
      </div>

      {isFailed ? (
        task.error_logs && task.error_logs.length > 0 && (
          <p className="mt-2 text-xs text-red-600 line-clamp-3">
            {task.error_logs[0]}
          </p>
        )
      ) : isDone ? (
        task.final_copy ? (
          <p className="mt-2 text-xs text-stone-600 line-clamp-3 whitespace-pre-wrap">
            {task.final_copy}
          </p>
        ) : task.draft_copy ? (
          <p className="mt-2 text-xs text-stone-500 line-clamp-3 whitespace-pre-wrap">
            {task.draft_copy}
          </p>
        ) : null
      ) : (
        task.draft_copy && (
          <p className="mt-2 text-xs text-stone-500 line-clamp-3 whitespace-pre-wrap">
            {task.draft_copy}
          </p>
        )
      )}

      <div className="mt-2 flex items-center gap-2 text-[10px] text-stone-400">
        <span>修订 {task.revision_count} 次</span>
        <span>·</span>
        <span>{new Date(task.created_at).toLocaleDateString("zh-CN")}</span>
      </div>
    </button>
  );
}

export function TaskCardSkeleton() {
  return (
    <div className="rounded-xl border border-stone-200 bg-white px-4 py-3 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="h-4 w-28 bg-stone-200 rounded" />
        <div className="h-5 w-12 bg-stone-200 rounded-full" />
      </div>
      <div className="mt-2 space-y-1.5">
        <div className="h-3 w-full bg-stone-100 rounded" />
        <div className="h-3 w-3/4 bg-stone-100 rounded" />
      </div>
      <div className="mt-2 h-3 w-20 bg-stone-100 rounded" />
    </div>
  );
}
