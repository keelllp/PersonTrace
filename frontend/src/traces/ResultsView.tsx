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
      <h1 className="display text-xl">{job.video_filename}</h1>

      <video
        ref={videoRef}
        src={results.video.url}
        controls
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        className="w-full rounded-lg border border-line bg-black"
      />

      <Timeline results={results} currentTime={currentTime} onSeek={seek} />

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
