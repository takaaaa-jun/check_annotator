type FeedbackMessageProps = {
  message: string;
  kind?: "success" | "error";
};

export function FeedbackMessage({
  message,
  kind = "success",
}: FeedbackMessageProps) {
  return (
    <p
      role={kind === "error" ? "alert" : "status"}
      aria-live="polite"
      className={`rounded-lg border px-3 py-2 text-sm font-medium ${
        kind === "success"
          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
          : "border-red-200 bg-red-50 text-red-700"
      }`}
    >
      {message}
    </p>
  );
}
