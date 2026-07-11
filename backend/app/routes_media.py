import mimetypes
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .models import Job
from .routes_jobs import get_owned_job
from .storage import job_key

router = APIRouter(prefix="/api/media", tags=["media"])

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)$")


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
    if range_header:
        m = _RANGE_RE.match(range_header.strip())
        if m is None:
            raise HTTPException(status_code=416, detail="Malformed Range header")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start >= size or start > end:
            raise HTTPException(
                status_code=416,
                detail="Range not satisfiable",
                headers={"Content-Range": f"bytes */{size}"},
            )
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
