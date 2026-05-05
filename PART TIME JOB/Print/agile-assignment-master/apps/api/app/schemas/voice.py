from pydantic import BaseModel


class VoiceSessionRequest(BaseModel):
    session_id: str | None = None
    locale: str | None = None


class VoiceSessionResponse(BaseModel):
    status: str
    message: str


class VoiceTranscriptionResponse(BaseModel):
    text: str
