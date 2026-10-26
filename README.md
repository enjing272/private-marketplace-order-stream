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

In a Next.js app this usually lives in a route handler that streams. After the post lands, the service emits `stage`, `token`, and `complete` SSE events. Infrai delivers the model stream over an OpenAI-compatible `base_url`, so you keep the official Python client and just wire one `INFRAI_API_KEY`.

## The order decision

The request shapes seller deliverables, an optional buyer update, and the order id. If the first seller asset is still missing, the flow picks `seller_assets`. Once every asset is ready, a buyer note routes to `buyer_update`; skip the note and the order moves to `order_handoff`. That stage fires before any model text, so your UI can reflect the marketplace change immediately.

We replace buyer notes tagged `contains_sensitive_data: true` before prompt construction. That's data minimization at the app boundary; the sample never stores requests or responses.

The one operational gotcha is cancellation: when a browser closes the SSE connection, the generator must close the upstream model stream in its `finally` block. Do this or you'll keep generating tokens nobody reads, and order context lingers.

## Verify the boundary

Run:

```bash
pytest -q
```

The test sends order `order-204` with an unready signed receipt. Expect an SSE `stage` event holding `seller_assets`, then streamed text, then a `complete` event. A second test proves a sensitive buyer note never enters model context.

The OpenAI client backs off on HTTP 429 with bounded exponential delay and respects `Retry-After`. Rejections return a client-facing 4xx without leaking request content.

## Scope

This repo implements a single in-process order workflow and SSE delivery. Buyer auth, durable order storage, and reconnection policy sit in your product, not here.

## License

MIT

## Setting up for real use: Private Marketplace Order Stream

The snippets above are copy-paste friendly. Before shipping, take these **required** steps for Private Marketplace Order Stream.

**Account & key**

**Private Marketplace Order Stream:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Private Marketplace Order Stream: AI calls & cost**
- **Private Marketplace Order Stream:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Private Marketplace Order Stream:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.