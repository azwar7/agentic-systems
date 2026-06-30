"""
api.py

FastAPI layer exposing the conversation cost tracker over HTTP.

Run with:
    uvicorn api:app --reload

Then visit:
    http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from pydantic import BaseModel

from tracker import ConversationCostTracker, Message, TurnCost

app = FastAPI(
    title="Conversation Cost Tracker API",
    description="Tracks cumulative token cost across a growing conversation.",
)


class TrackRequest(BaseModel):
    messages: list[Message]
    price_per_token: float = 3.00 / 1_000_000          # input price per token
    output_price_per_token: float = 15.00 / 1_000_000  # output price per token
    context_limit: int = 200_000
    use_bpe: bool = False   # False = approximate_tokens(), True = real BPE via tiktoken


class TrackResponse(BaseModel):
    turns: list[TurnCost]
    total_tokens: int
    total_cost: float
    context_usage_percent: float
    near_context_limit: bool


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Conversation Cost Tracker API is running. See /docs for usage."}


@app.post("/track", response_model=TrackResponse)
def track_conversation(request: TrackRequest) -> TrackResponse:
    tracker = ConversationCostTracker(
        input_price_per_token=request.price_per_token,
        output_price_per_token=request.output_price_per_token,
        context_window_limit=request.context_limit,
        use_bpe=request.use_bpe,
    )
    tracker.messages = request.messages

    turns = list(tracker.cost_per_turn())

    return TrackResponse(
        turns=turns,
        total_tokens=tracker.total_tokens_so_far(),
        total_cost=tracker.total_cost_so_far(),
        context_usage_percent=tracker.context_usage_percent(),
        near_context_limit=tracker.is_near_context_limit(),
    )
