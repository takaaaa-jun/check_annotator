"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAssignments, saveAssignments, type AssignmentGroup, type WorkerProgress } from "@/src/lib/api/management";
import { ApiError } from "@/src/lib/api/client";
import { LoadingState } from "@/src/components/async-state";

const button = "min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold disabled:opacity-40";
export function AssignmentPanel({ workers, onChanged }: { workers: WorkerProgress[]; onChanged: () => void }) {
  const router = useRouter();
  const [groups, setGroups] = useState<AssignmentGroup[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reload, setReload] = useState(0);
  const changed = groups.filter((group) => drafts[group.group_id] !== undefined && drafts[group.group_id] !== String(group.user_id ?? ""));
  const ownerName = (id: number | null) => id === null ? "未割り当て" : workers.find((worker) => worker.user_id === id)?.user_name ?? `ユーザー #${id}`;
  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true); setError("");
      try { const result = await getAssignments(); if (active) { setGroups(result.groups); setDrafts({}); } }
      catch (failure) { if (active) { if (failure instanceof ApiError && failure.status === 401) router.replace("/login"); else setError(failure instanceof Error ? failure.message : "割り当てを取得できませんでした。"); } }
      finally { if (active) setLoading(false); }
    }
    void load();
    return () => { active = false; };
  }, [reload, router]);
  async function save() {
    if (saving || !changed.length) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const result = await saveAssignments(changed.map((group) => ({ group_id: group.group_id, expected_user_id: group.user_id, user_id: drafts[group.group_id] ? Number(drafts[group.group_id]) : null })));
      setNotice(`${changed.length}グループの担当者を更新しました。タスク・進捗・コメントは保持しています。`);
      setGroups(result.groups); setDrafts({}); setConfirming(false); onChanged();
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) router.replace("/login");
      else setError(failure instanceof Error ? failure.message : "担当者を更新できませんでした。");
      setConfirming(false);
    } finally { setSaving(false); }
  }
  return <section aria-label="タスクの割り当て設定" className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-extrabold">タスクの割り当て設定</h2><p className="mt-1 text-sm text-slate-500">グループごとの担当者を選び、確認して保存します。解除してもタスク・進捗・コメントは残ります。</p></div><button className={button} disabled={loading || saving} onClick={() => { if (!changed.length || window.confirm("未保存の担当者の選択を破棄して、最新の内容を読み込みますか？")) { setNotice(""); setReload((value) => value + 1); } }}>最新に更新</button></div>
    {notice && <p role="status" className="rounded-lg bg-green-50 p-3 font-bold text-green-800">{notice}</p>}
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
    {loading ? <LoadingState compact message="割り当てを読み込み中..." /> : <>
      <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm font-bold">全{groups.length}グループ / 未割り当て {groups.filter((group) => group.user_id === null).length}グループ</p><button className={button} disabled={saving || !groups.some((group) => group.user_id !== null)} onClick={() => setDrafts(Object.fromEntries(groups.map((group) => [group.group_id, ""])))}>すべて未割り当てとして選択</button></div>
      <div className="max-h-[32rem] overflow-auto"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-50"><tr>{["グループ", "画像ID範囲", "タスク数", "現在の担当者", "新しい担当者"].map((label) => <th className="whitespace-nowrap p-3" key={label}>{label}</th>)}</tr></thead><tbody>{groups.map((group) => <tr key={group.group_id} className={drafts[group.group_id] !== undefined && drafts[group.group_id] !== String(group.user_id ?? "") ? "border-t bg-blue-50" : "border-t border-slate-100"}><td className="p-3 font-bold">{group.group_name}</td><td className="p-3">{group.image_id_min === null ? "—" : `${group.image_id_min}〜${group.image_id_max}`}</td><td className="p-3">{group.total_count}</td><td className="p-3">{ownerName(group.user_id)}</td><td className="p-3"><select aria-label={`${group.group_name}の担当者`} className="min-h-11 rounded-lg border border-slate-300 bg-white px-3" disabled={saving} value={drafts[group.group_id] ?? String(group.user_id ?? "")} onChange={(event) => setDrafts((previous) => ({ ...previous, [group.group_id]: event.target.value }))}><option value="">未割り当て</option>{group.user_id !== null && !workers.some((worker) => worker.user_id === group.user_id) && <option value={group.user_id} disabled>{ownerName(group.user_id)}（選択不可）</option>}{workers.map((worker) => <option value={worker.user_id} key={worker.user_id}>{worker.user_name}</option>)}</select></td></tr>)}</tbody></table></div>
      <div className="flex flex-wrap items-center justify-end gap-4"><span className="text-sm">変更予定：{changed.length}グループ</span><button className={`${button} bg-blue-600 text-white`} disabled={!changed.length || saving} onClick={() => setConfirming(true)}>選択内容を確認して保存</button></div>
    </>}
    {confirming && <div className="fixed inset-0 z-[100] grid place-items-center bg-slate-950/45 p-4"><section role="dialog" aria-modal="true" aria-labelledby="assignment-confirm-title" className="w-full max-w-xl space-y-4 rounded-2xl bg-white p-6"><h3 id="assignment-confirm-title" className="text-xl font-bold">担当者を変更しますか？</h3><p>以下の{changed.length}グループをまとめて更新します。タスク・進捗・コメントは削除しません。</p><ul className="max-h-72 space-y-2 overflow-y-auto">{changed.map((group) => <li key={group.group_id}><strong>{group.group_name}</strong>：{ownerName(group.user_id)} → {ownerName(drafts[group.group_id] ? Number(drafts[group.group_id]) : null)}</li>)}</ul><div className="flex justify-end gap-3"><button className={button} autoFocus disabled={saving} onClick={() => setConfirming(false)}>戻る</button><button className={`${button} bg-blue-600 text-white`} disabled={saving} onClick={save}>{saving ? "保存中..." : "この内容で担当者を更新"}</button></div></section></div>}
  </section>;
}
