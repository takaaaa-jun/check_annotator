import { parseCatalog } from "./catalog";
import { demoCatalog, demoImage } from "./fixtures";
import type { Catalog, CategoryAdapter, ImageReview, Replacement, ReviewBox } from "./types";

export class CategoryConflict extends Error {}
export function demoAdapter(catalog: Catalog = demoCatalog): CategoryAdapter {
  const image = structuredClone(demoImage);
  image.datasetId = catalog.datasetId;
  const firstSource = catalog.sourceCategories[0].id;
  const unmapped = catalog.sourceCategories.find((source) => !catalog.mappings.some((mapping) => mapping.sourceCategoryId === source.id));
  image.boxes.forEach((box, index) => {
    box.categoryId = index < 2 ? firstSource : (unmapped?.id ?? catalog.sourceCategories.at(-1)!.id);
    box.originalCategoryId = box.categoryId;
  });
  let revision = 0;
  return {
    async catalog() { return structuredClone(catalog); },
    async image() { return structuredClone(image); },
    async replace(request) {
      const box = image.boxes.find((b) => b.id === request.annotationId);
      if (request.datasetId !== image.datasetId || request.imageId !== image.imageId || request.catalogVersion !== catalog.version || !box || box.categoryId !== request.expectedCategoryId || box.revision !== request.expectedRevision) throw new CategoryConflict("表示後にデータが更新されました。再読み込みしてください。");
      const mapping = catalog.mappings.find((m) => m.sourceCategoryId === box.originalCategoryId);
      if (mapping?.targetCategoryId !== request.targetCategoryId || !catalog.targetCategories.some((c) => c.id === request.targetCategoryId)) throw new Error("対応表と置換先が一致しません。");
      if (box.categoryId !== box.originalCategoryId) throw new Error("元カテゴリから変更済みです。");
      box.categoryId = request.targetCategoryId;
      box.revision = `demo-${++revision}`;
      return structuredClone(box);
    },
  };
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/coco-annotator/api/category-review${path}`, {
    ...init, credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Category-Review": "1" },
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message = response.status === 401
      ? "COCO Annotatorにログインしてから、再読み込みしてください。"
      : data?.message ?? `接続に失敗しました（HTTP ${response.status}）。`;
    if (response.status === 409) throw new CategoryConflict(message);
    throw new Error(message);
  }
  return data as T;
}
export function liveAdapter(): CategoryAdapter {
  return {
    async catalog() { return parseCatalog(await request<unknown>("/catalog")); },
    image(imageId) { return request<ImageReview>(`/images/${imageId}`); },
    replace(data: Replacement) { return request<ReviewBox>(`/annotations/${data.annotationId}/category`, { method: "PUT", body: JSON.stringify(data) }); },
  };
}
export async function readReview(adapter: CategoryAdapter, imageId: number) {
  const [catalogResult, imageResult] = await Promise.allSettled([adapter.catalog(), adapter.image(imageId)]);
  if (imageResult.status === "rejected") throw imageResult.reason;
  const catalog = catalogResult.status === "fulfilled" ? catalogResult.value : null;
  const image = imageResult.value;
  if (catalog && catalog.datasetId !== image.datasetId) throw new Error("画像と対応表のデータセットが一致しません。");
  return { catalog, image, warning: catalogResult.status === "rejected" ? String(catalogResult.reason instanceof Error ? catalogResult.reason.message : "置換対応表を読み込めません。") : "" };
}
export function editorUrl(imageId: number, datasetId: number, categoryId: number): string {
  const query = new URLSearchParams({ dataset_id: String(datasetId), category_id: String(categoryId), tool: "bbox" });
  // The document query forces an image reload when reusing the named editor tab.
  return `/coco-annotator/?review_image=${imageId}&category=${categoryId}#/annotate/${imageId}?${query}`;
}
