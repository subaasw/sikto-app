from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="sikto-tts")


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "default"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/synthesize")
def synthesize(body: SynthesizeRequest) -> dict[str, object]:
    return {"audio_b64": "", "duration_ms": max(1, len(body.text)) * 50}
