import { forwardRef, type InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  has_error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ has_error = false, className = "", ...rest }, ref) => {
    const base =
      "block w-full rounded-md border px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-500";
    const border_color = has_error
      ? "border-red-300 focus:border-red-400 focus:ring-red-500"
      : "border-gray-300 focus:border-brand-500 focus:ring-brand-500";

    return (
      <input
        ref={ref}
        className={`${base} ${border_color} ${className}`}
        {...rest}
      />
    );
  },
);

Input.displayName = "Input";

