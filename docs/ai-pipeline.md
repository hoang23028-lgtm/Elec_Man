# AI pipeline

The pipeline has isolated modules for quality assessment, conservative preprocessing, meter-window detection, customer OCR, meter reader, validator, and confidence calculation. Original images remain unchanged.

The bootstrap implementation uses OpenCV, pretrained RapidOCR ONNX models, and a Tesseract fallback. It reads customer labels such as `ma kh KH004`, finds the main mechanical digit row, and separately attempts the red decimal wheel. Every result remains `REVIEW`; recognition is never auto-approved. The immutable `ai_results` record retains OCR lines, detected regions, confidence components, and model version `meter-ocr-baseline-v1`.

This baseline is intended to collect verified labels while real data is still limited. It is not a trained production meter model. A future trained and evaluated model bundle must implement the same module interfaces and declare a new version before activation.
