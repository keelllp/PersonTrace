import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ApiError, api } from "../lib/api";
import { formatDate, formatTimecode } from "../lib/format";
import type { JobListItem } from "../lib/types";
import { PersonAvatars } from "./PersonAvatars";
import { StatusChip } from "./StatusChip";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const { data: jobs, isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.get<JobListItem[]>("/api/jobs"),
    refetchInterval: (query) =>
      query.state.data?.some((j) => j.status === "queued" || j.status === "processing")
        ? 2500
        : false,
  });

  const deleteJob = useMutation({
    mutationFn: (id: string) => api.del(`/api/jobs/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  if (isLoading) return <p className="text-dim">Loading traces…</p>;

  if (!jobs?.length) {
    return (
      <div className="max-w-md mx-auto mt-24 text-center space-y-4">
        <h1 className="display text-xl">No traces yet</h1>
        <p className="text-dim">
          Upload footage and reference photos, and PersonTrace will find every
          appearance — with timecodes and annotated screenshots.
        </p>
        <Link
          to="/new"
          className="inline-block rounded-md bg-signal text-void font-semibold px-5 py-2"
        >
          Start your first trace
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <h1 className="display text-xl mb-6">Traces</h1>
      {deleteJob.isError && (
        <p className="text-danger text-sm mb-4">
          Couldn't delete the trace
          {deleteJob.error instanceof ApiError ? `: ${deleteJob.error.message}` : " — try again."}
        </p>
      )}
      <ul className="space-y-3">
        {jobs.map((job) => (
          <li
            key={job.id}
            className="bg-panel border border-line rounded-lg p-4 flex items-center gap-4 hover:border-dim/50 transition-colors duration-150"
          >
            <PersonAvatars persons={job.persons} />
            <div className="min-w-0 flex-1">
              <Link
                to={`/traces/${job.id}`}
                className="font-medium truncate block hover:text-signal"
              >
                {job.video_filename}
              </Link>
              <p className="text-xs text-dim tc mt-0.5">
                {formatDate(job.created_at)}
                {job.duration_s != null && <> · {formatTimecode(job.duration_s)}</>}
                {" · "}
                {job.persons.map((p) => p.name).join(", ")}
              </p>
            </div>
            {(job.status === "processing" || job.status === "queued") && (
              <span className="tc text-xs text-dim">{Math.round(job.progress_pct)}%</span>
            )}
            <StatusChip status={job.status} stage={job.stage} />
            <button
              onClick={() => {
                if (confirm(`Delete trace "${job.video_filename}"? This removes its video, photos, and results.`))
                  deleteJob.mutate(job.id);
              }}
              disabled={job.status === "processing"}
              title={
                job.status === "processing"
                  ? "Cancel the trace before deleting it"
                  : undefined
              }
              className="text-dim hover:text-danger text-sm disabled:opacity-40 disabled:hover:text-dim"
              aria-label={`Delete trace ${job.video_filename}`}
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
