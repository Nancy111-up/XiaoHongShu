import type { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
  children: ReactNode;
}

const variantClasses: Record<string, string> = {
  primary:
    "bg-stone-800 text-stone-50 hover:bg-stone-700 active:bg-stone-900",
  secondary:
    "border border-stone-300 bg-white text-stone-700 hover:bg-stone-50 active:bg-stone-100",
  ghost: "text-stone-500 hover:text-stone-700 hover:bg-stone-100 active:bg-stone-200",
};

const sizeClasses: Record<string, string> = {
  sm: "px-3 py-1.5 text-xs rounded-lg",
  md: "px-4 py-2 text-sm rounded-xl",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stone-400 disabled:opacity-40 disabled:pointer-events-none cursor-pointer ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
