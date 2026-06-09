import type { ReactNode } from "react";

interface FormFieldProps {
  label: string;
  html_for: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}

export function FormField({
  label,
  html_for,
  error,
  hint,
  children,
}: FormFieldProps) {
  return (
    <div>
      <label
        htmlFor={html_for}
        className="mb-1 block text-sm font-medium text-gray-700"
      >
        {label}
      </label>
      {children}
      {hint && !error && (
        <p className="mt-1 text-xs text-gray-500">{hint}</p>
      )}
      {error && (
        <p className="mt-1 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

