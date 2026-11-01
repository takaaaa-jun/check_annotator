// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AssignmentPanel } from "./assignment-panel";
import { getAssignmentRanges, saveAssignmentRanges } from "@/src/lib/api/management";
const router = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/src/lib/api/management", () => ({ getAssignmentRanges: vi.fn(), saveAssignmentRanges: vi.fn() }));
const data = { revision: "a".repeat(64), ranges: [], total_tasks: 30000, image_id_min: 1, image_id_max: 30000 };
const workers = [{ user_id: 6, user_name: "sato", group_count: 0, total_count: 0, completed_count: 0, pending_comments: 0, state_counts: [] }];
beforeEach(() => { vi.clearAllMocks(); vi.mocked(getAssignmentRanges).mockResolvedValue(data); vi.mocked(saveAssignmentRanges).mockResolvedValue({ ...data, revision: "b".repeat(64), ranges: [{ start_image_id: 50, end_image_id: 1249, user_id: 6 }] }); });
afterEach(cleanup);
async function addRange(start = "50", end = "1249") {
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "範囲を追加" }));
  const count = screen.getAllByRole("combobox").length;
  await user.type(screen.getByLabelText(`範囲${count}の開始画像ID`), start);
  await user.type(screen.getByLabelText(`範囲${count}の終了画像ID`), end);
  await user.selectOptions(screen.getByLabelText(`範囲${count}の担当者`), "6");
  return user;
}
describe("画像ID範囲による担当者設定", () => {
  it("1000件の区切りによらない範囲を確認後だけ保存する", async () => {
    const changed = vi.fn(); render(<AssignmentPanel workers={workers} onChanged={changed} />);
    const user = await addRange();
    expect(saveAssignmentRanges).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("50〜1249 → sato（1,200件）");
    await user.click(screen.getByRole("button", { name: "戻る" }));
    expect(saveAssignmentRanges).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" }));
    await user.click(screen.getByRole("button", { name: "この内容で割り当てを更新" }));
    await waitFor(() => expect(saveAssignmentRanges).toHaveBeenCalledWith(data.revision, [{ start_image_id: 50, end_image_id: 1249, user_id: 6 }]));
    expect(await screen.findByRole("status")).toHaveTextContent("画像IDの範囲と担当者を更新しました"); expect(changed).toHaveBeenCalledOnce();
  });
  it("重複と逆転を保存前に検証する", async () => {
    render(<AssignmentPanel workers={workers} onChanged={vi.fn()} />);
    const user = await addRange("20", "10");
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("開始画像IDは終了画像ID以下");
    await user.clear(screen.getByLabelText("範囲1の終了画像ID")); await user.type(screen.getByLabelText("範囲1の終了画像ID"), "30");
    await addRange("30", "40");
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("重複"); expect(saveAssignmentRanges).not.toHaveBeenCalled();
  });
  it("失敗時は入力を保持して成功通知を表示しない", async () => {
    vi.mocked(saveAssignmentRanges).mockRejectedValueOnce(new Error("範囲内に存在しない画像IDがあります"));
    render(<AssignmentPanel workers={workers} onChanged={vi.fn()} />); const user = await addRange();
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" })); await user.click(screen.getByRole("button", { name: "この内容で割り当てを更新" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("存在しない画像ID"); expect(screen.getByLabelText("範囲1の開始画像ID")).toHaveValue(50); expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
  it("全範囲の解除も確認してから保存する", async () => {
    vi.mocked(getAssignmentRanges).mockResolvedValueOnce({ ...data, ranges: [{ start_image_id: 1, end_image_id: 15, user_id: 6 }] });
    render(<AssignmentPanel workers={workers} onChanged={vi.fn()} />); const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "すべて未割り当てとして選択" }));
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" })); expect(screen.getByRole("dialog")).toHaveTextContent("すべての担当割り当てを解除");
    await user.click(screen.getByRole("button", { name: "この内容で割り当てを更新" })); await waitFor(() => expect(saveAssignmentRanges).toHaveBeenCalledWith(data.revision, []));
  });
});
