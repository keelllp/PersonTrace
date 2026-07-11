import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { JobDetail } from "../lib/types";

const STAGES = ["probe", "gallery", "detect", "embed", "match", "render"] as const;

export function ProcessingView({ job }: { job: JobDetail }) {
  const queryClient = useQueryClient();
  const cancel = useMutation({
    mutationFn: () => api.post(`/api/jobs/${job.id}/cancel`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["job", job.id] }),
  });
  const currentIndex = job.stage ? STAGES.indexOf(job.stage as (typeof STAGES)[number]) : -1;

  return (
    <div className="max-w-xl space-y-8">
      <div>
        <h1 className="display text-xl">{job.video_filename}</h1>
        <p className="text-dim text-sm mt-1">
          {job.status === "queued"
            ? "Waiting for the analysis worker…"
            : "Analyzing footage — this runs on CPU and can take a few minutes."}
        </p>
      </div>

      <ol className="flex gap-2">
        {STAGES.map((stage, i) => (
          <li key={stage} className="flex-1">
            <div
              className={`h-1.5 rounded-full ${
                i < currentIndex
                  ? "bg-signal"
                  : i === currentIndex
                    ? "bg-signal/40 scanning"
                    : "bg-line"
              }`}
            />
            <span
              className={`tc text-[11px] mt-1 block ${
                i === currentIndex ? "text-signal" : "text-dim"
              }`}
            >
              {stage}
            </span>
          </li>
        ))}
      </ol>

      <p className="tc text-3xl">
        {Math.round(job.progress_pct)}
        <span className="text-dim text-lg">%</span>
      </p>

      <button
        onClick={() => cancel.mutate()}
        disabled={cancel.isPending || cancel.isSuccess}
        className="rounded-md border border-line px-4 py-2 text-sm text-dim hover:text-danger hover:border-danger/50 disabled:opacity-50"
      >
        {cancel.isSuccess ? "Cancelling…" : "Cancel trace"}
      </button>
      {cancel.isError && (
        <p className="text-dim text-sm">
          Couldn't cancel — the trace may have just finished.
        </p>
      )}
    </div>
  );
}
