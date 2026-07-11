import type { PersonSummary } from "../lib/types";

export function PersonAvatars({ persons }: { persons: PersonSummary[] }) {
  return (
    <div className="flex -space-x-2">
      {persons.map((p) =>
        p.photo_url ? (
          <img
            key={p.id}
            src={p.photo_url}
            alt={p.name}
            title={p.name}
            className="w-8 h-8 rounded-full object-cover border-2"
            style={{ borderColor: p.color }}
          />
        ) : (
          <span
            key={p.id}
            title={p.name}
            className="w-8 h-8 rounded-full grid place-items-center text-xs font-semibold border-2 bg-panel2"
            style={{ borderColor: p.color, color: p.color }}
          >
            {p.name.slice(0, 1).toUpperCase()}
          </span>
        ),
      )}
    </div>
  );
}
