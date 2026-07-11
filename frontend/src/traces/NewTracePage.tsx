import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../lib/api";
import type { CreateJobResponse } from "../lib/types";

const VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"];
const MAX_VIDEO_MB = 500;
// Keep in sync with PERSON_COLORS in backend/app/routes_jobs.py
const PERSON_COLORS = ["#e05252", "#4f9cf0", "#4fc07a", "#e0a34f", "#a06fe0", "#e05c9c"];

interface PersonDraft {
  name: string;
  photos: File[];
}

export function NewTracePage() {
  const navigate = useNavigate();
  const [video, setVideo] = useState<File | null>(null);
  const [persons, setPersons] = useState<PersonDraft[]>([{ name: "", photos: [] }]);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[] | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const videoInput = useRef<HTMLInputElement>(null);

  const submit = useMutation({
    mutationFn: (form: FormData) => api.postForm<CreateJobResponse>("/api/jobs", form),
  });

  function validate(): string | null {
    if (!video) return "Add a video to search.";
    if (!VIDEO_EXTENSIONS.some((ext) => video.name.toLowerCase().endsWith(ext)))
      return `Unsupported video type. Use ${VIDEO_EXTENSIONS.join(", ")}.`;
    if (video.size > MAX_VIDEO_MB * 1024 * 1024)
      return `Video is over the ${MAX_VIDEO_MB} MB limit.`;
    for (const [i, p] of persons.entries()) {
      if (!p.name.trim()) return `Person ${i + 1} needs a name.`;
      if (p.photos.length < 1 || p.photos.length > 3)
        return `${p.name.trim() || `Person ${i + 1}`} needs 1–3 photos.`;
    }
    return null;
  }

  async function start() {
    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    const form = new FormData();
    form.append("video", video!);
    form.append("persons", JSON.stringify(persons.map((p) => ({ name: p.name.trim() }))));
    persons.forEach((p, i) => p.photos.forEach((f) => form.append(`photos_${i}`, f)));
    try {
      const result = await submit.mutateAsync(form);
      if (result.warnings.length) {
        setWarnings(result.warnings);
        setCreatedId(result.job_id);
      } else {
        navigate(`/traces/${result.job_id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed — try again.");
    }
  }

  function updatePerson(index: number, patch: Partial<PersonDraft>) {
    setPersons((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }

  if (warnings && createdId) {
    return (
      <div className="max-w-lg space-y-4">
        <h1 className="display text-xl">Heads up</h1>
        <ul className="bg-panel border border-line rounded-lg p-4 space-y-2 text-sm">
          {warnings.map((w) => (
            <li key={w} className="text-dim">
              ⚠ {w} — matching for them may rely on body appearance only.
            </li>
          ))}
        </ul>
        <button
          onClick={() => navigate(`/traces/${createdId}`)}
          className="rounded-md bg-signal text-void font-semibold px-5 py-2"
        >
          Continue to trace
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-8">
      <h1 className="display text-xl">New trace</h1>

      <section>
        <h2 className="text-sm text-dim mb-2">Footage</h2>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files[0];
            if (file) setVideo(file);
          }}
          onClick={() => videoInput.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && videoInput.current?.click()}
          className={`rounded-lg border-2 border-dashed p-10 text-center cursor-pointer transition-colors ${
            dragging ? "border-signal bg-panel2" : "border-line bg-panel hover:border-dim"
          }`}
        >
          {video ? (
            <p>
              <span className="font-medium">{video.name}</span>{" "}
              <span className="tc text-dim text-sm">
                ({(video.size / 1024 / 1024).toFixed(1)} MB)
              </span>
            </p>
          ) : (
            <p className="text-dim">Drop a video here, or click to choose one</p>
          )}
          <input
            ref={videoInput}
            type="file"
            accept={VIDEO_EXTENSIONS.join(",")}
            hidden
            onChange={(e) => setVideo(e.target.files?.[0] ?? null)}
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm text-dim">People to find</h2>
        {persons.map((person, i) => (
          <div
            key={i}
            className="bg-panel border border-line rounded-lg p-4 space-y-3"
            style={{ borderLeftWidth: 3, borderLeftColor: PERSON_COLORS[i % PERSON_COLORS.length] }}
          >
            <div className="flex items-center gap-3">
              <input
                value={person.name}
                onChange={(e) => updatePerson(i, { name: e.target.value })}
                placeholder={`Person ${i + 1} name`}
                className="flex-1 rounded-md bg-void border border-line px-3 py-2"
              />
              {persons.length > 1 && (
                <button
                  onClick={() => setPersons((prev) => prev.filter((_, j) => j !== i))}
                  className="text-dim hover:text-danger text-sm"
                >
                  Remove
                </button>
              )}
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              {person.photos.map((photo, j) => (
                <div key={j} className="relative">
                  <img
                    src={URL.createObjectURL(photo)}
                    alt={`${person.name || "person"} photo ${j + 1}`}
                    className="w-16 h-16 rounded object-cover border border-line"
                  />
                  <button
                    onClick={() =>
                      updatePerson(i, { photos: person.photos.filter((_, k) => k !== j) })
                    }
                    aria-label="Remove photo"
                    className="absolute -top-2 -right-2 bg-panel2 border border-line rounded-full w-5 h-5 text-xs grid place-items-center hover:text-danger"
                  >
                    ×
                  </button>
                </div>
              ))}
              {person.photos.length < 3 && (
                <label className="w-16 h-16 rounded border border-dashed border-line grid place-items-center text-dim cursor-pointer hover:border-dim text-2xl">
                  +
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    hidden
                    multiple
                    onChange={(e) => {
                      const files = Array.from(e.target.files ?? []);
                      updatePerson(i, {
                        photos: [...person.photos, ...files].slice(0, 3),
                      });
                      e.target.value = "";
                    }}
                  />
                </label>
              )}
              <span className="text-xs text-dim">1–3 clear photos; faces work best</span>
            </div>
          </div>
        ))}
        {persons.length < 6 && (
          <button
            onClick={() => setPersons((prev) => [...prev, { name: "", photos: [] }])}
            className="text-sm text-signal hover:underline"
          >
            + Add another person
          </button>
        )}
      </section>

      {error && <p className="text-danger text-sm">{error}</p>}

      <button
        onClick={start}
        disabled={submit.isPending}
        className="rounded-md bg-signal text-void font-semibold px-6 py-2.5 disabled:opacity-50"
      >
        {submit.isPending ? "Uploading…" : "Start trace"}
      </button>
    </div>
  );
}
