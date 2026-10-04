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

import { logout } from "@/src/lib/api/auth";
import { LogoutButton } from "./logout-button";

const replaceMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
    refresh: refreshMock,
  }),
}));

vi.mock("@/src/lib/api/auth", () => ({
  logout: vi.fn(),
}));

const logoutMock = vi.mocked(logout);

beforeEach(() => {
  replaceMock.mockReset();
  refreshMock.mockReset();
  logoutMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("LogoutButton integration", () => {
  it("ログアウト成功後にログイン画面へ戻す", async () => {
    logoutMock.mockResolvedValue(undefined);
    render(<LogoutButton />);

    await userEvent.setup().click(
      screen.getByRole("button", {
        name: "ログアウト",
      }),
    );

    await waitFor(() => {
      expect(logoutMock).toHaveBeenCalledTimes(1);
      expect(replaceMock).toHaveBeenCalledWith(
        "/login",
      );
      expect(refreshMock).toHaveBeenCalledTimes(1);
    });
  });
});
