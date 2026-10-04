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

import { ApiError } from "@/src/lib/api/client";
import {
  getCurrentUser,
  login,
} from "@/src/lib/api/auth";
import { LoginForm } from "./login-form";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

vi.mock("@/src/lib/api/auth", () => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
}));

const getCurrentUserMock =
  vi.mocked(getCurrentUser);
const loginMock = vi.mocked(login);

beforeEach(() => {
  replaceMock.mockReset();
  getCurrentUserMock.mockRejectedValue(
    new ApiError(401, "UNAUTHORIZED", "Unauthorized"),
  );
  loginMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("LoginForm integration", () => {
  it("ログイン成功後に本人のグループ一覧へ遷移する", async () => {
    loginMock.mockResolvedValue({
      user: {
        user_id: 7,
        user_name: "worker",
        role_name: "worker",
      },
    });

    render(<LoginForm />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: "ログイン",
        }),
      ).toBeEnabled();
    });

    await user.type(
      screen.getByLabelText("ユーザー名"),
      "worker",
    );
    await user.type(
      screen.getByLabelText("パスワード"),
      "password",
    );
    await user.click(
      screen.getByRole("button", {
        name: "ログイン",
      }),
    );

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        user_name: "worker",
        password: "password",
      });
      expect(replaceMock).toHaveBeenCalledWith(
        "/mypage/7/groups",
      );
    });
  });
});
