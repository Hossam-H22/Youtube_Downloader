"""In-memory background-job registry for the GUI.

Each download runs on a daemon thread and reports progress by pushing events
into its job's queue. The SSE endpoint drains that queue and streams the events
to the browser. Kept deliberately simple: single-process, local app.
"""

import json
import queue
import threading
import uuid


class Job:
    """A single running download and its progress event queue."""

    def __init__(self) -> None:
        self.id = uuid.uuid4().hex
        self.events: "queue.Queue" = queue.Queue()

    def emit(self, **event) -> None:
        """Push a progress event (a dict) to the stream."""
        self.events.put(event)

    def close(self) -> None:
        """Signal the end of the stream."""
        self.events.put(None)


_jobs: "dict[str, Job]" = {}


def create_job() -> Job:
    job = Job()
    _jobs[job.id] = job
    return job


def get_job(job_id: str):
    return _jobs.get(job_id)


def run_in_thread(job: Job, target) -> None:
    """Run ``target(job)`` on a daemon thread; emit any error and always close."""
    def _run() -> None:
        try:
            target(job)
        except Exception as e:  # noqa: BLE001 - surface any failure to the UI
            job.emit(type='error', message=str(e))
        finally:
            job.close()

    threading.Thread(target=_run, daemon=True).start()


def sse_stream(job: Job):
    """Yield Server-Sent-Events strings until the job closes, then forget it."""
    try:
        while True:
            event = job.events.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
    finally:
        _jobs.pop(job.id, None)
