import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api } from "../lib/api";
import type { JobDetail, Results } from "../lib/types";
import { SightingCard } from "./SightingCard";
import { Timeline } from "./Timeline";

export function ResultsView({ job }: { job: JobDetail }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const { data: results, isLoading } = useQuery({
    queryKey: ["results", job.id],
    queryFn: () => api.get<Results>(`/api/jobs/${job.id}/results`),
    staleTime: Infinity,
  });

  if (isLoading || !results) return <p className="text-dim">Loading results…</p>;

  function seek(seconds: number) {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = seconds;
    video.play().catch(() => {});
    video.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  const found = results.persons.filter((p) => p.sightings.length > 0);
  const notFound = results.persons.filter((p) => p.sightings.length === 0);

  return (
    <div className="max-w-5xl space-y-6">
      {/* Size heading + video + timeline to the viewport (minus the shell's
          padding and, below md, the top bar) so results open with the video
          AND the scrubber visible without scrolling. The timeline grows with
          person count, so the video flexes to whatever space remains. */}
      <div className="flex flex-col gap-4 h-[calc(100dvh-6rem)] md:h-[calc(100vh-4rem)]">
        <h1 className="display text-xl shrink-0">{job.video_filename}</h1>

        <video
          ref={videoRef}
          src={results.video.url}
          controls
          onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          className="w-full flex-1 min-h-0 object-contain rounded-lg border border-line bg-black"
        />

        <div className="shrink-0">
          <Timeline results={results} currentTime={currentTime} onSeek={seek} />
        </div>
      </div>

      {notFound.length > 0 && (
        <div className="bg-panel border border-line rounded-lg p-4 text-sm text-dim">
          {notFound.map((p) => (
            <p key={p.id}>
              No sightings of <span style={{ color: p.color }}>{p.name}</span>. They may
              not appear in this footage — or try clearer, front-facing reference photos.
            </p>
          ))}
        </div>
      )}

      {found.map((person) => (
        <section key={person.id}>
          <h2 className="text-sm mb-3">
            <span style={{ color: person.color }}>{person.name}</span>{" "}
            <span className="tc text-dim">
              · {person.sightings.length} sighting{person.sightings.length === 1 ? "" : "s"}
            </span>
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {person.sightings.map((s, i) => (
              <SightingCard key={i} person={person} sighting={s} onSeek={seek} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
