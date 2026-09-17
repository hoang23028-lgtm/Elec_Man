# AI pipeline

The Phase 5 pipeline has isolated modules for quality assessment, conservative preprocessing, detector, customer OCR, meter reader, validator, and confidence calculation. Original images remain unchanged.

The included implementations are development mocks. Quality analysis uses OpenCV (blur, brightness, contrast, and resolution signals); object detection and recognition return no values, and therefore every result is marked `REVIEW` with `is_mock: true`. The immutable `ai_results` record retains raw pipeline output and model version `mock-pipeline-v0`.

Do not replace these mocks with arbitrary downloaded models. A trained, evaluated model bundle must implement the same module interfaces and declare its real version before activation.
