"use client";

import { useEffect } from "react";

import { ErrorState } from "@/src/components/async-state";

type GlobalErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function GlobalError({
  error,
  reset,
}: GlobalErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="mb-5 text-2xl font-bold text-slate-950">
        エラーが発生しました
      </h1>
      <ErrorState
        message="画面を表示できませんでした。時間をおいて再度お試しください"
        onRetry={reset}
      />
    </main>
  );
}
