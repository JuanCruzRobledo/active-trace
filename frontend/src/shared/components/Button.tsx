import type { ButtonHTMLAttributes, ReactNode } from "react";
import { LoadingSpinner } from "./LoadingSpinner";

type Variant = "primary" | "secondary" | "danger" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  is_loading?: boolean;
  children: ReactNode;
}

const variant_styles: Record<Variant, string> = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-700 focus:ring-brand-500 disabled:bg-brand-300",
  secondary:
    "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-brand-500 disabled:text-gray-400 disabled:bg-gray-100",
  danger:
    "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 disabled:bg-red-300",
  ghost:
    "text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:ring-brand-500 disabled:text-gray-400",
};

export function Button({
  variant = "primary",
  is_loading = false,
  disabled,
  children,
  className = "",
  ...rest
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed";

  return (
    <button
      className={`${base} ${variant_styles[variant]} ${className}`}
      disabled={disabled || is_loading}
      {...rest}
    >
      {is_loading && <LoadingSpinner size="h-4 w-4" />}
      {children}
    </button>
  );
}

