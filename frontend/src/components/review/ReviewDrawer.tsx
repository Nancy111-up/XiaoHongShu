"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { useKanbanStore } from "@/store/kanban";
import { useSubmitFeedback } from "@/hooks/useSubmitFeedback";
import { useKanbanBoard } from "@/hooks/useKanbanBoard";
import type { TaskData } from "@/lib/types";

export function ReviewDrawer() {
  const isOpen = useKanbanStore((s) => s.isDrawerOpen);
  const taskId = useKanbanStore((s) => s.selectedTaskId);
  const closeDrawer = useKanbanStore((s) => s.closeDrawer);
  const addToast = useKanbanStore((s) => s.addToast);

  const { data: board } = useKanbanBoard();
  const feedback = useSubmitFeedback();

  const [tab, setTab] = useState<"polish" | "redo">("polish");
  const [editedContent, setEditedContent] = useState("");
  const [redoFeedback, setRedoFeedback] = useState("");

  const task = findTask(board, taskId);

  useEffect(() => {
    if (task) {
      setEditedContent(task.draft_copy || task.final_copy || "");
    }
  }, [task]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeDrawer();
    };
    if (isOpen) document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, closeDrawer]);

  if (!isOpen || !task) return null;

  const handleApprove = async () => {
    try {
      await feedback.mutateAsync({
        thread_id: task.thread_id,
        action: "approve",
        feedback: "",
        edited_content: editedContent,
      });
      addToast({ message: "已通过审核", type: "success" });
      closeDrawer();
    } catch {
      addToast({ message: "操作失败，请重试", type: "error" });
    }
  };

  const handleRevise = async () => {
    if (!redoFeedback.trim()) return;
    try {
      await feedback.mutateAsync({
        thread_id: task.thread_id,
        action: "revise",
        feedback: redoFeedback,
        edited_content: "",
      });
      addToast({ message: "已发送重做指令", type: "info" });
      closeDrawer();
    } catch {
      addToast({ message: "操作失败，请重试", type: "error" });
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={closeDrawer}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-stone-100">
          <div>
            <h2 className="text-lg font-semibold text-stone-800">
              审核文案
            </h2>
            <p className="text-xs text-stone-400 mt-0.5">{task.user_input}</p>
          </div>
          <button
            onClick={closeDrawer}
            className="w-8 h-8 flex items-center justify-center rounded-full text-stone-400 hover:bg-stone-100 hover:text-stone-600 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-stone-100">
          <button
            onClick={() => setTab("polish")}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              tab === "polish"
                ? "text-stone-800 border-b-2 border-stone-800"
                : "text-stone-400 hover:text-stone-600"
            }`}
          >
            微调通过
          </button>
          <button
            onClick={() => setTab("redo")}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              tab === "redo"
                ? "text-stone-800 border-b-2 border-stone-800"
                : "text-stone-400 hover:text-stone-600"
            }`}
          >
            重做
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {tab === "polish" ? (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-stone-500 mb-2">
                  编辑文案
                </label>
                <textarea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  rows={12}
                  className="w-full rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-800 leading-relaxed focus:outline-none focus:ring-2 focus:ring-stone-300 focus:border-stone-300 resize-none"
                />
              </div>

              {task.visual_guidance && (
                <div className="rounded-xl bg-stone-50 border border-stone-200 p-4">
                  <h4 className="text-xs font-semibold text-stone-500 mb-2">
                    视觉建议
                  </h4>
                  <p className="text-xs text-stone-600 leading-relaxed">
                    {task.visual_guidance.cover_suggestion}
                  </p>
                  {task.visual_guidance.shot_descriptions.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {task.visual_guidance.shot_descriptions.map((s, i) => (
                        <li key={i} className="text-xs text-stone-500">
                          {s}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              <Button
                className="w-full"
                onClick={handleApprove}
                disabled={feedback.isPending}
              >
                {feedback.isPending ? "提交中..." : "保存并通过"}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-stone-500 mb-2">
                  反馈意见
                </label>
                <textarea
                  value={redoFeedback}
                  onChange={(e) => setRedoFeedback(e.target.value)}
                  placeholder="描述需要调整的方向、风格、重点..."
                  rows={6}
                  className="w-full rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-800 placeholder:text-stone-300 focus:outline-none focus:ring-2 focus:ring-stone-300 focus:border-stone-300 resize-none"
                />
              </div>

              {task.draft_copy && (
                <div>
                  <label className="block text-xs font-medium text-stone-500 mb-2">
                    当前文案
                  </label>
                  <div className="rounded-xl bg-stone-50 border border-stone-200 p-4 text-xs text-stone-600 leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">
                    {task.draft_copy}
                  </div>
                </div>
              )}

              <Button
                className="w-full"
                variant="secondary"
                onClick={handleRevise}
                disabled={feedback.isPending || !redoFeedback.trim()}
              >
                {feedback.isPending ? "提交中..." : "发送重做指令"}
              </Button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function findTask(
  board: { in_progress: TaskData[]; pending_review: TaskData[]; done: TaskData[] } | undefined,
  taskId: string | null,
): TaskData | null {
  if (!board || !taskId) return null;
  return (
    board.pending_review.find((t) => t.thread_id === taskId) ||
    board.in_progress.find((t) => t.thread_id === taskId) ||
    board.done.find((t) => t.thread_id === taskId) ||
    null
  );
}
