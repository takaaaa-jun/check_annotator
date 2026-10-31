"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { APP_BASE_PATH } from "@/src/lib/api/client";
import { CategoryConflict, demoAdapter, editorUrl, liveAdapter } from "./adapter";
import { parseCatalog, searchCategories, suggestedCategory } from "./catalog";
import { demoCatalog } from "./fixtures";
import type { Catalog, CategoryAdapter, ImageReview, ReviewBox } from "./types";

const button = "min-h-11 rounded-lg border border-blue-300 bg-blue-50 px-4 py-2 font-semibold text-blue-900 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-40";
const field = "min-h-11 rounded-lg border border-slate-300 bg-white px-3 py-2";
function message(error: unknown) { return error instanceof Error ? error.message : "処理に失敗しました。"; }

export function CategoryWorkbench() {
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [demoData, setDemoData] = useState(demoCatalog);
  const adapter = useMemo(() => mode === "demo" ? demoAdapter(demoData) : liveAdapter(), [mode, demoData]);
  const adapterRef = useRef<CategoryAdapter>(adapter);
  const epoch = useRef(0);
  const operation = useRef(false);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [image, setImage] = useState<ImageReview | null>(null);
  const [imageInput, setImageInput] = useState("4001");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [confirmation, setConfirmation] = useState<ReviewBox | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    adapterRef.current = adapter;
    const counter = epoch;
    const requestEpoch = ++counter.current;
    operation.current = true;
    const initialId = Number(new URLSearchParams(window.location.search).get("imageId")) || 4001;
    Promise.resolve().then(() => {
      if (requestEpoch !== counter.current) return null;
      setCatalog(null); setImage(null); setConfirmation(null); setSelectedId(null); setError(""); setNotice(""); setBusy(true);
      setImageInput(String(mode === "demo" ? 4001 : initialId));
      return Promise.all([adapter.catalog(), adapter.image(initialId)]);
    })
      .then((result) => {
        if (!result || requestEpoch !== counter.current) return;
        const [nextCatalog, nextImage] = result;
        if (nextCatalog.datasetId !== nextImage.datasetId) throw new Error("画像と対応表のデータセットが一致しません。");
        setCatalog(nextCatalog); setImage(nextImage); setSelectedId(nextImage.boxes[0]?.id ?? null);
      })
      .catch((failure) => { if (requestEpoch === epoch.current) setError(message(failure)); })
      .finally(() => { if (requestEpoch === epoch.current) { operation.current = false; setBusy(false); } });
    return () => { ++counter.current; };
  }, [adapter, mode]);

  async function loadImage() {
    if (operation.current) return;
    const id = Number(imageInput);
    if (!Number.isSafeInteger(id) || id < 1) { setError("画像IDは正の整数で指定してください。"); return; }
    const requestEpoch = ++epoch.current;
    operation.current = true; setBusy(true); setError(""); setNotice(""); setConfirmation(null); setImage(null);
    try {
      const [nextCatalog, nextImage] = await Promise.all([adapterRef.current.catalog(), adapterRef.current.image(id)]);
      if (requestEpoch !== epoch.current) return;
      if (nextCatalog.datasetId !== nextImage.datasetId) throw new Error("画像と対応表のデータセットが一致しません。");
      setCatalog(nextCatalog); setImage(nextImage); setSelectedId(nextImage.boxes[0]?.id ?? null);
    } catch (failure) { if (requestEpoch === epoch.current) { setCatalog(null); setError(message(failure)); } }
    finally { if (requestEpoch === epoch.current) { operation.current = false; setBusy(false); } }
  }
  async function replace() {
    if (!catalog || !image || !confirmation || operation.current) return;
    const target = suggestedCategory(catalog, confirmation);
    if (!target || target.id === confirmation.categoryId) return;
    const requestEpoch = epoch.current;
    operation.current = true; setBusy(true); setError(""); setNotice("");
    try {
      const updated = await adapterRef.current.replace({
        datasetId: image.datasetId, imageId: image.imageId, annotationId: confirmation.id,
        expectedCategoryId: confirmation.categoryId, expectedRevision: confirmation.revision,
        targetCategoryId: target.id, catalogVersion: catalog.version,
      });
      if (requestEpoch !== epoch.current) return;
      setImage((previous) => previous ? { ...previous, boxes: previous.boxes.map((box) => box.id === updated.id ? updated : box) } : previous);
      setNotice(`ボックス #${updated.id} のみを「${target.name}」へ置き換えました。${mode === "demo" ? "実データは変更していません。" : "COCO Annotatorで開いている画像は再読み込みしてください。"}`);
      setConfirmation(null);
    } catch (failure) {
      if (requestEpoch !== epoch.current) return;
      setError(message(failure));
      if (failure instanceof CategoryConflict) { setConfirmation(null); setImage(null); }
    } finally { if (requestEpoch === epoch.current) { operation.current = false; setBusy(false); } }
  }
  async function importCatalog(file: File | undefined) {
    if (!file || mode !== "demo" || busy) return;
    const requestEpoch = epoch.current;
    try {
      if (file.size > 2_000_000) throw new Error("対応表は2MB以下のJSONを選択してください。");
      const parsed = parseCatalog(JSON.parse(await file.text()));
      if (requestEpoch !== epoch.current) return;
      // Changing the adapter clears pending confirmations and starts a fresh demo session.
      setDemoData(parsed);
    } catch (failure) { setError(message(failure)); }
  }

  const selected = image?.boxes.find((box) => box.id === selectedId);
  const matches = catalog ? searchCategories(catalog.targetCategories, query) : [];
  const originalName = (box: ReviewBox) => catalog?.sourceCategories.find((c) => c.id === box.originalCategoryId)?.name ?? `未登録の元カテゴリ #${box.originalCategoryId}`;
  const currentName = (box: ReviewBox) => box.categoryId === box.originalCategoryId ? originalName(box) : catalog?.targetCategories.find((c) => c.id === box.categoryId)?.name ?? `カテゴリ #${box.categoryId}`;
  const confirmedTarget = catalog && confirmation ? suggestedCategory(catalog, confirmation) : undefined;

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 text-slate-900 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><h1 className="text-2xl font-extrabold">カテゴリ確認・置き換え</h1><p className="mt-2 text-slate-600">元カテゴリを確認し、バウンディングボックス一つずつ対応するカテゴリへ置き換えます。</p></div>
        <label className="flex items-center gap-2">データ元<select aria-label="データ元" className={field} value={mode} disabled={busy} onChange={(event) => { setImage(null); setCatalog(null); setConfirmation(null); setBusy(true); setMode(event.target.value as "demo" | "live"); }}><option value="demo">テスト（仮データ）</option><option value="live">COCO Annotator（実データ）</option></select></label>
      </div>
      <div className={`rounded-xl border p-4 ${mode === "demo" ? "border-amber-300 bg-amber-50" : "border-blue-300 bg-blue-50"}`}>
        {mode === "demo" ? "テストモード：テスト1〜3と仮のボックスを使用します。操作はこの画面内だけで有効で、再読み込みすると元に戻ります。実画像・実DBは変更しません。" : "実データモード：COCO Annotatorへのログインと対象データセットの権限が必要です。更新前にCOCO側の画像編集を保存して閉じてください。接続エラー時にテストデータへ切り替わることはありません。"}
      </div>
      <section className="flex flex-wrap items-end gap-4 rounded-xl border bg-white p-5" aria-label="読み込み設定">
        <label className="grid gap-2">画像ID<input aria-label="画像ID" type="number" min="1" className={field} value={imageInput} disabled={busy || mode === "demo"} onChange={(event) => setImageInput(event.target.value)} /></label>
        <button className={button} disabled={busy} onClick={loadImage}>再読み込み</button>
        {mode === "demo" && <label className="grid gap-2">対応表JSONを試す<input type="file" accept=".json,application/json" disabled={busy} onChange={(event) => { void importCatalog(event.target.files?.[0]); event.target.value = ""; }} /></label>}
        <a href={`${APP_BASE_PATH}/category-review.example.json`} download className="py-2 text-sm font-semibold text-blue-800 underline">対応表サンプルをダウンロード</a>
        {catalog && <p className="text-sm text-slate-600">データセット {catalog.datasetId} / 対応表 {catalog.version}</p>}
      </section>
      {busy && <p role="status">処理中です…</p>}
      {error && <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-800">{error}</p>}
      {notice && <p role="status" className="rounded-lg border border-green-300 bg-green-50 p-4 text-green-900">{notice}</p>}
      {image && catalog && <div className="grid gap-6 lg:grid-cols-2">
        <section className="space-y-4 rounded-xl border bg-white p-5">
          <h2 className="text-lg font-bold">画像 {image.imageId}：{image.fileName}</h2>
          <svg viewBox={`0 0 ${image.width} ${image.height}`} className="w-full rounded-lg bg-slate-100" role="img" aria-label="画像とボックスの位置。選択中のボックスを青で表示">
            {mode === "live" && <image href={`/coco-annotator/api/image/${image.imageId}`} width={image.width} height={image.height} />}
            {mode === "demo" && <text x="320" y="220" textAnchor="middle" fill="#64748b" fontSize="25">仮の画像・ボックス</text>}
            {image.boxes.map((box) => <g key={box.id}>
              <rect x={box.bbox[0]} y={box.bbox[1]} width={box.bbox[2]} height={box.bbox[3]} fill={box.id === selectedId ? "#3b82f622" : "transparent"} stroke={box.id === selectedId ? "#2563eb" : "#f59e0b"} strokeWidth={box.id === selectedId ? 5 : 2} />
              <text x={box.bbox[0] + 5} y={box.bbox[1] + 20} fill="#0f172a" fontSize="16">#{box.id}</text>
            </g>)}
          </svg>
          <p className="text-sm text-slate-600">ボックス数：{image.boxes.length}。下の一覧で対象を選んでください。矩形以外のアノテーションは変更対象に含みません。</p>
          {selected && <p className="font-semibold">選択中 #{selected.id} / 座標 [x, y, 幅, 高さ]：{selected.bbox.join(", ")}</p>}
        </section>
        <section className="space-y-4 rounded-xl border bg-white p-5" aria-labelledby="search-categories">
          <h2 id="search-categories" className="text-lg font-bold">新しく付与するカテゴリを探す</h2>
          <label className="grid gap-2">名前・別名・IDで検索<input className={field} value={query} placeholder="例：テスト1、パン、bread" onChange={(event) => setQuery(event.target.value)} /></label>
          <p className="text-sm text-slate-600">候補 {matches.length}件。カテゴリを選んでCOCO Annotatorへ進み、画像上で新しいボックスを描画します。</p>
          <ul className="max-h-80 space-y-2 overflow-y-auto">
            {matches.slice(0, 100).map((category) => <li key={category.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3">
              <div><p className="font-bold">{category.name} <span className="text-sm font-normal">#{category.id}</span></p><p className="text-sm text-slate-500">{category.aliases.join(" / ")}</p></div>
              {mode === "live" ? <a href={editorUrl(image.imageId, catalog.datasetId, category.id)} target="_blank" rel="noopener noreferrer" className={button}>このカテゴリで矩形を描く</a> : <button className={button} onClick={() => setNotice(`「${category.name}」を選択しました。実データ接続後はCOCO Annotatorでこのカテゴリを選択し、矩形を描けます。仮カテゴリは実DBへ送信しません。`)}>このカテゴリを試す</button>}
            </li>)}
          </ul>
          {matches.length === 0 && <p>該当するカテゴリはありません。</p>}
          {matches.length > 100 && <p>先頭100件を表示しています。検索文字列を追加してください。</p>}
          {mode === "live" && <p className="text-sm text-slate-600">未保存の編集を守るため、カテゴリ選択による新規描画は別タブで開きます。ボックスは描画・保存するまで追加されません。</p>}
        </section>
      </div>}
      {image && catalog && <section className="overflow-x-auto rounded-xl border bg-white p-5">
        <h2 className="mb-4 text-lg font-bold">元カテゴリと置換候補（ボックス単位）</h2>
        <table className="w-full text-left"><thead><tr>{["ボックス", "元カテゴリ", "現在のカテゴリ", "対応する新カテゴリ", "操作"].map((heading) => <th key={heading} className="border-b p-3">{heading}</th>)}</tr></thead>
          <tbody>{image.boxes.map((box) => { const target = suggestedCategory(catalog, box); return <tr key={box.id} className={box.id === selectedId ? "bg-blue-50" : ""}>
            <td className="border-b p-3"><button className="font-bold text-blue-800 underline" onClick={() => setSelectedId(box.id)}>#{box.id}</button><p className="text-xs text-slate-500">{box.bbox.join(", ")}</p></td>
            <td className="border-b p-3">{originalName(box)}</td><td className="border-b p-3">{currentName(box)}</td><td className="border-b p-3">{target?.name ?? "対応未設定"}</td>
            <td className="border-b p-3"><button className={button} disabled={busy || !target || box.categoryId !== box.originalCategoryId || target.id === box.categoryId} onClick={() => { setSelectedId(box.id); setConfirmation(structuredClone(box)); }}>{box.categoryId !== box.originalCategoryId || target?.id === box.categoryId ? "置換済み" : "置き換えを確認"}</button></td>
          </tr>; })}</tbody>
        </table>
        {image.boxes.length === 0 && <p className="py-4">置換対象のボックスはありません。右側の検索から新規付与を開始できます。</p>}
      </section>}
      {confirmation && confirmedTarget && <div className="fixed inset-0 z-[60] grid place-items-center bg-slate-950/50 p-4" onKeyDown={(event) => { if (event.key === "Escape" && !busy) setConfirmation(null); }}>
        <section role="alertdialog" aria-modal="true" aria-labelledby="replacement-title" aria-describedby="replacement-description" className="w-full max-w-lg space-y-5 rounded-2xl bg-white p-6 shadow-xl">
          <h2 id="replacement-title" className="text-xl font-bold">このボックスを置き換えますか？</h2>
          <p id="replacement-description">画像 {image?.imageId}・ボックス #{confirmation.id} の「{currentName(confirmation)}」を「{confirmedTarget.name}」へ置き換えます。座標と元カテゴリを保持し、他のボックスは変更しません。</p>
          <p>座標：{confirmation.bbox.join(", ")}</p>
          {mode === "demo" && <p className="text-amber-800">テスト操作です。実データは変更しません。</p>}
          <div className="flex justify-end gap-3"><button autoFocus disabled={busy} className={button} onClick={() => setConfirmation(null)} onKeyDown={(event) => { if (event.key === "Tab" && event.shiftKey) { event.preventDefault(); document.getElementById("confirm-replacement")?.focus(); } }}>キャンセル</button><button id="confirm-replacement" disabled={busy} className={button} onClick={replace} onKeyDown={(event) => { if (event.key === "Tab" && !event.shiftKey) { event.preventDefault(); if (event.currentTarget.previousElementSibling instanceof HTMLElement) event.currentTarget.previousElementSibling.focus(); } }}>この1件を置き換える</button></div>
        </section>
      </div>}
    </main>
  );
}
