import { describe, expect, it } from "vitest";
import { formatTimecode } from "./format";

describe("formatTimecode", () => {
  it("formats zero", () => expect(formatTimecode(0)).toBe("00:00"));
  it("floors fractional seconds", () => expect(formatTimecode(12.9)).toBe("00:12"));
  it("carries minutes", () => expect(formatTimecode(83)).toBe("01:23"));
  it("handles hours-long inputs gracefully", () =>
    expect(formatTimecode(3671)).toBe("61:11"));
});
