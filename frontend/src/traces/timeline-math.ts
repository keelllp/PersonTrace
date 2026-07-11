export function intervalRect(start: number, end: number, duration: number) {
  if (duration <= 0) return { leftPct: 0, widthPct: 0.8 };
  const leftPct = Math.min(Math.max((start / duration) * 100, 0), 100);
  const naturalWidth = ((end - start) / duration) * 100;
  const widthPct = Math.min(Math.max(naturalWidth, 0.8), 100 - leftPct);
  return { leftPct, widthPct };
}

const STEPS = [1, 5, 10, 30, 60, 300, 600];

export function rulerTicks(duration: number): number[] {
  if (duration <= 0) return [0];
  const step = STEPS.find((s) => duration / s <= 11) ?? 600;
  const ticks: number[] = [];
  for (let t = 0; t <= duration; t += step) ticks.push(t);
  return ticks;
}
