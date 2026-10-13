import json
from collections.abc import Callable, Iterator

import openai
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

from .infrai_stream import stream_order_update
from .order_handoff import HandoffStage, OrderStreamRequest, select_handoff_stage

TokenStream = Callable[[OrderStreamRequest, HandoffStage], Iterator[str]]


def _event(name: str, payload: dict[str, str]) -> bytes:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n".encode()


def create_marketplace_service(streamer: TokenStream = stream_order_update) -> FastAPI:
    service = FastAPI(title="Marketplace order stream")

    @service.post("/orders/stream", response_class=StreamingResponse)
    def stream_order(request: OrderStreamRequest) -> StreamingResponse:
        stage = select_handoff_stage(request)
        tokens = streamer(request, stage)

        def events() -> Iterator[bytes]:
            yield _event("stage", {"order_id": request.order_id, "stage": stage.value})
            for token in tokens:
                yield _event("token", {"text": token})
            yield _event("complete", {"order_id": request.order_id, "stage": stage.value})

        return StreamingResponse(events(), media_type="text/event-stream")

    @service.exception_handler(openai.APIStatusError)
    async def upstream_rejection(_, exc: openai.APIStatusError) -> JSONResponse:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        return JSONResponse(
            status_code=status,
            content={"detail": "The model request was not accepted."},
        )

    return service


service = create_marketplace_service()


def run() -> None:
    uvicorn.run("marketplace_stream.marketplace_service:service", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
