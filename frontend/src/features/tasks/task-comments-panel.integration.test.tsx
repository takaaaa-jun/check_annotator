// @vitest-environment jsdom

import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import {
  cleanup,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  createTaskComment,
  getTaskComments,
} from "../../lib/api/tasks";
import { TaskCommentsPanel } from "./task-comments-panel";

vi.mock("../../lib/api/tasks", () => ({
  createTaskComment: vi.fn(),
  getTaskComments: vi.fn(),
}));

const getTaskCommentsMock =
  vi.mocked(getTaskComments);
const createTaskCommentMock =
  vi.mocked(createTaskComment);

const firstComment = {
  comment_id: 1,
  user_id: 1,
  user_name: "takahashi",
  parent_id: null,
  content: "確認をお願いします",
  created_at: "2026-10-04T03:00:00Z",
  updated_at: "2026-10-04T03:00:00Z",
};

beforeEach(() => {
  getTaskCommentsMock.mockResolvedValue({
    task_id: 10,
    comments: [firstComment],
    pagination: {
      page: 1,
      page_size: 50,
      total: 1,
      total_pages: 1,
    },
  });
  createTaskCommentMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("TaskCommentsPanel integration", () => {
  it("コメントを表示して既存コメントへ返信できる", async () => {
    createTaskCommentMock.mockResolvedValue({
      comment_id: 2,
      task_id: 10,
      user_id: 2,
      user_name: "reviewer",
      parent_id: 1,
      content: "確認しました",
      created_at: "2026-10-04T04:00:00Z",
      updated_at: "2026-10-04T04:00:00Z",
    });

    render(
      <TaskCommentsPanel
        taskId={10}
        imageId={100}
        onUnauthorized={vi.fn()}
      />,
    );
    const user = userEvent.setup();

    expect(
      await screen.findByText("確認をお願いします"),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "このコメントに返信",
      }),
    );
    await user.type(
      screen.getByLabelText("コメント #1 へ返信"),
      "確認しました",
    );
    await user.click(
      screen.getByRole("button", {
        name: "返信する",
      }),
    );

    await waitFor(() => {
      expect(createTaskCommentMock).toHaveBeenCalledWith(
        10,
        {
          content: "確認しました",
          parentId: 1,
        },
      );
    });
    expect(
      await screen.findByText("返信を投稿しました"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("確認しました"),
    ).toBeInTheDocument();
  });

  it("空白のみのコメントはAPIへ送信しない", async () => {
    render(
      <TaskCommentsPanel
        taskId={10}
        imageId={100}
        onUnauthorized={vi.fn()}
      />,
    );
    const user = userEvent.setup();

    await screen.findByText("確認をお願いします");
    await user.type(
      screen.getByLabelText("新しいコメント"),
      "   ",
    );
    await user.click(
      screen.getByRole("button", {
        name: "投稿する",
      }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("コメントを入力してください");
    expect(createTaskCommentMock).not.toHaveBeenCalled();
  });

  it("初期文言を設定しCtrl+Enterで投稿できる", async () => {
    const onCompleted = vi.fn();
    createTaskCommentMock.mockResolvedValue({
      comment_id: 2,
      task_id: 10,
      user_id: 1,
      user_name: "takahashi",
      parent_id: null,
      content: "付与予定ラベル：tuna",
      created_at: "2026-10-04T04:00:00Z",
      updated_at: "2026-10-04T04:00:00Z",
    });

    render(
      <TaskCommentsPanel
        taskId={10}
        imageId={100}
        initialContent="付与予定ラベル："
        focusKey={1}
        onUnauthorized={vi.fn()}
        onCompleted={onCompleted}
      />,
    );
    const user = userEvent.setup();

    await screen.findByText("確認をお願いします");
    const input = screen.getByLabelText(
      "新しいコメント",
    );
    expect(input).toHaveFocus();
    expect(input).toHaveValue("付与予定ラベル：");

    await user.type(input, "tuna{Control>}{Enter}{/Control}");

    await waitFor(() => {
      expect(createTaskCommentMock).toHaveBeenCalledWith(
        10,
        {
          content: "付与予定ラベル：tuna",
          parentId: null,
        },
      );
      expect(onCompleted).toHaveBeenCalledTimes(1);
    });
  });
});
