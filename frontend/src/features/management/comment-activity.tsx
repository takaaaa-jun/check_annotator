"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { EmptyState, ErrorState, LoadingState } from "@/src/components/async-state";
import { ApiError } from "@/src/lib/api/client";
import { getCommentActivity, type CommentActivityPage, type WorkerProgress } from "@/src/lib/api/management";
import { formatDateTime } from "@/src/lib/format/date-time";
import { TaskCommentsPanel } from "@/src/features/tasks/task-comments-panel";

const control = "min-h-11 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-40";

export function CommentActivity({ kind, workers = [], refreshKey = 0, onChanged }: {
  kind: "admin" | "replies"; workers?: WorkerProgress[]; refreshKey?: number; onChanged?: () => void;
}) {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [workerId, setWorkerId] = useState("");
  const [unanswered, setUnanswered] = useState(kind === "admin");
  const [data, setData] = useState<CommentActivityPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [reload, setReload] = useState(0);
  const unauthorized = useCallback(() => router.replace("/login"), [router]);

  useEffect(() => {
    if (openId !== null) return;
    let active = true;
    async function load() {
      setLoading(true); setError("");
      try {
        const result = await getCommentActivity(kind, page, workerId, unanswered);
        if (!active) return;
        // Replies may remove the last unanswered item on a later page.
        if (page > 1 && page > Math.max(1, result.pagination.total_pages)) { setPage(Math.max(1, result.pagination.total_pages)); return; }
        setData(result);
      } catch (failure) {
        if (!active) return;
        if (failure instanceof ApiError && failure.status === 401) { unauthorized(); return; }
        setError(failure instanceof Error ? failure.message : "コメントを読み込めませんでした。");
      } finally { if (active) setLoading(false); }
    }
    void load();
    return () => { active = false; };
  }, [kind, page, workerId, unanswered, refreshKey, reload, unauthorized, openId]);

  useEffect(() => {
    if (openId !== null) return;
    const refresh = () => { if (document.visibilityState === "visible") setReload((value) => value + 1); };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    const timer = window.setInterval(refresh, 30000);
    return () => { window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); window.clearInterval(timer); };
  }, [openId]);

  return <section className="space-y-4" aria-label={kind === "admin" ? "作業者コメント一覧" : "管理者からの返信一覧"}>
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div><h2 className="text-xl font-extrabold">{kind === "admin" ? "作業者からのコメント" : "管理者からの返信"}</h2><p className="mt-1 text-sm text-slate-500">{kind === "admin" ? "返信するコメントを選んで、内容を確認してから送信してください。" : "現在担当しているタスクへの管理者の返信を、新しい順に表示します。"}</p></div>
      <button className={control} disabled={loading || openId !== null} onClick={() => setReload((value) => value + 1)}>最新の内容を確認</button>
    </div>
    {kind === "admin" && <div className="flex flex-wrap items-center gap-4 rounded-xl bg-slate-50 p-4">
      <label className="flex items-center gap-2 text-sm font-bold">作業者<select aria-label="コメントの作業者" className={control} value={workerId} disabled={openId !== null} onChange={(event) => { setWorkerId(event.target.value); setPage(1); }}><option value="">すべての作業者</option>{workers.map((worker) => <option value={worker.user_id} key={worker.user_id}>{worker.user_name}</option>)}</select></label>
      <label className="flex min-h-11 items-center gap-2 text-sm font-bold"><input type="checkbox" checked={unanswered} disabled={openId !== null} onChange={(event) => { setUnanswered(event.target.checked); setPage(1); }} />管理者が未返信のコメントのみ</label>
    </div>}
    {notice && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 font-semibold text-emerald-800">{notice}</p>}
    {error ? <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} /> : loading ? <LoadingState message="コメントを読み込み中..." /> : !data?.comments.length ? <EmptyState message={kind === "admin" ? "該当するコメントはありません" : "管理者からの返信はまだありません"} /> : <>
      <p className="text-sm font-semibold text-slate-600">全{data.pagination.total}件</p>
      <ul className="space-y-4">{data.comments.map((comment) => <li key={comment.comment_id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="space-y-3 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-extrabold text-slate-900">画像 {comment.image_id} <span className="ml-2 text-sm font-medium text-slate-500">{comment.group_name} / 担当 {comment.worker_name}</span></p>{kind === "admin" && <span className={`rounded-full px-3 py-1 text-xs font-bold ${comment.has_admin_reply ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>{comment.has_admin_reply ? "管理者返信あり" : "未返信"}</span>}</div>
          <p className="text-sm text-slate-500"><span className="font-bold text-slate-800">{comment.user_name}</span>{comment.author_role === "admin" && <span className="ml-2 rounded bg-blue-50 px-2 py-0.5 font-bold text-blue-800">管理者</span>} · {formatDateTime(comment.created_at)} · コメント #{comment.comment_id}</p>
          {comment.parent_id !== null && <blockquote className="border-l-4 border-slate-200 bg-slate-50 p-3 text-sm text-slate-600"><p className="mb-1 font-bold">返信元 #{comment.parent_id}</p><p className="whitespace-pre-wrap break-words">{comment.parent_content ?? "元のコメントは表示できません。"}</p></blockquote>}
          <p className="whitespace-pre-wrap break-words leading-7 text-slate-800">{comment.content}</p>
          <div className="flex flex-wrap gap-3">
            <button className={control} aria-expanded={openId === comment.comment_id} onClick={() => { setOpenId((current) => current === comment.comment_id ? null : comment.comment_id); setNotice(""); }}>{openId === comment.comment_id ? "返信欄を閉じる" : "このコメントに返信"}</button>
            <Link className={`${control} inline-flex items-center text-blue-800`} href={`/mypage/${comment.worker_id}/groups/${comment.group_id}`}>担当タスクを開く</Link>
          </div>
        </div>
        {openId === comment.comment_id && <div className="border-t bg-slate-50 p-4"><TaskCommentsPanel key={comment.comment_id} taskId={comment.task_id} imageId={comment.image_id} initialReplyTarget={comment} replyOnly focusKey={1} onUnauthorized={unauthorized} onCompleted={() => { setNotice(`画像${comment.image_id}のコメント #${comment.comment_id} に返信を送信しました。`); setOpenId(null); setReload((value) => value + 1); onChanged?.(); }} /></div>}
      </li>)}</ul>
      <nav aria-label="コメント一覧のページ移動" className="flex items-center justify-center gap-4"><button className={control} disabled={page <= 1 || openId !== null} onClick={() => setPage((value) => value - 1)}>前へ</button><span>{page} / {Math.max(1, data.pagination.total_pages)}ページ</span><button className={control} disabled={page >= data.pagination.total_pages || openId !== null} onClick={() => setPage((value) => value + 1)}>次へ</button></nav>
    </>}
    <p className="text-xs text-slate-500">返信欄を開いていないときは、画面への復帰時と30秒ごとに更新します。</p>
  </section>;
}
