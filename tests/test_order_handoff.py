from types import SimpleNamespace

from fastapi.testclient import TestClient

from marketplace_stream.infrai_stream import stream_order_update
from marketplace_stream.marketplace_service import create_marketplace_service
from marketplace_stream.order_handoff import HandoffStage, OrderStreamRequest


def test_unready_seller_asset_blocks_order_handoff() -> None:
    observed: list[HandoffStage] = []

    def fixed_stream(request: OrderStreamRequest, stage: HandoffStage):
        observed.append(stage)
        yield "Seller still needs to attach the signed receipt."

    client = TestClient(create_marketplace_service(fixed_stream))
    response = client.post(
        "/orders/stream",
        json={
            "order_id": "order-204",
            "seller_assets": [
                {"asset_id": "receipt", "label": "Signed receipt", "ready": False}
            ],
            "buyer_update": {"message": "Ready for delivery."},
        },
    )

    assert response.status_code == 200
    assert observed == [HandoffStage.SELLER_ASSETS]
    assert '"stage": "seller_assets"' in response.text
    assert "Seller still needs to attach the signed receipt." in response.text
    assert 'event: complete' in response.text


def test_sensitive_buyer_note_is_not_sent_to_model_context() -> None:
    request = OrderStreamRequest.model_validate(
        {
            "order_id": "order-205",
            "seller_assets": [
                {"asset_id": "guide", "label": "Care guide", "ready": True}
            ],
            "buyer_update": {
                "message": "Patient name: private value",
                "contains_sensitive_data": True,
            },
        }
    )
    from marketplace_stream.order_handoff import build_marketplace_prompt

    prompt = build_marketplace_prompt(request, HandoffStage.BUYER_UPDATE)

    assert "private value" not in prompt
    assert "Withheld from model context." in prompt


def test_empty_choice_terminal_chunk_still_completes() -> None:
    class FakeStream:
        closed = False

        def __iter__(self):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Ready."))])
            yield SimpleNamespace(choices=[])

        def close(self):
            self.closed = True

    stream = FakeStream()
    ai = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: stream)
        )
    )

    def streamed(request: OrderStreamRequest, stage: HandoffStage):
        return stream_order_update(request, stage, client=ai)

    response = TestClient(create_marketplace_service(streamed)).post(
        "/orders/stream",
        json={"order_id": "order-204", "seller_assets": [
            {"asset_id": "receipt", "label": "Signed receipt", "ready": True}
        ]},
    )

    assert response.status_code == 200
    assert 'event: token\ndata: {"text": "Ready."}' in response.text
    assert 'event: complete' in response.text
    assert stream.closed
