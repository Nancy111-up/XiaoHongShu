"use client";

import { useState, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  useSensor,
  useSensors,
  PointerSensor,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "./KanbanColumn";
import { TopicCard } from "./TopicCard";
import { TaskCard, TaskCardSkeleton } from "./TaskCard";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { COLUMN_ORDER, COLUMNS } from "@/lib/constants";
import { useKanbanStore } from "@/store/kanban";
import { useKanbanBoard } from "@/hooks/useKanbanBoard";
import { useDiscover } from "@/hooks/useDiscover";
import { useStartTask } from "@/hooks/useStartTask";
import type { TopicCardData } from "@/lib/types";

export function KanbanBoard() {
  const { data, error } = useKanbanBoard();
  const discover = useDiscover();
  const startTask = useStartTask();
  const openDrawer = useKanbanStore((s) => s.openDrawer);
  const selectedTaskId = useKanbanStore((s) => s.selectedTaskId);
  const addToast = useKanbanStore((s) => s.addToast);

  const [newTopic, setNewTopic] = useState("");
  const [inspirationCards, setInspirationCards] = useState<TopicCardData[]>([]);
  const [activeDrag, setActiveDrag] = useState<TopicCardData | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const board = data ?? {
    inspiration: [],
    in_progress: [],
    pending_review: [],
    done: [],
  };

  const allInspiration = [...inspirationCards, ...board.inspiration];

  const handleDiscover = async () => {
    try {
      const result = await discover.mutateAsync(undefined);
      if (result) {
        // Replace entirely — each discover call is a fresh trend snapshot
        const seen = new Set<string>();
        const deduped = [...inspirationCards, ...result].filter(
          (c) => !seen.has(c.card_id) && seen.add(c.card_id),
        );
        setInspirationCards(deduped);
      }
    } catch {
      addToast({ message: "趋势搜索失败，请重试", type: "error" });
    }
  };

  const handleStartTask = async (topic: string) => {
    if (!topic.trim()) return;
    try {
      await startTask.mutateAsync(topic.trim());
      setNewTopic("");
      addToast({ message: `已开始: ${topic}`, type: "success" });
    } catch {
      addToast({ message: "创建任务失败", type: "error" });
    }
  };

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const card = allInspiration.find(
        (c) => c.card_id === event.active.id,
      );
      if (card) setActiveDrag(card);
    },
    [allInspiration],
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveDrag(null);
      const { active, over } = event;
      if (!over) return;

      const topic = active.data.current?.title as string;
      if (topic && over.id === "in_progress") {
        handleStartTask(topic);
        setInspirationCards((prev) =>
          prev.filter((c) => c.card_id !== active.id),
        );
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [handleStartTask],
  );

  const columnData: Record<string, unknown[]> = {
    inspiration: allInspiration,
    in_progress: board.in_progress,
    pending_review: board.pending_review,
    done: board.done,
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-sm text-stone-500">
            无法连接后端服务
          </p>
          <p className="text-xs text-stone-400 mt-1">
            请确保 backend 已启动于 localhost:8000
          </p>
        </div>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 h-full">
        {COLUMN_ORDER.map((colId) => {
          const col = COLUMNS[colId];
          const items = columnData[colId] || [];

          return (
            <KanbanColumn key={colId} id={colId} title={col.title} count={items.length}>
              {colId === "inspiration" && (
                <InspirationContent
                  cards={allInspiration}
                  onDiscover={handleDiscover}
                  discovering={discover.isPending}
                />
              )}
              {colId === "in_progress" && (
                <InProgressContent
                  newTopic={newTopic}
                  onTopicChange={setNewTopic}
                  onStart={handleStartTask}
                  starting={startTask.isPending}
                  tasks={board.in_progress}
                  selectedTaskId={selectedTaskId}
                />
              )}
              {colId === "pending_review" && (
                <PendingReviewContent
                  tasks={board.pending_review}
                  selectedTaskId={selectedTaskId}
                  onOpenDrawer={openDrawer}
                />
              )}
              {colId === "done" && (
                <DoneContent
                  tasks={board.done}
                  onCopy={(text) => {
                    navigator.clipboard.writeText(text);
                    addToast({ message: "已复制到剪贴板", type: "success" });
                  }}
                />
              )}
            </KanbanColumn>
          );
        })}
      </div>

      <DragOverlay>
        {activeDrag ? (
          <div className="opacity-80 scale-105">
            <TopicCard topic={activeDrag} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

function InspirationContent({
  cards,
  onDiscover,
  discovering,
}: {
  cards: TopicCardData[];
  onDiscover: () => void;
  discovering: boolean;
}) {
  return (
    <div className="space-y-2">
      <Button
        variant="secondary"
        size="sm"
        className="w-full"
        onClick={onDiscover}
        disabled={discovering}
      >
        {discovering ? "搜索中..." : "发现热点"}
      </Button>

      {cards.length === 0 && !discovering && (
        <p className="text-xs text-stone-400 text-center py-6">
          点击"发现热点"探索小红书趋势
        </p>
      )}

      {cards.map((card) => (
        <TopicCard key={card.card_id} topic={card} />
      ))}
    </div>
  );
}

function InProgressContent({
  newTopic,
  onTopicChange,
  onStart,
  starting,
  tasks,
  selectedTaskId,
}: {
  newTopic: string;
  onTopicChange: (v: string) => void;
  onStart: (topic: string) => void;
  starting: boolean;
  tasks: { thread_id: string }[];
  selectedTaskId: string | null;
}) {
  return (
    <div className="space-y-2">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onStart(newTopic);
        }}
        className="flex gap-2"
      >
        <Input
          placeholder="输入创作主题..."
          value={newTopic}
          onChange={(e) => onTopicChange(e.target.value)}
        />
        <Button type="submit" size="sm" disabled={starting}>
          {starting ? "..." : "开始"}
        </Button>
      </form>

      {tasks.length === 0 && !starting && (
        <p className="text-xs text-stone-400 text-center py-6">
          输入主题或拖拽灵感卡片开始创作
        </p>
      )}

      {starting && <TaskCardSkeleton />}

      {tasks.map((task) => (
        <TaskCard
          key={task.thread_id}
          task={task as any}
          isSelected={selectedTaskId === task.thread_id}
        />
      ))}
    </div>
  );
}

function PendingReviewContent({
  tasks,
  selectedTaskId,
  onOpenDrawer,
}: {
  tasks: { thread_id: string }[];
  selectedTaskId: string | null;
  onOpenDrawer: (id: string) => void;
}) {
  return (
    <div className="space-y-2">
      {tasks.length === 0 && (
        <p className="text-xs text-stone-400 text-center py-6">
          AI 完成任务后将出现在这里
        </p>
      )}
      {tasks.map((task) => (
        <TaskCard
          key={task.thread_id}
          task={task as any}
          onClick={() => onOpenDrawer(task.thread_id)}
          isSelected={selectedTaskId === task.thread_id}
        />
      ))}
    </div>
  );
}

function DoneContent({
  tasks,
  onCopy,
}: {
  tasks: { thread_id: string; final_copy: string | null; draft_copy: string | null }[];
  onCopy: (text: string) => void;
}) {
  return (
    <div className="space-y-2">
      {tasks.length === 0 && (
        <p className="text-xs text-stone-400 text-center py-6">
          审核通过的文案会归档于此
        </p>
      )}
      {tasks.map((task) => (
        <div key={task.thread_id} className="group">
          <TaskCard task={task as any} />
          {(task.final_copy || task.draft_copy) && (
            <button
              onClick={() => onCopy(task.final_copy || task.draft_copy || "")}
              className="mt-1 w-full text-center text-[10px] text-stone-400 hover:text-stone-600 opacity-0 group-hover:opacity-100 transition-opacity py-1 rounded-lg cursor-pointer"
            >
              复制文案
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
