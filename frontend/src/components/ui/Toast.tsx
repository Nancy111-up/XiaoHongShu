"use client";

import { useEffect } from "react";
import { useKanbanStore } from "@/store/kanban";

const iconMap: Record<string, string> = {
  success: "✓",
  error: "✗",
  info: "ℹ",
};

export function ToastContainer() {
  const toasts = useKanbanStore((s) => s.toasts);
  const removeToast = useKanbanStore((s) => s.removeToast);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDone={removeToast} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onDone,
}: {
  toast: { id: string; message: string; type: string };
  onDone: (id: string) => void;
}) {
  useEffect(() => {
    const t = setTimeout(() => onDone(toast.id), 4000);
    return () => clearTimeout(t);
  }, [toast.id, onDone]);

  const bg =
    toast.type === "success"
      ? "bg-emerald-900 text-emerald-50"
      : toast.type === "error"
        ? "bg-red-900 text-red-50"
        : "bg-stone-800 text-stone-50";

  return (
    <div
      className={`pointer-events-auto flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm animate-slide-up ${bg}`}
    >
      <span className="text-base">{iconMap[toast.type] || ""}</span>
      <span>{toast.message}</span>
    </div>
  );
}
