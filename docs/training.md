# Training data

`training/annotations.jsonl` is the versioned label manifest for approved training samples. Images are not committed: meter photos may contain personal or operational data and must remain in protected object storage.

Each row requires a SHA-256 checksum, a verified customer identifier, and the full meter reading. The seed record currently represents `ảnh.jpg` with `KH003` and `05068.4 kWh`; its red final wheel is the decimal-tenths digit.

One image is a labelled seed and evaluation fixture, not a sufficient training set. Before activating a real recognition model, collect a split dataset with a representative range of meter types, lighting, blur, viewpoints, dirt/occlusion, and digit combinations. Keep a held-out test split and publish accuracy/error metrics for customer ID and reading separately.

Manual confirmations recorded by the application are the operational source of future labels. Train only from labels that have been reviewed by an authorised person, and keep the model version and evaluation report with every deployed model bundle.
