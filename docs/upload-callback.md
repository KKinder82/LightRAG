# Upload completion callback

`POST /documents/upload` accepts an optional multipart field `callback_url`.
Existing callers can omit it. The upload response remains unchanged and returns
`track_id` immediately; processing and callback delivery run in the background.

```bash
curl -X POST 'http://localhost:9621/documents/upload' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -F 'file=@document.pdf' \
  -F 'callback_url=https://caller.example/hooks/lightrag'
```

The URL must use HTTP or HTTPS. No separate callback authentication parameters
are required, and URL username/password fields are not checked or rejected.
The callback sends a JSON POST after text/vector indexing and knowledge graph
processing have finished. With `fast_index=true`, knowledge graph processing is
skipped and the callback follows text/vector indexing. Parsing/indexing failures
and knowledge graph failures also generate a notification. A failed knowledge
graph does not remove the successfully indexed text vectors.

Example success payload:

```json
{
  "event": "document.processing_completed",
  "event_id": "upload_20261009_example",
  "track_id": "upload_20261009_example",
  "filename": "document.pdf",
  "status": "processed",
  "documents": [
    {
      "doc_id": "doc-example",
      "file_path": "document.pdf",
      "status": "processed",
      "kg_status": "completed",
      "chunks_count": 12,
      "error": null
    }
  ],
  "error": null
}
```

The top-level `status` is `processed` or `failed`. Each document reports its own
status, KG status (`completed`, `skipped`, or `failed`), and error. Errors before
document creation appear in the top-level `error`; `documents` may then be empty.
Use `track_id` to correlate the notification with the original upload response.

The receiver should return any HTTP 2xx response; no JSON response is required.
Delivery has a 10-second HTTP timeout and at most three attempts, with 1-second
and 2-second waits between attempts. Redirects are not followed. Requests bypass
environment proxy settings. Each attempt uses the same `event_id` and
`Idempotency-Key` header, so the receiver should deduplicate repeated delivery.
Exhausted delivery is logged without changing document processing results.

In WebUI, open the document panel's processing status dialog and select
**Callback Logs** to view sending, failed attempts, retry delays, successful
delivery, and exhausted delivery. Entries include a timestamp, `track_id`,
filename, processing status, attempt number, HTTP status or exception type, and
request duration. They also appear in pipeline history and server logs. Callback
URLs and response bodies are not logged. WebUI entries share the existing
workspace pipeline history lifecycle and are not a persistent audit log.

Callbacks currently use in-process background tasks. They are not persisted or
replayed after service termination/restart, and exhausted deliveries are not
stored in a retry queue. Callers can recover status with
`GET /documents/track_status/{track_id}`. This is best-effort delivery rather than
a durable notification guarantee.
