import { describe, expect, it } from "vitest";

import { formatDateTime } from "./date-time";

describe("formatDateTime", () => {
  it("formats a valid API timestamp", () => {
    expect(formatDateTime("2026-09-30T07:30:00Z")).not.toBe("-");
  });

  it("returns a placeholder for an invalid timestamp", () => {
    expect(formatDateTime("invalid")).toBe("-");
  });
});
