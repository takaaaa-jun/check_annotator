"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getCurrentUser } from "@/src/lib/api/auth";
import type { CurrentUser } from "@/src/lib/api/types";

import { LogoutButton } from "./logout-button";

export function GlobalHeader() {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);
  const protectedPage =
    pathname !== "/login" && pathname !== "/";

  useEffect(() => {
    if (!protectedPage) {
      return;
    }

    let active = true;

    getCurrentUser()
      .then((user) => {
        if (active) {
          setCurrentUser(user);
        }
      })
      .catch(() => {
        if (active) {
          setCurrentUser(null);
        }
      });

    return () => {
      active = false;
    };
  }, [protectedPage]);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 shadow-[0_1px_12px_rgba(15,23,42,0.05)] backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <div
            aria-hidden="true"
            className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-sm font-bold text-white shadow-sm"
          >
            CA
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold tracking-tight text-slate-900 sm:text-base">
              アノテーション作業進捗管理
            </p>
            <p className="hidden text-xs text-slate-500 sm:block">
              Check Annotator
            </p>
          </div>
        </div>

        {protectedPage && (
          <div className="flex items-center gap-3">
            {currentUser !== null && (
              <p className="hidden text-sm text-slate-600 md:block">
                ログイン中: <span className="font-semibold text-slate-900">{currentUser.user_name}</span>
              </p>
            )}
            <LogoutButton />
          </div>
        )}
      </div>
    </header>
  );
}
