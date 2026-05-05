"use client";

import { Badge } from "@/components/ui/Badge";

interface HeaderProps {
  title: string;
  agentStatus?: "idle" | "running" | "waiting";
}

const statusMap: Record<string, { label: string; variant: "default" | "success" | "warning" }> = {
  idle: { label: "就绪", variant: "default" },
  running: { label: "创作中", variant: "warning" },
  waiting: { label: "待审核", variant: "success" },
};

export function Header({ title, agentStatus = "idle" }: HeaderProps) {
  const s = statusMap[agentStatus];

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-stone-100 bg-white">
      <div>
        <h2 className="text-lg font-semibold text-stone-800">{title}</h2>
        <p className="text-xs text-stone-400 mt-0.5">
          小红书自主品牌运营专家
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Badge variant={s.variant}>{s.label}</Badge>
      </div>
    </header>
  );
}
