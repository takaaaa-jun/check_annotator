import { describe, expect, it } from "vitest";

import { validateLoginInput } from "./validation";

describe("validateLoginInput", () => {
  it("accepts valid credentials without trimming them", () => {
    expect(
      validateLoginInput({ userName: " takahashi ", password: " test1 " }),
    ).toBeNull();
  });

  it("rejects missing values", () => {
    expect(validateLoginInput({ userName: "", password: "test1" })).not.toBeNull();
    expect(validateLoginInput({ userName: "takahashi", password: "" })).not.toBeNull();
  });

  it("rejects values over the backend limits", () => {
    expect(
      validateLoginInput({ userName: "x".repeat(51), password: "test1" }),
    ).not.toBeNull();
    expect(
      validateLoginInput({ userName: "takahashi", password: "x".repeat(256) }),
    ).not.toBeNull();
  });
});
