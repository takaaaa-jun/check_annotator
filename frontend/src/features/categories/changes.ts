import type { Catalog, ImageReview } from "./types";

export function categoryName(image: ImageReview, catalog: Catalog | null, id: number): string {
  return image.categories?.find((category) => category.id === id)?.name
    ?? catalog?.targetCategories.find((category) => category.id === id)?.name
    ?? catalog?.sourceCategories.find((category) => category.id === id)?.name
    ?? `カテゴリ #${id}`;
}

export type ReviewSnapshot = { image: ImageReview; catalog: Catalog | null };

export function categoryChanges(before: ReviewSnapshot | null, after: ReviewSnapshot): string[] {
  if (!before || before.image.imageId !== after.image.imageId || before.image.datasetId !== after.image.datasetId) return [];
  const previous = new Map(before.image.boxes.map((box) => [box.id, box]));
  return after.image.boxes.flatMap((box) => {
    const old = previous.get(box.id);
    const name = categoryName(after.image, after.catalog, box.categoryId);
    if (!old) return [`「${name}」を追加しました（ボックス #${box.id}）。`];
    if (old.categoryId === box.categoryId) return [];
    return [`「${categoryName(before.image, before.catalog, old.categoryId)}」から「${name}」に変更しました（ボックス #${box.id}）。`];
  });
}
