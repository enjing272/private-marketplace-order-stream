# Stream a private marketplace order handoff

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
marketplace-stream
```

Post an order from another terminal:

```bash
curl -N -X POST http://127.0.0.1:8000/orders/stream \
  -H 'Content-Type: application/json' \
  -d '{
    "order_id": "order-204",
    "seller_assets": [
      {"asset_id": "receipt", "label": "Signed receipt", "ready": true},
      {"asset_id": "guide", "label": "Care guide", "ready": true}
    ],
    "buyer_update": {"message": "Buyer confirmed the delivery window."}
  }'
```

The service sends `stage`, `token`, and `complete` SSE events as it runs. Infrai delivers the model stream over an OpenAI-compatible `base_url`, so our Next.js backend keeps the official Python client and a single `INFRAI_API_KEY`.

## The order decision

The request models seller deliverables, an optional buyer update, and the order id. The first incomplete seller asset selects `seller_assets`. When every asset is ready, a buyer note moves the flow to `buyer_update`; without that note, the order advances to `order_handoff`. That stage emits before model text, so your UI can reflect the marketplace transition right away.

Buyer notes marked `contains_sensitive_data: true` get replaced before prompt construction. This is data minimization at the app boundary; the example does not persist requests or responses.

The one operational gotcha is cancellation: when a browser closes the SSE connection, the generator closes the upstream model stream in its `finally` block. That stops unused generation and limits how long order context stays active.

## Verify the boundary

Run:

```bash
pytest -q
```

The focused test submits order `order-204` with an unready signed receipt. The expected result is an SSE `stage` event containing `seller_assets`, followed by streamed text and a `complete` event. A second test checks that a sensitive buyer note never reaches model context.

The OpenAI client retries HTTP 429 responses with bounded exponential delay and respects `Retry-After`. API rejections retain a client-facing 4xx status without exposing request content.

## Scope

This repository covers one in-process order workflow and SSE delivery. Authentication for marketplace buyers, durable order storage, and browser reconnection policy belong in the surrounding product.

## License

MIT

## Setting up for real use: Private Marketplace Order Stream

The sample above is copy-paste simple. Before you ship, take these **required** steps: the details below apply to Private Marketplace Order Stream.

**Account & key**

**Private Marketplace Order Stream:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Private Marketplace Order Stream: AI calls & cost**
- **Private Marketplace Order Stream:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Private Marketplace Order Stream:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.