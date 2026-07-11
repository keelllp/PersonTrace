import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { JobDetail } from "../lib/types";
import { ProcessingView } from "./ProcessingView";
import { ResultsView } from "./ResultsView";

export function TracePage() {
  const { id } = useParams<{ id: string }>();
  const { data: job, isLoading } = useQuery({
    queryKey: ["job", id],
    queryFn: () => api.get<JobDetail>(`/api/jobs/${id}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "processing" ? 1500 : false;
    },
  });

  if (isLoading) return <p className="text-dim">Loading trace…</p>;
  if (!job) return <p className="text-dim">Trace not found.</p>;

  if (job.status === "queued" || job.status === "processing")
    return <ProcessingView job={job} />;
  if (job.status === "done") return <ResultsView job={job} />;

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="display text-xl">{job.video_filename}</h1>
      {job.status === "failed" ? (
        <>
          <p className="text-danger">This trace failed: {job.error ?? "unknown error"}</p>
          <p className="text-dim text-sm">
            Check the video plays locally, then start a new trace with it.
          </p>
        </>
      ) : (
        <p className="text-dim">This trace was cancelled before it finished.</p>
      )}
      <Link to="/new" className="inline-block text-signal hover:underline">
        Start a new trace
      </Link>
    </div>
  );
}
