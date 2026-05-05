"use client";

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-stone-100 bg-white flex flex-col">
      <div className="px-5 py-5 border-b border-stone-100">
        <h1 className="text-base font-serif font-bold text-stone-800 tracking-tight">
          L&apos;Atelier Luna
        </h1>
        <p className="mt-0.5 text-[10px] text-stone-400 tracking-wide">
          品牌内容工作室
        </p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        <NavItem active icon={<BoardIcon />} label="内容看板" />
        <NavItem icon={<DraftIcon />} label="文案库" />
        <NavItem icon={<AssetIcon />} label="素材管理" />
        <NavItem icon={<CalendarIcon />} label="发布日历" />
      </nav>

      <div className="px-5 py-4 border-t border-stone-100">
        <div className="flex items-center gap-2 text-xs text-stone-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          引擎在线
        </div>
      </div>
    </aside>
  );
}

function NavItem({
  icon,
  label,
  active,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
        active
          ? "bg-stone-100 text-stone-800 font-medium"
          : "text-stone-500 hover:text-stone-700 hover:bg-stone-50"
      }`}
    >
      <span className="w-4 h-4 shrink-0 opacity-60">{icon}</span>
      {label}
    </button>
  );
}

function BoardIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1" y="1" width="6" height="6" rx="1" />
      <rect x="9" y="1" width="6" height="4" rx="1" />
      <rect x="1" y="9" width="6" height="4" rx="1" />
      <rect x="9" y="7" width="6" height="6" rx="1" />
    </svg>
  );
}

function DraftIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2 12V3h8l4 4v8a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1Z" />
      <path d="M10 3v4h4M5 8h4M5 11h6" />
    </svg>
  );
}

function AssetIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1.5" y="3" width="13" height="11" rx="1.5" />
      <path d="M1.5 6h13M4.5 1v3M11.5 1v3" />
    </svg>
  );
}
