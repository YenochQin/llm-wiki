"""Scoped compatibility fixes for the installed MinerU 4 OCR pipeline."""

import functools
import importlib.metadata
import logging


def install() -> bool:
    """Install before importing MinerU's CLI/backend, which bind this function.

    MinerU 4.0.12's formula masking can leave a closed singleton interval.
    Its OCR result handler tries to crop that zero-area box before its later
    geometry filter, causing docvortex to reject a zero-width warp. Only these
    boxes are discarded here; positive-area boxes retain the upstream path.
    """
    if importlib.metadata.version("mineru") != "4.0.12":
        return False
    import numpy as np
    from mineru.model.ocr import results

    original = results.get_ocr_result_list
    if getattr(original, "_llm_wiki_zero_area_guard", False):
        return True

    @functools.wraps(original)
    def guarded(ocr_res, useful_list, ocr_enable, bgr_image):
        retained = []
        for item in ocr_res:
            # Two-element items already contain recognized text and confidence.
            if ocr_enable and len(item) == 4:
                points = np.asarray(item)
                if points.shape == (4, 2) and np.isfinite(points).all():
                    if np.any(np.ptp(points, axis=0) == 0):
                        logging.getLogger(__name__).warning(
                            "[mineru-compat] Discarding zero-area OCR box before crop: %s",
                            points.tolist(),
                        )
                        continue
            retained.append(item)
        return original(retained, useful_list, ocr_enable, bgr_image)

    guarded._llm_wiki_zero_area_guard = True
    results.get_ocr_result_list = guarded
    return True
