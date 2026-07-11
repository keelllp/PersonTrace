import { formatTimecode } from "../lib/format";
import type { Results } from "../lib/types";
import { intervalRect, rulerTicks } from "./timeline-math";

interface TimelineProps {
  results: Results;
  currentTime: number;
  onSeek: (seconds: number) => void;
}

export function Timeline({ results, currentTime, onSeek }: TimelineProps) {
  const duration = results.video.duration_s ?? 0;
  if (duration <= 0) return null;
  const playheadLeft = `${Math.min((currentTime / duration) * 100, 100)}%`;

  return (
    <div className="bg-panel border border-line rounded-lg p-4 select-none">
      <div className="relative sm:ml-28">
        <div className="relative h-5 border-b border-line">
          {rulerTicks(duration).map((t) => (
            <span
              key={t}
              className="tc absolute -translate-x-1/2 text-[10px] text-dim"
              style={{ left: `${(t / duration) * 100}%` }}
            >
              {formatTimecode(t)}
            </span>
          ))}
        </div>

        <div className="relative">
          {results.persons.map((person) => (
            <div key={person.id} className="py-1.5 sm:py-0 sm:flex sm:items-center sm:h-9">
              <span
                className="block truncate text-xs mb-1 sm:mb-0 sm:absolute sm:-left-28 sm:w-24 sm:text-right"
                style={{ color: person.color }}
                title={person.name}
              >
                {person.name}
              </span>
              <div className="relative h-5 bg-void rounded sm:flex-1">
                {person.sightings.map((s, i) => {
                  const rect = intervalRect(s.start_s, s.end_s, duration);
                  return (
                    <button
                      key={i}
                      onClick={() => onSeek(s.start_s)}
                      title={`${person.name} ${formatTimecode(s.start_s)}–${formatTimecode(s.end_s)}`}
                      aria-label={`Jump to ${person.name} at ${formatTimecode(s.start_s)}`}
                      className="absolute top-0 h-full rounded-sm opacity-80 hover:opacity-100"
                      style={{
                        left: `${rect.leftPct}%`,
                        width: `${rect.widthPct}%`,
                        backgroundColor: person.color,
                      }}
                    />
                  );
                })}
              </div>
            </div>
          ))}
          <div
            className="absolute top-0 bottom-0 w-px bg-signal pointer-events-none"
            style={{ left: playheadLeft }}
          />
        </div>
      </div>
    </div>
  );
}
