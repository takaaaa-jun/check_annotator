export type Category = { id: number; name: string; aliases: string[] };
export type Catalog = {
  version: string;
  datasetId: number;
  sourceCategories: Category[];
  targetCategories: Category[];
  mappings: { sourceCategoryId: number; targetCategoryId: number }[];
};
export type ReviewBox = {
  id: number;
  imageId: number;
  categoryId: number;
  originalCategoryId: number;
  bbox: [number, number, number, number];
  revision: string;
  isBox?: boolean;
};
export type ImageReview = {
  datasetId: number;
  imageId: number;
  fileName: string;
  width: number;
  height: number;
  boxes: ReviewBox[];
  categories?: Category[];
};
export type Replacement = {
  datasetId: number;
  imageId: number;
  annotationId: number;
  expectedCategoryId: number;
  expectedRevision: string;
  targetCategoryId: number;
  catalogVersion: string;
};
export interface CategoryAdapter {
  catalog(): Promise<Catalog>;
  image(imageId: number): Promise<ImageReview>;
  replace(request: Replacement): Promise<ReviewBox>;
}
