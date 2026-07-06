from __future__ import annotations

from pathlib import Path
import tempfile

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


class OcrService:
    """Optional local OCR wrapper with lightweight image preprocessing."""

    def __init__(self) -> None:
        self._engine = None
        try:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        except Exception:
            self._engine = None

    @property
    def available(self) -> bool:
        return self._engine is not None

    def extract_text(self, image_path: Path) -> str:
        if not self._engine:
            return ""

        image = Image.open(image_path).convert("RGB")
        candidates = [image]
        candidates.extend(self._preprocess_candidates(image))

        best_text = ""
        for candidate in candidates:
            text = self._run_ocr(candidate)
            if self._score_text(text) > self._score_text(best_text):
                best_text = text

        return best_text.strip()

    def _preprocess_candidates(self, image: Image.Image) -> list[Image.Image]:
        enlarged = image.resize((image.width * 2, image.height * 2))
        grayscale = ImageOps.grayscale(enlarged)
        contrast = ImageEnhance.Contrast(grayscale).enhance(2.4)
        sharp = contrast.filter(ImageFilter.SHARPEN)
        binary = sharp.point(lambda pixel: 255 if pixel > 170 else 0, mode="1").convert("L")
        inverted = ImageOps.invert(binary)
        smooth = sharp.filter(ImageFilter.MedianFilter(size=3))
        return [grayscale, contrast, sharp, binary, inverted, smooth]

    def _run_ocr(self, image: Image.Image) -> str:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        try:
            image.save(temp_path)
            result, _ = self._engine(str(temp_path))
        except Exception:
            return ""
        finally:
            temp_path.unlink(missing_ok=True)

        if not result:
            return ""

        lines = [item[1] for item in result if len(item) >= 2 and isinstance(item[1], str)]
        return "\n".join(line.strip() for line in lines if line.strip())

    def _score_text(self, text: str) -> tuple[int, int, int]:
        cleaned = text.strip()
        meaningful_chars = sum(1 for char in cleaned if char.isalnum() or "\u4e00" <= char <= "\u9fff")
        line_count = cleaned.count("\n") + (1 if cleaned else 0)
        return (meaningful_chars, len(cleaned), line_count)
