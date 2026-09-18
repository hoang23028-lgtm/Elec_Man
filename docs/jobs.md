# Processing jobs

Phase 4 uses PostgreSQL as the queue. The worker claims one eligible job in a transaction with `FOR UPDATE SKIP LOCKED`, so a second worker can be added without simultaneous claims. Crashed `PROCESSING` jobs are recovered after the configured timeout; failures retry with exponential backoff until `MAX_RETRY_COUNT` is reached.

The current processor is `OCR_BASELINE`. It records quality, OCR, detected regions, confidence, and model version while leaving every output in human review. It is a pretrained bootstrap for collecting verified labels, not a production-trained electricity-meter model.

The `migrate` Compose service applies all Alembic migrations before backend and worker start, eliminating queue-table startup races.
