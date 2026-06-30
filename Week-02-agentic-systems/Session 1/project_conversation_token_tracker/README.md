# Conversation Cost Tracker

A CLI and FastAPI tool that simulates a growing chat conversation and
tracks the **cumulative real-world cost** of that conversation, turn by
turn -- making visible the fact that, because LLM APIs are stateless,
the entire conversation history must be resent as input on every single
user turn.

Built as part of Week 2 (NLP for LLM Prep -- Tokenization) of an
Agentic AI Systems course, as a companion to the `TokenCostEstimator`
project. Standalone -- no shared code between the two.

## The core idea: turns vs. calls

A **turn** is one message in the conversation (one entry in the
`messages` list). A **call** is one real request to an LLM API. These
are not the same thing, and the relationship between them is the whole
point of this tool:

```
Turn 1 (user)      -> triggers Call 1
                       Call 1 input  = turn 1
                       Call 1 output = turn 2 (the assistant's reply)

Turn 2 (assistant) -> NOT a new call. It's the OUTPUT of Call 1 --
                       generated for free as part of the request
                       turn 1 already made.

Turn 3 (user)      -> triggers Call 2
                       Call 2 input  = turn 1 + turn 2 + turn 3
                       (the WHOLE history so far, resent again)
```

Only user (and system) turns trigger a new call, and every such call
must resend the entire conversation so far as input -- because the
server has no memory between requests. Assistant turns never trigger a
call on their own; they're the result of the call the preceding user
turn already made.

## How cost is calculated

Each turn is billed according to which side of the conversation it
came from:

| Turn role | What it represents | Billed as |
|---|---|---|
| `user` / `system` | Triggers a new API call. Its cost = (everything sent before it + itself), since the whole history is resent | `input_price_per_token` |
| `assistant` | The output of the call the preceding user turn triggered. Only its own new tokens are billed -- it is not "resent" the way history is | `output_price_per_token` |

`cumulative_cost` is the running sum of each individual call's real
cost -- i.e. what you would actually have spent if this conversation
happened as a real series of separate API calls, one per user turn.
`cumulative_tokens` is a separate figure: the total number of tokens
that have ever appeared in the conversation, used for tracking context
window usage (which counts all tokens regardless of who's paying for
them).

## What it does

Given a conversation (a list of `{role, content}` messages), it:
- estimates tokens per message using a simple `len(text) // 4` heuristic
- computes, per turn, whether that turn triggers a call and at which rate it's billed
- tracks the running real cost across all calls the conversation would have triggered
- tracks cumulative tokens against a context window limit, and warns when it's getting close

## Project structure

```
project_conversation_tracker/
├── tracker.py               # ConversationCostTracker -- the core class (generator-based)
├── cli.py                   # argparse CLI, reads a conversation from a JSON file
├── api.py                   # FastAPI app exposing /track
└── sample_conversation.json # example conversation for testing
```

## Setup

```bash
pip install fastapi uvicorn pydantic
```

## Running the CLI

Conversation files are plain JSON, shaped like:
```json
[
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi there!"}
]
```

```bash
python cli.py sample_conversation.json
python cli.py sample_conversation.json --price-per-token 0.000003
python cli.py sample_conversation.json --output-price-per-token 0.000015
python cli.py sample_conversation.json --context-limit 200000
```

Example output:
```
ConversationCostTracker(turns=6, total_tokens=242)

Turn  Role        New tok   Cumulative tok  Cumulative cost
----------------------------------------------------------------
1     user        14        14              $0.000042
2     assistant   45        59              $0.000717
3     user        11        70              $0.000927
4     assistant   61        131             $0.001842
5     user        13        144             $0.002274
6     assistant   98        242             $0.003744

Total tokens so far : 242
Total cost so far   : $0.003744
Context window used : 0.1210%
```

Notice assistant turns add noticeably more to the running cost than
user turns of similar length -- this reflects the output rate being
priced higher than the input rate, exactly as it is with real LLM
APIs.

## Running the API

```bash
uvicorn api:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/track \
  -H "Content-Type: application/json" \
  -d '{
        "messages": [
          {"role": "user", "content": "Hello!"},
          {"role": "assistant", "content": "Hi there!"}
        ],
        "price_per_token": 0.000003,
        "output_price_per_token": 0.000015
      }'
```

## Why a generator (`cost_per_turn`)

`ConversationCostTracker.cost_per_turn()` is a generator -- it yields
one `TurnCost` at a time rather than building the whole list upfront.
This means a caller can stop early (e.g. as soon as it detects costs
are climbing too fast) without the tracker doing unnecessary work for
turns that will never be inspected.

## Token estimation accuracy

This project intentionally uses the simple `len(text) // 4`
approximation rather than a real tokenizer library. The point of this
tool is the *shape of the cost curve* across a conversation, not exact
per-token precision -- see the `TokenCostEstimator` project for
provider-accurate token counts on a single piece of text.

## What this is not

This does not call any real LLM API and does not measure actual
historical spend. It models, given a conversation you provide, what
that conversation *would* have cost across the separate real API calls
it implies -- correctly split between input and output pricing -- not
a live usage/billing tracker against an account you've actually used.
