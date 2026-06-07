interface ErrorMessageProps {
  message: string;
  /** Optional label for a retry / action button. */
  action_label?: string;
  /** Called when the action button is clicked. */
  on_action?: () => void;
}

export function ErrorMessage({
  message,
  action_label,
  on_action,
}: ErrorMessageProps) {
  return (
    <div
      className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800"
      role="alert"
    >
      <svg
        className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
          clipRule="evenodd"
        />
      </svg>
      <div className="flex-1">{message}</div>
      {action_label && on_action && (
        <button
          type="button"
          onClick={on_action}
          className="ml-auto whitespace-nowrap rounded bg-red-100 px-3 py-1.5 text-xs font-medium text-red-800 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1"
        >
          {action_label}
        </button>
      )}
    </div>
  );
}

