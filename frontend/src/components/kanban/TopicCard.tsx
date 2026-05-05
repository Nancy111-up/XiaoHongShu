"use client";

import { useDraggable } from "@dnd-kit/core";
import type { TopicCardData } from "@/lib/types";

interface TopicCardProps {
  topic: TopicCardData;
}

export function TopicCard({ topic }: TopicCardProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: topic.card_id,
    data: { title: topic.title },
  });

  const heatColor =
    topic.heat_index >= 85
      ? "bg-red-50 border-red-200"
      : topic.heat_index >= 70
        ? "bg-amber-50 border-amber-200"
        : "bg-stone-50 border-stone-200";

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`rounded-xl border px-4 py-3 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow touch-none ${
        isDragging ? "opacity-40" : ""
      } ${heatColor}`}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-stone-800 leading-snug">
          {topic.title}
        </h4>
        <span className="shrink-0 text-[10px] font-bold text-stone-400 tabular-nums">
          {topic.heat_index}°
        </span>
      </div>
      <p className="mt-1.5 text-xs text-stone-500 leading-relaxed">
        {topic.reason}
      </p>
      <p className="mt-2 text-[10px] text-stone-400">
        {topic.estimated_traffic}
      </p>
    </div>
  );
}
