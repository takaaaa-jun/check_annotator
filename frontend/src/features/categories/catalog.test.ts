import { afterEach, describe, expect, it, vi } from "vitest";
import { CategoryConflict, demoAdapter, editorUrl, liveAdapter } from "./adapter";
import { parseCatalog, searchCategories } from "./catalog";
import { demoCatalog } from "./fixtures";

afterEach(() => vi.unstubAllGlobals());

it("COCOの未ログイン応答を日本語で説明する", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ message: "Authorization required" }) }));
  await expect(liveAdapter().catalog()).rejects.toThrow("COCO Annotatorにログイン");
});

describe("カテゴリ対応表", () => {
  it("名前・別名・全角の数字を検索できる", () => {
    expect(searchCategories(demoCatalog.targetCategories, "ＢＲＥＡＤ").map((c) => c.id)).toEqual([101]);
    expect(searchCategories(demoCatalog.targetCategories, "テスト １").map((c) => c.id)).toEqual([101]);
    expect(searchCategories(demoCatalog.targetCategories, "存在しない")).toEqual([]);
  });
  it("IDの重複・未登録IDへの対応・曖昧な対応・不正IDを拒否する", () => {
    for (const change of [
      { targetCategories: [...demoCatalog.targetCategories, demoCatalog.targetCategories[0]] },
      { mappings: [{ sourceCategoryId: 1, targetCategoryId: 999 }] },
      { mappings: [...demoCatalog.mappings, { sourceCategoryId: 1, targetCategoryId: 102 }] },
      { datasetId: 0 }, { version: "" },
    ]) expect(() => parseCatalog({ ...demoCatalog, ...change })).toThrow();
  });
  it("カテゴリ選択と画像・データセットをCOCO側へ引き継ぐ", () => {
    const url = new URL(editorUrl(4001, 2, 101), "http://localhost");
    const query = new URLSearchParams(url.hash.split("?")[1]);
    expect(url.pathname).toBe("/coco-annotator/");
    expect(url.hash.startsWith("#/annotate/4001?")).toBe(true);
    expect(query.get("category_id")).toBe("101");
    expect(query.get("dataset_id")).toBe("2");
    expect(query.get("tool")).toBe("bbox");
  });
});

describe("ボックス単位の置換", () => {
  it("一つだけ更新し、元カテゴリ・形状・同カテゴリの別ボックスを保持する", async () => {
    const adapter = demoAdapter();
    const before = await adapter.image(4001);
    const box = before.boxes[0];
    const request = { datasetId: 2, imageId: 4001, annotationId: box.id, expectedCategoryId: box.categoryId, expectedRevision: box.revision, targetCategoryId: 101, catalogVersion: demoCatalog.version };
    await adapter.replace(request);
    const after = await adapter.image(4001);
    expect(after.boxes[0]).toMatchObject({ categoryId: 101, originalCategoryId: 1, bbox: box.bbox });
    expect(after.boxes.slice(1)).toEqual(before.boxes.slice(1));
    await expect(adapter.replace(request)).rejects.toBeInstanceOf(CategoryConflict);
  });
  it("対応外の置換先を拒否し、操作セッションのデータを分離する", async () => {
    const adapter = demoAdapter();
    const box = (await adapter.image(4001)).boxes[0];
    await expect(adapter.replace({ datasetId: 2, imageId: 4001, annotationId: box.id, expectedCategoryId: 1, expectedRevision: box.revision, targetCategoryId: 102, catalogVersion: demoCatalog.version })).rejects.toThrow("対応表");
    expect((await demoAdapter().image(4001)).boxes[0].categoryId).toBe(1);
  });
});
