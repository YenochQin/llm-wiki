import importlib.metadata
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import _mineru_ocr_compat as compat

try:
    installed = importlib.metadata.version("mineru") == "4.0.12"
except importlib.metadata.PackageNotFoundError:
    installed = False


@unittest.skipUnless(installed, "Regression exercises the actual MinerU 4.0.12 OCR seam")
class MineruOcrCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        from mineru.model.ocr import geometry, results

        cls.np, cls.geometry, cls.results = np, geometry, results
        cls.original = staticmethod(results.get_ocr_result_list)
        compat.install()

    @classmethod
    def tearDownClass(cls):
        cls.results.get_ocr_result_list = cls.original

    def test_formula_mask_singleton_does_not_abort_page_or_drop_valid_neighbor(self):
        # Real masking returns [10, 10], then the old cropper attempts warp (0, 10).
        boxes = self.geometry.update_det_boxes(
            [self.geometry.bbox_to_points((10, 10, 20, 20))],
            [{"bbox": [11, 10, 20, 20]}],
        )
        self.assertEqual(boxes[0].tolist(), [[10, 10], [10, 10], [10, 20], [10, 20]])
        valid = self.geometry.bbox_to_points((22, 10, 35, 20))
        image = self.np.arange(40 * 40 * 3, dtype=self.np.uint8).reshape(40, 40, 3)
        useful = (0, 0, 0, 0, 40, 40, 40, 40)
        expected = self.original([valid], useful, True, image)
        result = self.results.get_ocr_result_list([boxes[0], valid], useful, True, image)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["bbox"], expected[0]["bbox"])
        self.np.testing.assert_array_equal(result[0]["np_img"], expected[0]["np_img"])

    def test_captured_seaton_zero_width_detection_returns_no_text(self):
        box = self.np.array([[262, 87], [262, 87], [262, 113], [262, 113]], dtype="float32")
        image = self.np.full((366, 1140, 3), 255, dtype="uint8")
        self.assertEqual(self.results.get_ocr_result_list(
            [box], (0, 0, 0, 0, 1140, 366, 1140, 366), True, image), [])

    def test_recognized_text_passes_through_unchanged(self):
        box = self.geometry.bbox_to_points((2, 2, 20, 12))
        image = self.np.zeros((30, 30, 3), dtype="uint8")
        items = [(box, ("Seaton", 0.99))]
        useful = (0, 0, 0, 0, 30, 30, 30, 30)
        self.assertEqual(self.results.get_ocr_result_list(items, useful, False, image),
                         self.original(items, useful, False, image))


if __name__ == "__main__":
    unittest.main()
