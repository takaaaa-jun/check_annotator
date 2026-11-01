"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAssignmentRanges, saveAssignmentRanges, type RangeAssignments, type WorkerProgress } from "@/src/lib/api/management";
import { ApiError } from "@/src/lib/api/client";
import { LoadingState } from "@/src/components/async-state";
type Draft = { start: string; end: string; owner: string };
const button = "min-h-11 rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold disabled:opacity-40";
const input = "min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2";
const toDrafts = (data: RangeAssignments): Draft[] => data.ranges.map(r => ({ start: String(r.start_image_id), end: String(r.end_image_id), owner: String(r.user_id) }));
export function AssignmentPanel({ workers, onChanged }: { workers: WorkerProgress[]; onChanged: () => void }) {
  const router = useRouter();
  const [data, setData] = useState<RangeAssignments | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reload, setReload] = useState(0);
  const dirty = data !== null && JSON.stringify(drafts) !== JSON.stringify(toDrafts(data));
  const ownerName = (id: string) => workers.find(w => String(w.user_id) === id)?.user_name ?? `ユーザー #${id}`;
  useEffect(() => {
    let active = true;

    getAssignmentRanges().then(result => { if (active) { setData(result); setDrafts(toDrafts(result)); } })
      .catch(failure => { if (active) { if (failure instanceof ApiError && failure.status === 401) router.replace("/login"); else setError(failure instanceof Error ? failure.message : "割り当てを取得できませんでした。"); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [reload, router]);
  function validate() {
    let end = 0;
    for (const row of [...drafts].sort((a, b) => Number(a.start) - Number(b.start))) {
      if (![row.start, row.end].every(value => /^\d+$/.test(value) && Number.isSafeInteger(Number(value)) && Number(value) > 0 && Number(value) <= 4294967295) || !workers.some(w => String(w.user_id) === row.owner)) return "開始画像ID・終了画像IDと担当者を正しく入力してください。";
      if (Number(row.start) > Number(row.end)) return "開始画像IDは終了画像ID以下にしてください。";
      if (Number(row.start) <= end) return "画像IDの範囲が重複しています。";
      end = Number(row.end);
    }
    return "";
  }
  async function save() {
    if (saving || !data) return;
    const invalid = validate();
    if (invalid) { setError(invalid); setConfirming(false); return; }
    setSaving(true); setError(""); setNotice("");
    try {
      const result = await saveAssignmentRanges(data.revision, drafts.map(row => ({ start_image_id: Number(row.start), end_image_id: Number(row.end), user_id: Number(row.owner) })));
      setData(result); setDrafts(toDrafts(result)); setConfirming(false);
      setNotice("画像IDの範囲と担当者を更新しました。タスク・進捗・コメントは保持しています。"); onChanged();
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) router.replace("/login");
      else setError(failure instanceof Error ? failure.message : "割り当てを更新できませんでした。");
      setConfirming(false);
    } finally { setSaving(false); }
  }
  function edit(index: number, key: keyof Draft, value: string) { setNotice(""); setDrafts(rows => rows.map((row, i) => i === index ? { ...row, [key]: value } : row)); }
  return <section aria-label="タスクの割り当て設定" className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-extrabold">タスクの割り当て設定</h2><p className="mt-1 text-sm text-slate-600">開始・終了画像IDと担当者を自由に指定できます。1,000件単位の区切りは不要です。</p></div><button className={button} disabled={loading || saving} onClick={() => { if (!dirty || window.confirm("未保存の入力を破棄して、最新の内容を読み込みますか？")) { setNotice(""); setError(""); setLoading(true); setReload(v => v + 1); } }}>最新に更新</button></div>
    {notice && <p role="status" className="rounded-lg bg-green-50 p-3 font-bold text-green-800">{notice}</p>}
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
    {loading ? <LoadingState compact message="割り当てを読み込み中..." /> : data && <>
      <p className="text-sm">対象タスク：{data.total_tasks.toLocaleString()}件 / 画像ID：{data.image_id_min === null ? "なし" : `${data.image_id_min}〜${data.image_id_max}`}</p>
      <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-950">保存すると、現在の割り当て全体を下の一覧で置き換えます。指定範囲の外は未割り当てになります。進捗・コメントは残ります。</p>
      <fieldset disabled={saving} className="space-y-3"><legend className="mb-3 font-bold">割り当てる画像IDの範囲</legend>
        {drafts.length === 0 && <p className="text-sm text-slate-500">割り当て範囲はありません。「範囲を追加」から設定してください。</p>}
        {drafts.map((row, index) => <div key={index} className="grid items-end gap-3 rounded-lg border border-slate-200 p-3 sm:grid-cols-[1fr_1fr_1fr_auto]">
          <label className="space-y-1 text-sm font-bold">開始画像ID<input aria-label={`範囲${index + 1}の開始画像ID`} className={input} type="number" min="1" max="4294967295" step="1" value={row.start} onChange={e => edit(index, "start", e.target.value)} /></label>
          <label className="space-y-1 text-sm font-bold">終了画像ID<input aria-label={`範囲${index + 1}の終了画像ID`} className={input} type="number" min="1" max="4294967295" step="1" value={row.end} onChange={e => edit(index, "end", e.target.value)} /></label>
          <label className="space-y-1 text-sm font-bold">担当者<select aria-label={`範囲${index + 1}の担当者`} className={input} value={row.owner} onChange={e => edit(index, "owner", e.target.value)}><option value="">選択してください</option>{row.owner && !workers.some(w => String(w.user_id) === row.owner) && <option value={row.owner} disabled>{ownerName(row.owner)}（選択不可）</option>}{workers.map(w => <option key={w.user_id} value={w.user_id}>{w.user_name}</option>)}</select></label>
          <button className={button} aria-label={`範囲${index + 1}を削除`} onClick={() => { setNotice(""); setDrafts(rows => rows.filter((_, i) => i !== index)); }}>削除</button>
        </div>)}
        <div className="flex flex-wrap gap-3"><button className={button} disabled={drafts.length >= 1000} onClick={() => { setNotice(""); setDrafts(rows => [...rows, { start: "", end: "", owner: "" }]); }}>範囲を追加</button><button className={button} disabled={!drafts.length} onClick={() => { setNotice(""); setDrafts([]); }}>すべて未割り当てとして選択</button></div>
      </fieldset>
      <div className="flex justify-end"><button className={`${button} bg-blue-600 text-white`} disabled={!dirty || saving} onClick={() => { const invalid = validate(); setError(invalid); if (!invalid) setConfirming(true); }}>選択内容を確認して保存</button></div>
    </>}
    {confirming && <div className="fixed inset-0 z-[100] grid place-items-center bg-slate-950/45 p-4"><section role="dialog" aria-modal="true" aria-labelledby="assignment-confirm-title" className="w-full max-w-xl space-y-4 rounded-2xl bg-white p-6"><h3 id="assignment-confirm-title" className="text-xl font-bold">画像IDの範囲と担当者を変更しますか？</h3><p>現在の割り当てを以下の{drafts.length}範囲で置き換えます。指定外は未割り当てにします。タスク・進捗・コメントは削除しません。</p>{drafts.length ? <ul className="max-h-72 space-y-2 overflow-y-auto">{drafts.map((row, index) => <li key={index}>{row.start}〜{row.end} → {ownerName(row.owner)}（{(Number(row.end) - Number(row.start) + 1).toLocaleString()}件）</li>)}</ul> : <p className="font-bold text-red-700">すべての担当割り当てを解除します。</p>}<div className="flex justify-end gap-3"><button className={button} autoFocus disabled={saving} onClick={() => setConfirming(false)}>戻る</button><button className={`${button} bg-blue-600 text-white`} disabled={saving} onClick={save}>{saving ? "保存中..." : "この内容で割り当てを更新"}</button></div></section></div>}
  </section>;
}
