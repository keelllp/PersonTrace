import { formatTimecode } from "../lib/format";
import type { ResultPerson, Sighting } from "../lib/types";

interface SightingCardProps {
  person: ResultPerson;
  sighting: Sighting;
  onSeek: (seconds: number) => void;
}

export function SightingCard({ person, sighting, onSeek }: SightingCardProps) {
  return (
    <figure className="bg-panel border border-line rounded-lg overflow-hidden hover:border-dim/60 transition-colors duration-150">
      <button
        onClick={() => onSeek(sighting.start_s)}
        className="block w-full relative"
        aria-label={`Jump to ${person.name} at ${formatTimecode(sighting.start_s)}`}
      >
        <img
          src={sighting.thumbnail_url}
          alt={`${person.name} at ${formatTimecode(sighting.start_s)}`}
          className="w-full aspect-video object-cover"
          loading="lazy"
        />
        <span className="tc absolute bottom-2 left-2 bg-void/85 text-xs px-1.5 py-0.5 rounded">
          {formatTimecode(sighting.start_s)}–{formatTimecode(sighting.end_s)}
        </span>
      </button>
      <figcaption className="p-3 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium truncate" style={{ color: person.color }}>
            {person.name}
          </span>
          <span className="tc text-[11px] text-dim border border-line rounded-full px-2 py-0.5">
            {sighting.match_type}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1 bg-void rounded-full overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.round(sighting.confidence * 100)}%`,
                backgroundColor: person.color,
              }}
            />
          </div>
          <span className="tc text-xs text-dim">
            {Math.round(sighting.confidence * 100)}%
          </span>
        </div>
      </figcaption>
    </figure>
  );
}
