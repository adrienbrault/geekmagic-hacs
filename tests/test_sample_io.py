"""Tests for the sample generators' save/prune helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PIL import Image

from scripts import sample_io
from scripts.sample_io import (
    NOISE_TOLERANCE,
    find_orphans,
    images_match,
    prune,
    save_gif_sample,
    save_sample,
)

if TYPE_CHECKING:
    from pathlib import Path


def _solid(color: tuple[int, int, int], size: tuple[int, int] = (8, 8)) -> Image.Image:
    return Image.new("RGB", size, color)


class TestImagesMatch:
    def test_identical(self) -> None:
        assert images_match(_solid((10, 20, 30)), _solid((10, 20, 30)))

    def test_within_tolerance_is_noise(self) -> None:
        a = _solid((10, 20, 30))
        b = a.copy()
        b.putpixel((3, 3), (10 + NOISE_TOLERANCE, 20 - NOISE_TOLERANCE, 30))
        assert images_match(a, b)

    def test_beyond_tolerance_is_a_change(self) -> None:
        a = _solid((10, 20, 30))
        b = a.copy()
        b.putpixel((3, 3), (10, 20, 30 + NOISE_TOLERANCE + 1))
        assert not images_match(a, b)

    def test_size_mismatch_is_a_change(self) -> None:
        assert not images_match(_solid((0, 0, 0)), _solid((0, 0, 0), (8, 9)))

    def test_single_band_images(self) -> None:
        a = Image.new("L", (4, 4), 100)
        assert images_match(a, Image.new("L", (4, 4), 101))
        assert not images_match(a, Image.new("L", (4, 4), 110))

    def test_mode_mismatch_compares_pixels(self) -> None:
        assert images_match(_solid((10, 20, 30)), _solid((10, 20, 30)).convert("RGBA"))


def _gif(*colors: tuple[int, int, int]) -> bytes:
    from io import BytesIO

    frames = [_solid(c) for c in colors]
    buffer = BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], loop=0)
    return buffer.getvalue()


class TestSaveGifSample:
    @pytest.fixture(autouse=True)
    def _isolate_produced(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sample_io, "PRODUCED", set())

    def test_writes_new_file_and_records_it(self, tmp_path: Path) -> None:
        path = tmp_path / "html" / "a.gif"
        save_gif_sample(_gif((0, 0, 0), (255, 0, 0)), path)
        assert path.exists()
        assert path.resolve() in sample_io.PRODUCED

    def test_same_frames_do_not_rewrite(self, tmp_path: Path) -> None:
        path = tmp_path / "a.gif"
        path.write_bytes(_gif((0, 0, 0), (255, 0, 0)))
        before = path.stat().st_mtime_ns
        save_gif_sample(_gif((0, 0, 0), (255, 0, 0)), path)
        assert path.stat().st_mtime_ns == before

    def test_changed_frame_rewrites(self, tmp_path: Path) -> None:
        path = tmp_path / "a.gif"
        path.write_bytes(_gif((0, 0, 0), (255, 0, 0)))
        new = _gif((0, 0, 0), (0, 0, 255))
        save_gif_sample(new, path)
        assert path.read_bytes() == new

    def test_frame_count_change_rewrites(self, tmp_path: Path) -> None:
        path = tmp_path / "a.gif"
        path.write_bytes(_gif((0, 0, 0), (255, 0, 0)))
        new = _gif((0, 0, 0), (255, 0, 0), (0, 255, 0))
        save_gif_sample(new, path)
        assert path.read_bytes() == new


class TestSaveSample:
    @pytest.fixture(autouse=True)
    def _isolate_produced(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sample_io, "PRODUCED", set())

    def test_noise_does_not_rewrite(self, tmp_path: Path) -> None:
        path = tmp_path / "a.png"
        _solid((10, 20, 30)).save(path)
        before = path.read_bytes()
        save_sample(_solid((11, 20, 30)), path)
        assert path.read_bytes() == before
        assert path.resolve() in sample_io.PRODUCED

    def test_real_change_rewrites(self, tmp_path: Path) -> None:
        path = tmp_path / "sub" / "a.png"
        save_sample(_solid((10, 20, 30)), path)
        save_sample(_solid((200, 20, 30)), path)
        with Image.open(path) as img:
            assert img.getpixel((0, 0)) == (200, 20, 30)


class TestPrune:
    def test_find_orphans(self, tmp_path: Path) -> None:
        keep = tmp_path / "keep.png"
        stale = tmp_path / "widgets" / "stale.png"
        stale.parent.mkdir()
        keep.write_bytes(b"x")
        stale.write_bytes(b"x")
        assert find_orphans(tmp_path, {keep}) == [stale]

    def test_prune_removes_orphans_and_empty_dirs(self, tmp_path: Path) -> None:
        keep = tmp_path / "layouts" / "keep.png"
        stale = tmp_path / "widgets" / "deep" / "stale.png"
        keep.parent.mkdir()
        stale.parent.mkdir(parents=True)
        keep.write_bytes(b"x")
        stale.write_bytes(b"x")
        assert prune(tmp_path, {keep}) == [stale]
        assert keep.exists()
        assert not (tmp_path / "widgets").exists()
