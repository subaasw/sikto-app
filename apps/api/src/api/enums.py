from enum import StrEnum


class JobStatus(StrEnum):
    queued = "queued"
    loading = "loading"
    embedding = "embedding"
    planning = "planning"
    narrating = "narrating"
    rendering = "rendering"
    done = "done"
    failed = "failed"
