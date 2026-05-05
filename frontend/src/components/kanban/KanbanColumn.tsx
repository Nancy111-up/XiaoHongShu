"use client";

import { useDroppable } from "@dnd-kit/core";
import type { ReactNode } from "react";

interface KanbanColumnProps {
  id: string;
  title: string;
  count: number;
  children: ReactNode;
}

export function KanbanColumn({ id, title, count, children }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={`flex flex-col min-w-0 rounded-2xl border transition-colors ${
        isOver
          ? "bg-sage/10 border-sage/40 ring-2 ring-sage/20"
          : "bg-stone-50/80 border-stone-100"
      }`}
    >
      <div className="flex items-center justify-between px-5 py-4 border-b border-stone-100">
        <h3 className="text-sm font-semibold text-stone-700 tracking-wide">
          {title}
        </h3>
        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-stone-200 text-xs font-bold text-stone-500 tabular-nums">
          {count}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2 min-h-[200px]">
        {children}
      </div>
    </div>
  );
}
