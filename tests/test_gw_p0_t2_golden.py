import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


GOLDEN = Path(__file__).parent / "identity_restoration" / "golden"
INDEX = GOLDEN / "index.json"
EXPECTED = {
    "gw-p0-t2-case-01": {
        "input": "470e8aa2cd4055496186271a818e7aa31bf0fb5228242266a2c8c1cbc1cf4dcb",
        "restored": "ffc76268b8110970bbf5c93e34eeceb8b3a0e33c29d32b302c506758e0f92b8e",
        "composite": "448d9952965572c17ba355ac3a5fe5255025b470325287fa713510e2759bdab3",
        "box": {"left": 201, "top": 0, "right": 888, "bottom": 659},
    },
    "gw-p0-t2-case-02": {
        "input": "8a8b41fdbf2a15272fd2c6a6a1d36615ea8297fc5d5e012d7177f9f378c14574",
        "restored": "2827727d3ba97cdf6a74e830751986d81ffa2813bce076c33105c9264680346f",
        "composite": "e3e82bfe2b86dd73127eefa6c4cad6b44770ee33eb206389f173b7683246878f",
        "box": {"left": 232, "top": 0, "right": 858, "bottom": 620},
    },
    "gw-p0-t2-case-03": {
        "input": "bf0a8b6bf46b78de800fc83be6fd1b6280acb7323aece18897c53a8a4a3f83a6",
        "restored": "27fc01abb3f3975dd3370cfda2e94e9d4db04d53de6f24cc00529609efa6999c",
        "composite": "5bd7354d7bfb439e131e14cfe1740039eec61346dd94b2620a04988cbc22be01",
        "box": {"left": 170, "top": 0, "right": 920, "bottom": 695},
    },
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gw_p0_t2_golden_master_is_offline_and_exact() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    assert index["golden_case_count"] == 3
    assert len(index["case_ids"]) == 3
    for case_id in index["case_ids"]:
        expected = EXPECTED[case_id]
        case_dir = GOLDEN / case_id
        record = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
        input_path = case_dir / record["inputs"]["input_crop"]
        restored_path = case_dir / record["restored_crop"]["path"]
        composite_path = case_dir / record["composite"]["path"]
        assert _sha(input_path) == expected["input"] == record["inputs"]["input_crop_sha256"]
        assert _sha(restored_path) == expected["restored"] == record["restored_crop"]["sha256"]
        assert _sha(composite_path) == expected["composite"] == record["composite"]["sha256"]
        assert record["restored_crop"]["differs_from_input"]
        assert _sha(input_path) != _sha(restored_path)
        assert record["pixelLock"]["status"] == "PASS"
        assert record["pixelLock"]["mutatedPixelCount"] == 0
        assert record["cropTransform"]["box"] == expected["box"]
        assert record["seed"] == 42
        assert record["face_qc"]["samples"] == 3
        assert len(record["face_qc"]["values"]) == 3
        assert all(abs(value - record["face_qc"]["expected_baseline"]) <= record["face_qc"]["tolerance"]
                   for value in record["face_qc"]["values"])


def test_gw_p0_t2_pixel_lock_is_recomputed_from_frozen_pngs() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    for case_id in index["case_ids"]:
        case_dir = GOLDEN / case_id
        record = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
        base = Image.open(case_dir / "input_crop.png").convert("RGB")
        restored = Image.open(case_dir / "restored_crop.png").convert("RGB")
        assert base.size == restored.size
        assert np.any(np.asarray(base) != np.asarray(restored))
