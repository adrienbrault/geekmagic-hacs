"""Tests for the image widget's source loader and cache (image_source.py).

Covers path safety (config-dir resolution, the HA allowlist, traversal and
symlink escapes), decoding (GIF first frame, alpha, downscale) and the
cache policy: one fetch per refresh interval, stale picture kept on error.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from custom_components.geekmagic import image_source
from custom_components.geekmagic.const import IMAGE_SOURCE_RETRY
from custom_components.geekmagic.image_source import (
    MAX_LONG_SIDE,
    MAX_SHORT_SIDE,
    ImageSourceCache,
    ImageSourceError,
    decode_image,
    get_image_cache,
    is_image_source,
    read_local_file,
    resolve_local_path,
)

URL = "https://example.com/logo.png"


def png_bytes(size=(8, 8), color=(255, 0, 0), mode="RGB") -> bytes:
    buf = BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


class FakeClock:
    """Stand-in for time.monotonic that tests advance by hand."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    fake = FakeClock()
    with patch("custom_components.geekmagic.image_source.time.monotonic", fake):
        yield fake


@pytest.fixture
def config_dir(hass, tmp_path):
    """A real config dir with www/ allowlisted (HA's default)."""
    hass.config.config_dir = str(tmp_path)
    www = tmp_path / "www"
    www.mkdir()
    hass.config.allowlist_external_dirs = {str(www.resolve())}
    return tmp_path


# --- classification / path mapping ----------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("camera.front_door", False),
        ("image.last_person", False),
        ("https://example.com/a.gif", True),
        ("http://192.168.1.2/snap.jpg", True),
        ("www/alarm.gif", True),
        ("/local/alarm.gif", True),
        ("/media/pics/a.png", True),
    ],
)
def test_is_image_source(value, expected):
    assert is_image_source(value) is expected


def test_resolve_relative_to_config_dir():
    assert resolve_local_path("/config", "www/a.png") == Path("/config/www/a.png")


def test_resolve_local_url_maps_to_www():
    assert resolve_local_path("/config", "/local/img/a.png") == Path("/config/www/img/a.png")


def test_resolve_absolute_path_kept():
    assert resolve_local_path("/config", "/media/a.png") == Path("/media/a.png")


@pytest.mark.parametrize("source", ["www/../secrets.yaml", "../etc/passwd", "/local/../x.png"])
def test_resolve_rejects_parent_segments(source):
    with pytest.raises(ImageSourceError):
        resolve_local_path("/config", source)


# --- local file reads -------------------------------------------------------


async def test_read_allowed_file(hass, config_dir):
    (config_dir / "www" / "logo.png").write_bytes(png_bytes())
    data = await hass.async_add_executor_job(read_local_file, hass, "www/logo.png")
    assert data == png_bytes()
    data = await hass.async_add_executor_job(read_local_file, hass, "/local/logo.png")
    assert data == png_bytes()


async def test_read_rejects_config_root_file(hass, config_dir):
    """The config dir itself is NOT allowlisted: secrets.yaml stays private."""
    (config_dir / "secrets.yaml").write_text("api_key: hunter2")
    with pytest.raises(ImageSourceError, match="outside"):
        await hass.async_add_executor_job(read_local_file, hass, str(config_dir / "secrets.yaml"))


async def test_read_rejects_absolute_path_outside_allowlist(hass, config_dir, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "a.png"
    outside.write_bytes(png_bytes())
    with pytest.raises(ImageSourceError, match="outside"):
        await hass.async_add_executor_job(read_local_file, hass, str(outside))


async def test_read_rejects_symlink_escaping_www(hass, config_dir):
    secret = config_dir / "secrets.yaml"
    secret.write_text("api_key: hunter2")
    (config_dir / "www" / "innocent.png").symlink_to(secret)
    with pytest.raises(ImageSourceError, match="outside"):
        await hass.async_add_executor_job(read_local_file, hass, "www/innocent.png")


async def test_read_missing_file(hass, config_dir):
    with pytest.raises(ImageSourceError, match="not found"):
        await hass.async_add_executor_job(read_local_file, hass, "www/nope.png")


async def test_read_rejects_directory(hass, config_dir):
    (config_dir / "www" / "dir").mkdir()
    with pytest.raises(ImageSourceError, match="not a file"):
        await hass.async_add_executor_job(read_local_file, hass, "www/dir")


# --- decoding ---------------------------------------------------------------


def test_decode_gif_first_frame():
    buf = BytesIO()
    frames = [Image.new("RGB", (10, 10), c) for c in ((255, 0, 0), (0, 0, 255))]
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], loop=0)
    image = decode_image(buf.getvalue())
    assert image.mode == "RGB"
    r, _g, b = image.getpixel((5, 5))  # ty: ignore[not-iterable]
    assert r > 200 and b < 50


def test_decode_keeps_transparency():
    image = decode_image(png_bytes(mode="RGBA", color=(0, 0, 0, 0)))
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0  # ty: ignore[not-subscriptable]


def test_decode_bounds_panorama_long_side():
    image = decode_image(png_bytes(size=(4000, 500)))
    assert image.size == (MAX_LONG_SIDE, 120)


def test_decode_downscales_large_photo():
    image = decode_image(png_bytes(size=(3000, 3000)))
    assert image.size == (MAX_SHORT_SIDE, MAX_SHORT_SIDE)


def test_decode_keeps_short_side_for_cover():
    """A wide picture keeps a 480px short side so `cover` stays sharp."""
    image = decode_image(png_bytes(size=(1200, 600)))
    assert image.size == (960, 480)


def test_decode_applies_exif_orientation():
    """Phone photos stored sideways are shown upright."""
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: rotate 90 CW to display
    buf = BytesIO()
    Image.new("RGB", (40, 20), (255, 0, 0)).save(buf, format="JPEG", exif=exif)
    assert decode_image(buf.getvalue()).size == (20, 40)


def test_decode_small_picture_untouched():
    assert decode_image(png_bytes(size=(64, 32))).size == (64, 32)


def test_decode_rejects_non_image():
    with pytest.raises(Exception):  # noqa: B017, PT011 - PIL's own error type
        decode_image(b"<html>not an image</html>")


# --- the cache --------------------------------------------------------------


async def test_url_fetched_once_within_refresh(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    cache = ImageSourceCache(hass)

    first = await cache.async_get(URL, 3600)
    clock.now += 10  # next render tick
    second = await cache.async_get(URL, 3600)

    assert first is not None
    assert second is not None
    assert second.tobytes() == first.tobytes()
    assert aioclient_mock.call_count == 1


async def test_each_caller_gets_its_own_copy(hass, aioclient_mock, clock):
    """Renders run in executor threads and Image.save mutates the image."""
    aioclient_mock.get(URL, content=png_bytes())
    cache = ImageSourceCache(hass)
    first = await cache.async_get(URL, 3600)
    second = await cache.async_get(URL, 3600)
    assert first is not second


async def test_url_refetched_after_refresh_interval(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    cache = ImageSourceCache(hass)

    await cache.async_get(URL, 300)
    clock.now += 300
    await cache.async_get(URL, 300)

    assert aioclient_mock.call_count == 2


async def test_failure_keeps_stale_picture_and_backs_off(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    cache = ImageSourceCache(hass)
    good = await cache.async_get(URL, 60)
    assert good is not None

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=500)
    clock.now += 60
    stale = await cache.async_get(URL, 60)  # failed refresh: stale kept
    assert stale is not None
    assert stale.tobytes() == good.tobytes()
    clock.now += 10
    assert await cache.async_get(URL, 60) is not None  # within retry window: skipped
    assert aioclient_mock.call_count == 1

    clock.now += IMAGE_SOURCE_RETRY
    await cache.async_get(URL, 60)
    assert aioclient_mock.call_count == 2


async def test_http_error_never_loaded_returns_none(hass, aioclient_mock, clock, caplog):
    aioclient_mock.get(URL, status=404)
    cache = ImageSourceCache(hass)
    assert await cache.async_get(URL, 60) is None
    assert "HTTP 404" in caplog.text


async def test_oversized_download_rejected(hass, aioclient_mock, clock, caplog):
    with patch.object(image_source, "MAX_SOURCE_BYTES", 16):
        aioclient_mock.get(URL, content=png_bytes())
        assert await ImageSourceCache(hass).async_get(URL, 60) is None
    assert "larger than 16 bytes" in caplog.text


async def test_local_file_loaded_through_cache(hass, config_dir, clock):
    (config_dir / "www" / "logo.png").write_bytes(png_bytes(color=(0, 255, 0)))
    image = await ImageSourceCache(hass).async_get("/local/logo.png", 60)
    assert image is not None
    assert image.getpixel((0, 0)) == (0, 255, 0)


async def test_rejected_path_returns_none(hass, config_dir, clock):
    (config_dir / "secrets.yaml").write_text("x")
    assert await ImageSourceCache(hass).async_get(str(config_dir / "secrets.yaml"), 60) is None


async def test_invalidate_forces_refetch(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    cache = ImageSourceCache(hass)
    await cache.async_get(URL, 3600)
    cache.invalidate()
    await cache.async_get(URL, 3600)
    assert aioclient_mock.call_count == 2


async def test_invalidate_one_source(hass, aioclient_mock, clock):
    other = "https://example.com/other.png"
    aioclient_mock.get(URL, content=png_bytes())
    aioclient_mock.get(other, content=png_bytes())
    cache = ImageSourceCache(hass)
    await cache.async_get(URL, 3600)
    await cache.async_get(other, 3600)
    cache.invalidate(URL)
    await cache.async_get(URL, 3600)
    await cache.async_get(other, 3600)
    assert aioclient_mock.call_count == 3


async def test_quiet_failures_log_at_debug(hass, aioclient_mock, clock, caplog):
    """The preview's half-typed sources don't spam WARNINGs."""
    aioclient_mock.get(URL, status=404)
    await ImageSourceCache(hass).async_get(URL, 60, quiet=True)
    assert not [r for r in caplog.records if r.levelname == "WARNING"]


async def test_concurrent_requests_share_one_fetch(hass, aioclient_mock, clock):
    import asyncio

    aioclient_mock.get(URL, content=png_bytes())
    cache = ImageSourceCache(hass)
    a, b = await asyncio.gather(cache.async_get(URL, 60), cache.async_get(URL, 60))
    assert a is not None
    assert b is not None
    assert aioclient_mock.call_count == 1


async def test_cache_is_bounded(hass, aioclient_mock, clock):
    """Half-typed preview URLs can't grow the cache without bound."""
    cache = ImageSourceCache(hass)
    for i in range(image_source.MAX_ENTRIES + 10):
        aioclient_mock.get(f"https://example.com/{i}.png", status=404)
        clock.now += 1
        await cache.async_get(f"https://example.com/{i}.png", 60)
    assert len(cache._entries) == image_source.MAX_ENTRIES


async def test_unused_entries_evicted(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    aioclient_mock.get("https://example.com/other.png", content=png_bytes())
    cache = ImageSourceCache(hass)
    await cache.async_get(URL, 60)
    clock.now += image_source.UNUSED_EVICT_SECONDS + 1
    await cache.async_get("https://example.com/other.png", 60)
    assert URL not in cache._entries


async def test_blank_source_is_none(hass, clock):
    assert await ImageSourceCache(hass).async_get("   ", 60) is None


async def test_get_image_cache_is_shared(hass):
    assert get_image_cache(hass) is get_image_cache(hass)
