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
    <div className="flex items-center gap-2">
      {error !== null && <p role="alert" className="text-red-500 text-sm m-0">{error}</p>}
      <button 
        type="button" 
        onClick={handleLogout} 
        disabled={isPending}
        className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors disabled:opacity-50"
      >
        {isPending ? "ログアウト中..." : "ログアウト"}
      </button>
    </div>
  );
}
