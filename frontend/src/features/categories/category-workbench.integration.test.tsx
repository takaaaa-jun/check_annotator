// @vitest-environment jsdom
import { cleanup, render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CategoryWorkbench } from "./category-workbench";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("カテゴリ確認画面", () => {
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
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });
  it("未対応カテゴリの自動置換を禁止し、別名から新カテゴリを検索できる", async () => {
    const user = userEvent.setup();
    render(<CategoryWorkbench />);
    const row = (await screen.findByRole("button", { name: "#90003" })).closest("tr")!;
    expect(within(row).getByRole("button", { name: "置き換えを確認" })).toBeDisabled();
    await user.type(screen.getByRole("textbox", { name: "名前・別名・IDで検索" }), "bread");
    expect(screen.getAllByRole("button", { name: "このカテゴリを試す" })).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "このカテゴリを試す" }));
    expect(screen.getByRole("status")).toHaveTextContent("仮カテゴリは実DBへ送信しません");
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
});
