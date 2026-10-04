"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { logout } from "@/src/lib/api/auth";

export function LogoutButton() {
  const router = useRouter();
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogout() {
    setIsPending(true);
    setError(null);
    try {
      await logout();
      router.replace("/login");
      router.refresh();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "ログアウトに失敗しました");
      setIsPending(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      {error !== null && (
        <p
          role="alert"
          className="m-0 hidden text-sm font-medium text-red-600 sm:block"
        >
          {error}
        </p>
      )}
      <button
        type="button"
        onClick={handleLogout}
        disabled={isPending}
        className="min-h-10 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 disabled:cursor-wait disabled:opacity-50"
      >
        {isPending ? "ログアウト中..." : "ログアウト"}
      </button>
    </div>
  );
}
