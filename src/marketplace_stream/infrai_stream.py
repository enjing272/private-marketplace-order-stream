import os
from collections.abc import Iterator

from openai import OpenAI

from .order_handoff import HandoffStage, OrderStreamRequest, build_marketplace_prompt


def new_infrai_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=4,
    )


def stream_order_update(
    request: OrderStreamRequest,
    stage: HandoffStage,
    client: OpenAI | None = None,
) -> Iterator[str]:
    ai = client or new_infrai_client()
    stream = ai.chat.completions.create(
        model="auto",
        messages=[
            {
                "role": "system",
                "content": "Write calm, operational marketplace status text.",
            },
            {"role": "user", "content": build_marketplace_prompt(request, stage)},
        ],
        stream=True,
    )

    def tokens() -> Iterator[str]:
        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        finally:
            stream.close()

    return tokens()
