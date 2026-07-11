export interface User {
  id: string;
  email: string;
}

export interface PersonSummary {
  id: string;
  name: string;
  color: string;
  photo_url: string | null;
}

export type JobStatus = "queued" | "processing" | "done" | "failed" | "cancelled";

export interface JobListItem {
  id: string;
  video_filename: string;
  status: JobStatus;
  stage: string | null;
  progress_pct: number;
  created_at: string;
  duration_s: number | null;
  persons: PersonSummary[];
}

export interface JobDetail {
  id: string;
  video_filename: string;
  status: JobStatus;
  stage: string | null;
  progress_pct: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  duration_s: number | null;
}

export interface Sighting {
  start_s: number;
  end_s: number;
  confidence: number;
  match_type: "face" | "body";
  screenshot_url: string;
  thumbnail_url: string;
  box: { x: number; y: number; w: number; h: number; frame_s: number };
}

export interface ResultPerson {
  id: string;
  name: string;
  color: string;
  photo_urls: string[];
  sightings: Sighting[];
}

export interface Results {
  video: {
    duration_s: number | null;
    fps: number | null;
    width: number | null;
    height: number | null;
    url: string;
  };
  persons: ResultPerson[];
}

export interface CreateJobResponse {
  job_id: string;
  warnings: string[];
}
