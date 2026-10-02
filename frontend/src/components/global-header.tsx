"use client";

import { usePathname } from "next/navigation";
import { LogoutButton } from "./logout-button";

export function GlobalHeader() {
  const pathname = usePathname();

  return (
    <header className="p-4 border-b flex justify-between items-center bg-white shadow-sm">
      <div className="font-bold text-lg">アノテーション作業進捗管理</div>
      {pathname !== "/login" && pathname !== "/" && <LogoutButton />}
    </header>
  );
}
