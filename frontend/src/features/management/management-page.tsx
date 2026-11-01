"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/src/lib/api/auth";
import { ApiError } from "@/src/lib/api/client";
import { getAdminOverview, type AdminOverview } from "@/src/lib/api/management";
import type { CurrentUser } from "@/src/lib/api/types";
import { LoadingState, ErrorState } from "@/src/components/async-state";
import { CommentActivity } from "./comment-activity";

export function ManagementPage({ admin = false }: { admin?: boolean }) {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    async function load() {
      setError("");
      try {
        const current = await getCurrentUser();
        if (!active) return;
        if (admin && current.role_name !== "admin") { setForbidden(true); setUser(current); return; }
        setUser(current);
        if (admin) { const result = await getAdminOverview(); if (active) setOverview(result); }
      } catch (failure) {
        if (!active) return;
        if (failure instanceof ApiError && failure.status === 401) { router.replace("/login"); return; }
        setError(failure instanceof Error ? failure.message : "情報を読み込めませんでした。");
      }
    }
    void load();
    return () => { active = false; };
  }, [admin, reload, router]);
  if (forbidden) return <main className="mx-auto max-w-3xl p-8"><ErrorState message="管理者権限が必要です。" /><Link className="mt-4 inline-block text-blue-800 underline" href={`/mypage/${user?.user_id}/groups`}>担当グループに戻る</Link></main>;
  if (error && (!user || (admin && !overview))) return <main className="mx-auto max-w-3xl p-8"><ErrorState message={error} onRetry={() => setReload((value) => value + 1)} /></main>;
  if (!user || (admin && !overview)) return <LoadingState message="情報を読み込み中..." />;
  return <main className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
    <header className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm font-bold text-blue-700">{admin ? "管理者" : "作業者"} · {user.user_name}</p><h1 className="mt-2 text-3xl font-extrabold text-slate-950">{admin ? "作業進捗とコメント管理" : "コメントへの返信"}</h1><p className="mt-2 text-slate-500">{admin ? "担当者ごとの状況を確認し、作業者の質問に返信できます。" : "管理者からの返信を確認して、必要に応じて回答できます。"}</p></div>{admin && <button className="min-h-11 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-bold" onClick={() => setReload((value) => value + 1)}>進捗を更新</button>}</header>
    {error && <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} />}
    {admin && overview && <>
      <section className="grid gap-4 sm:grid-cols-4" aria-label="全体の進捗">{[["作業者", `${overview.workers.length}人`], ["担当タスク", `${overview.total_tasks}件`], ["完了", `${overview.completed_tasks}件`], ["未返信コメント", `${overview.pending_comments}件`]].map(([label, value]) => <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" key={label}><p className="text-sm font-bold text-slate-500">{label}</p><p className="mt-2 text-3xl font-extrabold text-slate-950">{value}</p></div>)}</section>
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-label="作業者別の進捗"><h2 className="border-b px-5 py-4 text-xl font-extrabold">作業者別の進捗</h2><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-600"><tr>{["作業者", "グループ", "進捗", "状態別の件数", "未返信", "確認"].map((label) => <th key={label} className="whitespace-nowrap px-5 py-3">{label}</th>)}</tr></thead><tbody>{overview.workers.map((worker) => { const percent = worker.total_count ? Math.round(worker.completed_count / worker.total_count * 100) : 0; return <tr key={worker.user_id} className="border-t border-slate-100"><td className="px-5 py-4 font-bold text-slate-950">{worker.user_name}</td><td className="px-5 py-4">{worker.group_count}</td><td className="min-w-40 px-5 py-4"><p>{worker.completed_count} / {worker.total_count}件 · {percent}%</p><progress aria-label={`${worker.user_name}の進捗率`} className="mt-2 h-2 w-full accent-blue-600" max="100" value={percent} /></td><td className="px-5 py-4"><div className="flex flex-wrap gap-2">{worker.state_counts.map((state) => <span key={state.state_id} className="whitespace-nowrap rounded bg-slate-100 px-2 py-1">{state.state_name} {state.count}</span>)}</div></td><td className="px-5 py-4 font-bold">{worker.pending_comments}</td><td className="whitespace-nowrap px-5 py-4"><Link className="font-bold text-blue-800 underline" href={`/mypage/${worker.user_id}/groups`}>担当グループ</Link></td></tr>; })}</tbody></table></div>{overview.workers.length === 0 && <p className="p-5 text-slate-500">作業者はまだ登録されていません。</p>}</section>
    </>}
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><CommentActivity kind={admin ? "admin" : "replies"} workers={overview?.workers} refreshKey={reload} onChanged={() => setReload((value) => value + 1)} /></div>
    {!admin && <Link href={`/mypage/${user.user_id}/groups`} className="inline-block font-bold text-blue-800 underline">担当グループに戻る</Link>}
  </main>;
}
