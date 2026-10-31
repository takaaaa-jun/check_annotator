// @vitest-environment jsdom
import { cleanup, render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CategoryWorkbench } from "./category-workbench";
import { demoCatalog, demoImage } from "./fixtures";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("カテゴリ確認画面", () => {
  it("行内表示は指定された画像IDの実データを参照し、画像切り替えや仮データの操作を出さない", async () => {
    const fetch = vi.fn().mockImplementation(async (url: string) => ({ ok: true, json: async () => url.endsWith("/catalog") ? demoCatalog : { ...demoImage, imageId: 4050 } }));
    vi.stubGlobal("fetch", fetch);
    render(<CategoryWorkbench imageId={4050} embedded />);
    await screen.findByRole("button", { name: "#90001" });
    expect(fetch.mock.calls.some((call) => call[0].endsWith("/images/4050"))).toBe(true);
    expect(screen.getByRole("region", { name: "画像4050のカテゴリ確認" })).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "データ元" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("画像ID")).not.toBeInTheDocument();
  });
  it("キャンセルでは更新せず、確認したボックス一つだけを置換する", async () => {
    const user = userEvent.setup();
    render(<CategoryWorkbench />);
    await screen.findByRole("button", { name: "#90001" });
    const row1 = screen.getByRole("button", { name: "#90001" }).closest("tr")!;
    const row2 = screen.getByRole("button", { name: "#90002" }).closest("tr")!;
    await user.click(within(row1).getByRole("button", { name: "置き換えを確認" }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("ボックス #90001");
    await user.click(screen.getByRole("button", { name: "キャンセル" }));
    expect(within(row1).getByRole("button", { name: "置き換えを確認" })).toBeEnabled();
    await user.click(within(row1).getByRole("button", { name: "置き換えを確認" }));
    await user.click(screen.getByRole("button", { name: "この1件を置き換える" }));
    await waitFor(() => expect(within(row1).getByRole("button", { name: "置換済み" })).toBeDisabled());
    expect(within(row2).getByRole("button", { name: "置き換えを確認" })).toBeEnabled();
    expect(within(row1).getByText("元カテゴリA")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "カテゴリの変更通知" })).toHaveTextContent("「元カテゴリA」から「テスト1」に変更しました");
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });
  it("参照画面に新規付与の検索や操作を表示しない", async () => {
    render(<CategoryWorkbench />);
    const row = (await screen.findByRole("button", { name: "#90003" })).closest("tr")!;
    expect(within(row).getByRole("button", { name: "置き換えを確認" })).toBeDisabled();
    expect(screen.queryByRole("textbox", { name: "名前・別名・IDで検索" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "このカテゴリを試す" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "このカテゴリで矩形を描く" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "COCO Annotatorで付与済みのカテゴリ" })).toBeInTheDocument();
  });
  it("実APIの未設定エラーでテストデータを残さず、書き込みもしない", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({ message: "カテゴリ対応表が未設定です" }) });
    vi.stubGlobal("fetch", fetch);
    const user = userEvent.setup();
    render(<CategoryWorkbench />);
    await screen.findByRole("button", { name: "#90001" });
    await user.selectOptions(screen.getByRole("combobox", { name: "データ元" }), "live");
    expect(await screen.findByRole("alert")).toHaveTextContent("未設定");
    expect(screen.queryByRole("button", { name: "#90001" })).not.toBeInTheDocument();
    expect(fetch.mock.calls.every((call) => !call[1]?.method)).toBe(true);
  });
  it("COCO側の変更と追加をフォーカス復帰時に通知し、再取得では重複しない", async () => {
    const current = structuredClone(demoImage);
    const fetch = vi.fn().mockImplementation(async (url: string) => ({ ok: true, json: async () => url.endsWith("/catalog") ? demoCatalog : structuredClone(current) }));
    vi.stubGlobal("fetch", fetch);
    const user = userEvent.setup();
    render(<CategoryWorkbench />);
    await screen.findByRole("button", { name: "#90001" });
    await user.selectOptions(screen.getByRole("combobox", { name: "データ元" }), "live");
    await waitFor(() => expect(screen.getByRole("button", { name: "再読み込み" })).toBeEnabled());
    current.boxes[0].categoryId = 101;
    current.boxes.push({ ...current.boxes[0], id: 90004 });
    window.dispatchEvent(new Event("focus"));
    const notice = await screen.findByRole("status", { name: "カテゴリの変更通知" });
    expect(notice).toHaveTextContent("「元カテゴリA」から「テスト1」に変更しました");
    expect(notice).toHaveTextContent("「テスト1」を追加しました");
    await user.click(screen.getByRole("button", { name: "再読み込み" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "再読み込み" })).toBeEnabled());
    expect(within(notice).getAllByRole("listitem")).toHaveLength(2);
    expect(fetch.mock.calls.every((call) => !call[1]?.method)).toBe(true);
  });
  it("対応表が未設定でも実際の付与済みカテゴリを参照できる", async () => {
    const image = { ...demoImage, categories: [{ id: 1, name: "COCOのパン", aliases: [] }] };
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => url.endsWith("/catalog")
      ? { ok: false, status: 503, json: async () => ({ message: "置換対応表が未設定です" }) }
      : { ok: true, json: async () => image }));
    const user = userEvent.setup();
    render(<CategoryWorkbench />);
    await screen.findByRole("button", { name: "#90001" });
    await user.selectOptions(screen.getByRole("combobox", { name: "データ元" }), "live");
    await screen.findByText("置換対応表が利用できないため、参照のみ可能です。");
    expect(screen.getAllByText("COCOのパン").length).toBeGreaterThan(0);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "カテゴリの変更通知" })).not.toBeInTheDocument();
  });
});
