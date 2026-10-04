type LoadingStateProps = {
  message?: string;
  compact?: boolean;
};

export function LoadingState({
  message = "読み込み中...",
  compact = false,
}: LoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-center justify-center gap-3 text-slate-600 ${
        compact ? "py-6 text-sm" : "min-h-48 p-8"
      }`}
    >
      <span
        aria-hidden="true"
        className="size-5 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600"
      />
      <span>{message}</span>
    </div>
  );
}

type ErrorStateProps = {
  message: string;
  onRetry?: () => void;
  compact?: boolean;
};

export function ErrorState({
  message,
  onRetry,
  compact = false,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`rounded-xl border border-red-200 bg-red-50 ${
        compact ? "p-4" : "p-6"
      }`}
    >
      <p className="font-medium text-red-700">
        {message}
      </p>
      {onRetry !== undefined && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          再試行
        </button>
      )}
    </div>
  );
}

type EmptyStateProps = {
  message: string;
  compact?: boolean;
};

export function EmptyState({
  message,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      className={`rounded-xl border border-dashed border-slate-300 bg-white text-center text-slate-600 ${
        compact ? "p-6 text-sm" : "p-8"
      }`}
    >
      <p>{message}</p>
    </div>
  );
}
