import type { JobStatus } from "../lib/types";

const STYLES: Record<JobStatus, string> = {
  queued: "text-dim border-line",
  processing: "text-signal border-signal/40",
  done: "text-ok border-ok/40",
  failed: "text-danger border-danger/40",
  cancelled: "text-dim border-line",
};

export function StatusChip({ status, stage }: { status: JobStatus; stage?: string | null }) {
  const label = status === "processing" && stage ? `${status} · ${stage}` : status;
  return (
    <span className={`tc text-xs border rounded-full px-2 py-0.5 ${STYLES[status]}`}>
      {label}
    </span>
  );
}
