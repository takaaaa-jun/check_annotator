import { describe, expect, it } from "vitest";
import { categoryChanges } from "./changes";
import { demoCatalog, demoImage } from "./fixtures";

const before = { image: demoImage, catalog: demoCatalog };
describe("保存済みカテゴリの変更通知", () => {
  it("初回表示、画像の切り替え、座標だけの変更ではカテゴリ追加を通知しない", () => {
    expect(categoryChanges(null, before)).toEqual([]);
    expect(categoryChanges(before, { ...before, image: { ...demoImage, imageId: 999 } })).toEqual([]);
    const moved = structuredClone(demoImage);
    moved.boxes[0].bbox[0] += 10;
    expect(categoryChanges(before, { ...before, image: moved })).toEqual([]);
  });
  it("ボックスIDで照合し、変更前後と同カテゴリの追加を通知する", () => {
    const image = structuredClone(demoImage);
    image.boxes[0].categoryId = 101;
    image.boxes.push({ ...image.boxes[0], id: 90004 });
    const after = { image, catalog: demoCatalog };
    expect(categoryChanges(before, after)).toEqual([
      "「元カテゴリA」から「テスト1」に変更しました（ボックス #90001）。",
      "「テスト1」を追加しました（ボックス #90004）。",
    ]);
    expect(categoryChanges(after, after)).toEqual([]);
  });
  it("対応表がなくてもCOCOが返す実際のカテゴリ名を使う", () => {
    const oldImage = { ...demoImage, categories: [{ id: 1, name: "パン", aliases: [] }] };
    const image = structuredClone(oldImage);
    image.categories.push({ id: 101, name: "クロワッサン", aliases: [] });
    image.boxes[0].categoryId = 101;
    expect(categoryChanges({ image: oldImage, catalog: null }, { image, catalog: null })[0]).toContain("「パン」から「クロワッサン」に変更しました");
  });
});
