# Processing jobs

Phase 4 uses PostgreSQL as the queue. The worker claims one eligible job in a transaction with `FOR UPDATE SKIP LOCKED`, so a second worker can be added without simultaneous claims. Crashed `PROCESSING` jobs are recovered after the configured timeout; failures retry with exponential backoff until `MAX_RETRY_COUNT` is reached.

The current processor is explicitly `MOCK`. It records a quality/preprocessing pipeline result but never invents customer IDs, meter readings, confidence, or production accuracy. Real inference model integration begins only after approved trained models are supplied.

The `migrate` Compose service applies all Alembic migrations before backend and worker start, eliminating queue-table startup races.
