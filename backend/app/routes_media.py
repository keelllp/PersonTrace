import mimetypes
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .models import Job
from .routes_jobs import get_owned_job
from .storage import job_key

router = APIRouter(prefix="/api/media", tags=["media"])

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)$")
_SUFFIX_RANGE_RE = re.compile(r"bytes=-(\d+)$")


def _parse_range(header: str, size: int) -> tuple[int, int] | None:
    """Return (start, end) for a supported satisfiable range.

    Returns None when the header is unsupported/malformed (caller serves 200).
    Raises HTTPException(416) when the range is parseable but unsatisfiable.
    """
    header = header.strip()
    unsatisfiable = HTTPException(
        status_code=416,
        detail="Range not satisfiable",
        headers={"Content-Range": f"bytes */{size}"},
    )
    m = _RANGE_RE.match(header)
    if m:
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start >= size or start > end:
            raise unsatisfiable
        return start, end
    m = _SUFFIX_RANGE_RE.match(header)
    if m:
        n = int(m.group(1))
        if n == 0:
            raise unsatisfiable
        return max(0, size - n), size - 1
    return None


@router.get("/{job_id}/{path:path}")
def get_media(
    path: str,
    request: Request,
    job: Job = Depends(get_owned_job),
):
    storage = request.app.state.storage
    key = job_key(job.user_id, job.id, path)
    try:
        size = storage.head(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Media not found")

    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    base_headers = {"Accept-Ranges": "bytes"}

    range_header = request.headers.get("range")
    byte_range = _parse_range(range_header, size) if range_header else None
    if byte_range is not None:
        start, end = byte_range
        return StreamingResponse(
            storage.stream(key, start=start, end=end),
            status_code=206,
            media_type=content_type,
            headers={
                **base_headers,
                "Content-Range": f"bytes {start}-{end}/{size}",
                "Content-Length": str(end - start + 1),
            },
        )

    return StreamingResponse(
        storage.stream(key),
        media_type=content_type,
        headers={**base_headers, "Content-Length": str(size)},
    )
