import type { Catalog, ImageReview } from "./types";

export const demoCatalog: Catalog = {
  version: "demo-1", datasetId: 2,
  sourceCategories: [
    { id: 1, name: "元カテゴリA", aliases: ["original A"] },
    { id: 2, name: "元カテゴリB", aliases: ["original B"] },
    { id: 3, name: "元カテゴリC（対応未設定）", aliases: [] },
  ],
  targetCategories: [
    { id: 101, name: "テスト1", aliases: ["パン", "bread"] },
    { id: 102, name: "テスト2", aliases: ["ご飯", "rice"] },
    { id: 103, name: "テスト3", aliases: ["麺", "noodle"] },
  ],
  mappings: [{ sourceCategoryId: 1, targetCategoryId: 101 }, { sourceCategoryId: 2, targetCategoryId: 102 }],
};
export const demoImage: ImageReview = {
  datasetId: 2, imageId: 4001, fileName: "テスト画像（実画像・実DBは使用しません）", width: 640, height: 400,
  boxes: [
    { id: 90001, imageId: 4001, categoryId: 1, originalCategoryId: 1, bbox: [50, 50, 200, 140], revision: "demo-0" },
    { id: 90002, imageId: 4001, categoryId: 1, originalCategoryId: 1, bbox: [300, 80, 230, 190], revision: "demo-0" },
    { id: 90003, imageId: 4001, categoryId: 3, originalCategoryId: 3, bbox: [70, 250, 170, 100], revision: "demo-0" },
  ],
};
