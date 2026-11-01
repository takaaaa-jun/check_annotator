import type { Catalog, Category, ReviewBox } from "./types";

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("JSONの形式が正しくありません。");
  return value as Record<string, unknown>;
}
function positiveId(value: unknown): number {
  if (!Number.isSafeInteger(value) || (value as number) <= 0) throw new Error("IDは正の整数で指定してください。");
  return value as number;
}
function categories(value: unknown): Category[] {
  if (!Array.isArray(value) || !value.length) throw new Error("カテゴリ一覧が空です。");
  const ids = new Set<number>();
  return value.map((item) => {
    const data = record(item);
    const id = positiveId(data.id);
    if (ids.has(id)) throw new Error(`カテゴリID ${id} が重複しています。`);
    ids.add(id);
    if (typeof data.name !== "string" || !data.name.trim()) throw new Error("カテゴリ名が空です。");
    const aliases = data.aliases ?? [];
    if (!Array.isArray(aliases) || aliases.some((alias) => typeof alias !== "string")) throw new Error("別名は文字列の配列で指定してください。");
    return { id, name: data.name.trim(), aliases: aliases as string[] };
  });
}
export function parseCatalog(value: unknown): Catalog {
  const data = record(value);
  if (typeof data.version !== "string" || !data.version.trim()) throw new Error("対応表のversionが必要です。");
  const sourceCategories = categories(data.sourceCategories);
  const targetCategories = categories(data.targetCategories);
  if (!Array.isArray(data.mappings)) throw new Error("対応表mappingsが必要です。");
  const mapped = new Set<number>();
  const mappings = data.mappings.map((item) => {
    const mapping = record(item);
    const sourceCategoryId = positiveId(mapping.sourceCategoryId);
    const targetCategoryId = positiveId(mapping.targetCategoryId);
    if (!sourceCategories.some((c) => c.id === sourceCategoryId) || !targetCategories.some((c) => c.id === targetCategoryId)) throw new Error("対応表に存在しないカテゴリIDがあります。");
    if (mapped.has(sourceCategoryId)) throw new Error("一つの元カテゴリに複数の置換先は指定できません。");
    mapped.add(sourceCategoryId);
    return { sourceCategoryId, targetCategoryId };
  });
  return { version: data.version.trim(), datasetId: positiveId(data.datasetId), sourceCategories, targetCategories, mappings };
}
export function suggestedCategory(catalog: Catalog, box: ReviewBox): Category | undefined {
  const mapping = catalog.mappings.find((m) => m.sourceCategoryId === box.originalCategoryId);
  return catalog.targetCategories.find((c) => c.id === mapping?.targetCategoryId);
}
export function searchCategories(categories: Category[], query: string): Category[] {
  const terms = query.normalize("NFKC").toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  return categories.filter((c) => {
    const haystack = [c.name, ...c.aliases].join(" ").normalize("NFKC").toLocaleLowerCase();
    return terms.every((term) => haystack.includes(term) || String(c.id) === term);
  });
}
