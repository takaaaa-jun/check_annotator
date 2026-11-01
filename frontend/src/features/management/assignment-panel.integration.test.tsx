// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AssignmentPanel } from "./assignment-panel";
import { getAssignments, saveAssignments } from "@/src/lib/api/management";
const router = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/src/lib/api/management", () => ({ getAssignments: vi.fn(), saveAssignments: vi.fn() }));
const groups = [{ group_id: 1, group_name: "00001-01000", user_id: null, total_count: 1000, image_id_min: 1, image_id_max: 1000 }];
const workers = [{ user_id: 6, user_name: "sato", group_count: 0, total_count: 0, completed_count: 0, pending_comments: 0, state_counts: [] }];
beforeEach(() => { vi.clearAllMocks(); vi.mocked(getAssignments).mockResolvedValue({ groups }); vi.mocked(saveAssignments).mockResolvedValue({ groups: [{ ...groups[0], user_id: 6 }] }); });
afterEach(cleanup);
describe("担当者の設定", () => {
  it("選ぶだけでは保存せず、確認後に元の担当者とともに変更を送信する", async () => {
    const user = userEvent.setup(); const changed = vi.fn();
    render(<AssignmentPanel workers={workers} onChanged={changed} />);
    const select = await screen.findByRole("combobox", { name: "00001-01000の担当者" });
    await user.selectOptions(select, "6");
    expect(saveAssignments).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("未割り当て → sato");
    await user.click(screen.getByRole("button", { name: "戻る" }));
    expect(saveAssignments).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" }));
    await user.click(screen.getByRole("button", { name: "この内容で担当者を更新" }));
    await waitFor(() => expect(saveAssignments).toHaveBeenCalledWith([{ group_id: 1, expected_user_id: null, user_id: 6 }]));
    expect(await screen.findByRole("status")).toHaveTextContent("1グループの担当者を更新しました");
    expect(changed).toHaveBeenCalledTimes(1);
  });
  it("失敗時は選択を保持して保存済みと表示しない", async () => {
    vi.mocked(saveAssignments).mockRejectedValueOnce(new Error("担当者が変更されています"));
    const user = userEvent.setup();
    render(<AssignmentPanel workers={workers} onChanged={vi.fn()} />);
    await user.selectOptions(await screen.findByRole("combobox"), "6");
    await user.click(screen.getByRole("button", { name: "選択内容を確認して保存" }));
    await user.click(screen.getByRole("button", { name: "この内容で担当者を更新" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("担当者が変更されています");
    expect(screen.getByRole("combobox")).toHaveValue("6");
    expect(screen.queryByText(/担当者を更新しました/)).not.toBeInTheDocument();
  });
});
