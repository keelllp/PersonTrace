import { describe, expect, it } from "vitest";
import { intervalRect, rulerTicks } from "./timeline-math";

describe("intervalRect", () => {
  it("maps interval to percentages", () => {
    expect(intervalRect(30, 60, 120)).toEqual({ leftPct: 25, widthPct: 25 });
  });
  it("floors tiny widths for clickability", () => {
    expect(intervalRect(10, 10, 100).widthPct).toBe(0.8);
  });
  it("clamps to the video bounds", () => {
    const r = intervalRect(110, 130, 120);
    expect(r.leftPct + r.widthPct).toBeLessThanOrEqual(100);
  });
});

describe("rulerTicks", () => {
  it("uses 5s steps for short clips", () => {
    expect(rulerTicks(30)).toEqual([0, 5, 10, 15, 20, 25, 30]);
  });
  it("uses 30s steps for five-minute clips", () => {
    expect(rulerTicks(300)).toEqual([0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300]);
  });
  it("never returns more than 12 ticks", () => {
    expect(rulerTicks(3600).length).toBeLessThanOrEqual(12);
  });
});
