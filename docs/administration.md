# Administration

System settings, model lifecycle records, evaluation metrics, and audit history are authenticated administrator functions.

Settings changes are validated, stored in PostgreSQL, and audited. Values that control process startup remain deployment policies and take effect after the related environment configuration and service restart; no hidden automatic restart occurs.

Model registration accepts only files already present below `MODELS_ROOT`. The API resolves the path inside that root and verifies the submitted SHA-256. New records begin in `TESTING`. Activation archives the previous active model of the same type and records an audit event, but deliberately does not hot-load arbitrary code or automatically deploy a model.

Evaluation uses immutable AI predictions paired with human-confirmed final readings. Customer exact accuracy, reading exact accuracy, and digit accuracy are reported only for confirmed samples. These operational metrics are not a substitute for a held-out test dataset. False-auto-pass remains unavailable while the review-only OCR baseline cannot auto-pass results.
