import type { ReactNode } from "react";

interface BadgeProps {
  variant?: "default" | "success" | "warning" | "error";
  children: ReactNode;
}

const variantClasses: Record<string, string> = {
  default: "bg-stone-100 text-stone-600",
  success: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-700",
  error: "bg-red-50 text-red-700",
};

export function Badge({ variant = "default", children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${variantClasses[variant]}`}
    >
      {children}
    </span>
  );
}
