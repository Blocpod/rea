"""Container boundary checks with synthetic data; no Canon bytes bundled."""

import importlib.util
from pathlib import Path
import struct
import unittest

path = Path(__file__).resolve().parents[1] / "tools" / "inspect_fir.py"
spec = importlib.util.spec_from_file_location("inspect_fir", path)
fir = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fir)


def fixture():
    data = bytearray(0x320)
    def put(offset, value):
        struct.pack_into("<I", data, offset, value)
    put(0, fir.MODEL)
    data[0x10:0x15] = b"1.0.3"
    for offset, value in ((0x24, 0xB0), (0x28, 0x120), (0x2C, 0xFFFFFFFF),
                          (0x30, 0x220), (0x34, 0xFFFFFFFF), (0x38, len(data)),
                          (0x60, 0x220), (0x64, 0x100), (0xB0, 0x100),
                          (0x224, 0x80), (0x228, 0x100), (0x230, 0x80), (0x234, 0x80)):
        put(offset, value)
    data[0xC0] = 1
    checksum(data)
    return data


def checksum(data):
    value = (~(sum(data[:0x20]) + sum(data[0x24:]))) & 0xFFFFFFFF
    struct.pack_into("<I", data, 0x20, value)


class FirTest(unittest.TestCase):
    def test_ranges_and_identity_are_distinct(self):
        report = fir.inspect(fixture())
        self.assertFalse(report["matches_downloaded_official_reference"])
        self.assertTrue(report["checksum"]["valid"])
        self.assertEqual(report["regions"][-1]["offset"], 0x2A0)
        self.assertFalse(report["authentication"]["hmac_verified"])

    def test_corrupted_body_fails(self):
        data = fixture()
        data[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            fir.inspect(data)

    def test_truncated_input_fails(self):
        for size in (0, 0x110, 0x300):
            with self.subTest(size=size), self.assertRaises(ValueError):
                fir.inspect(fixture()[:size])

    def test_out_of_range_and_overlap_fail_even_with_valid_checksum(self):
        for offset, value in ((0x30, 0xFFFFFFFF), (0xB0, 0x101),
                              (0x64, 0xFFFF0000), (0x224, 0xFFFFFF80),
                              (0x230, 0xFFFF0000), (0x234, 1)):
            data = fixture()
            struct.pack_into("<I", data, offset, value)
            checksum(data)
            with self.subTest(offset=hex(offset)), self.assertRaises(ValueError):
                fir.inspect(data)

    def test_wrong_camera_and_layout_fail(self):
        for offset, value in ((0, 0x80000349), (0x24, 0x100), (0x2C, 0)):
            data = fixture()
            struct.pack_into("<I", data, offset, value)
            checksum(data)
            with self.subTest(offset=hex(offset)), self.assertRaises(ValueError):
                fir.inspect(data)


if __name__ == "__main__":
    unittest.main()
