from pydantic import BaseModel
from typing import Literal


# Client -> Server

class ChatMessage(BaseModel):
    type: Literal["chat"]
    text: str


class InterruptMessage(BaseModel):
    type: Literal["interrupt"]


class PongMessage(BaseModel):
    type: Literal["pong"]


class IdleResponseMessage(BaseModel):
    type: Literal["idle_response"]


# Server -> Client

class ConnectedMessage(BaseModel):
    type: Literal["connected"] = "connected"
    session_id: str | None = None


class AssistantDeltaMessage(BaseModel):
    type: Literal["assistant_delta"] = "assistant_delta"
    text: str


class AssistantTextMessage(BaseModel):
    type: Literal["assistant_text"] = "assistant_text"
    text: str


class TurnCompleteMessage(BaseModel):
    type: Literal["turn_complete"] = "turn_complete"
    session_id: str
    cost_usd: float | None = None


class SessionRecoveredMessage(BaseModel):
    type: Literal["session_recovered"] = "session_recovered"
    message: str


class IdleWarningMessage(BaseModel):
    type: Literal["idle_warning"] = "idle_warning"
    message: str


class SessionExpiredMessage(BaseModel):
    type: Literal["session_expired"] = "session_expired"


class SessionTakeoverMessage(BaseModel):
    type: Literal["session_takeover"] = "session_takeover"


class PingMessage(BaseModel):
    type: Literal["ping"] = "ping"


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
