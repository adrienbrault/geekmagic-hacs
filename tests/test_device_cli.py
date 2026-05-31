"""Tests for live-device CLI wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.geekmagic.const import MODEL_PRO
from custom_components.geekmagic.device import (
    AlbumSettings,
    DeviceState,
    FirmwareCapabilities,
    RenderedDashboardRequest,
    SpaceInfo,
)
from scripts import device_cli


def _mock_device() -> MagicMock:
    """Create a mock GeekMagicDevice-like object."""
    device = MagicMock()
    device.model = MODEL_PRO
    device.profile_id = MODEL_PRO
    device.model_name = "GeekMagic SmallTV-PRO"
    device.firmware_version = "V3.3.76EN"
    device.custom_theme = 4
    device.builtin_modes = {"Bitcoin": 0, "Clock": 6}
    device.capabilities = FirmwareCapabilities(
        profile_id=MODEL_PRO,
        display_name="GeekMagic SmallTV-PRO",
        firmware_version="V3.3.76EN",
        supports_rendered_dashboard=True,
        builtin_modes={"Bitcoin": 0, "Clock": 6},
        custom_image_theme=4,
        display_mechanism="picture_album",
        requires_managed_album=True,
    )
    device.detect_model = AsyncMock(return_value=MODEL_PRO)
    device.get_space = AsyncMock(return_value=SpaceInfo(total=1000, free=400))
    device.get_brightness = AsyncMock(return_value=85)
    device.get_state = AsyncMock(
        return_value=DeviceState(theme=4, brightness=None, current_image=None)
    )
    device.get_album_settings = AsyncMock(
        return_value=AlbumSettings(interval=5, gif_loop=1, autoplay=0)
    )
    device.display_rendered_dashboard = AsyncMock()
    device.set_brightness = AsyncMock()
    device.set_album_display = AsyncMock()
    device.set_theme = AsyncMock()
    device.clear_images = AsyncMock()
    device.backup_pro_album_files = AsyncMock(return_value=[])
    device.restore_pro_album_files = AsyncMock()
    device.clear_pro_album_files = AsyncMock()
    device.delete_sdpro_photo = AsyncMock()
    device.close = AsyncMock()
    return device


def test_parser_probe() -> None:
    """Test probe command parsing."""
    args = device_cli.create_parser().parse_args(["probe", "192.168.1.50"])

    assert args.command == "probe"
    assert args.host == "192.168.1.50"
    assert args.bind_address is None


def test_parser_probe_bind_address() -> None:
    """Test probe command can bind to a local source address."""
    args = device_cli.create_parser().parse_args(
        ["probe", "--bind-address", "10.76.9.165", "192.168.1.50"]
    )

    assert args.command == "probe"
    assert args.host == "192.168.1.50"
    assert args.bind_address == "10.76.9.165"


def test_parser_render_test_defaults() -> None:
    """Test render-test command parsing."""
    args = device_cli.create_parser().parse_args(["render-test", "192.168.1.50"])

    assert args.command == "render-test"
    assert args.dashboard == "clock"
    assert args.filename == "cli-test.jpg"
    assert args.hold_seconds == device_cli.DEFAULT_HOLD_SECONDS
    assert args.no_restore is False
    assert args.takeover_album is False
    assert args.try_enter_picture is False


def test_parser_render_test_try_enter_picture() -> None:
    """Test render-test can explicitly opt into Pro button navigation."""
    args = device_cli.create_parser().parse_args(
        ["render-test", "192.168.1.50", "--try-enter-picture"]
    )

    assert args.try_enter_picture is True


def test_parser_upload_file() -> None:
    """Test upload-file command parsing."""
    args = device_cli.create_parser().parse_args(["upload-file", "192.168.1.50", "dashboard.jpg"])

    assert args.command == "upload-file"
    assert args.path.name == "dashboard.jpg"
    assert args.hold_seconds == device_cli.DEFAULT_HOLD_SECONDS
    assert args.takeover_album is False
    assert args.no_restore is False
    assert args.try_enter_picture is False


def test_parser_brightness_set() -> None:
    """Test brightness set command parsing."""
    args = device_cli.create_parser().parse_args(["brightness", "192.168.1.50", "set", "80"])

    assert args.command == "brightness"
    assert args.brightness_command == "set"
    assert args.value == 80


@pytest.mark.asyncio
async def test_run_probe_uses_device_methods(capsys: pytest.CaptureFixture[str]) -> None:
    """Test probe calls detection, storage, and brightness methods."""
    device = _mock_device()
    args = device_cli.create_parser().parse_args(["probe", "192.168.1.50"])

    result = await device_cli.run(args, device_factory=lambda host: device)

    assert result == 0
    device.detect_model.assert_awaited_once()
    device.get_space.assert_awaited_once()
    device.get_brightness.assert_awaited_once()
    device.close.assert_awaited_once()
    output = capsys.readouterr().out
    assert "GeekMagic SmallTV-PRO" in output
    assert "custom image theme: 4" in output


@pytest.mark.asyncio
async def test_run_render_test_uploads_rendered_dashboard() -> None:
    """Test render-test uploads through GeekMagicDevice."""
    device = _mock_device()
    sleep = AsyncMock()
    args = device_cli.create_parser().parse_args(
        ["render-test", "192.168.1.50", "--dashboard", "clock"]
    )

    result = await device_cli.run(args, device_factory=lambda host: device, sleep=sleep)

    assert result == 0
    device.detect_model.assert_awaited_once()
    device.get_state.assert_awaited_once()
    device.display_rendered_dashboard.assert_awaited_once()
    request = device.display_rendered_dashboard.await_args.args[0]
    assert isinstance(request, RenderedDashboardRequest)
    assert request.image_data.startswith(b"\xff\xd8")
    assert request.filename == "cli-test.jpg"
    assert request.allow_destructive_album_management is False
    assert request.try_menu_navigation is False
    device.clear_images.assert_not_awaited()
    sleep.assert_awaited_once_with(device_cli.DEFAULT_HOLD_SECONDS)
    device.set_brightness.assert_awaited_once_with(85)
    device.set_album_display.assert_awaited_once_with(interval=5, gif_loop=1, autoplay=0)
    device.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_render_test_can_take_over_album() -> None:
    """Test render-test can explicitly clear the device album first."""
    device = _mock_device()
    sleep = AsyncMock()
    args = device_cli.create_parser().parse_args(
        [
            "render-test",
            "192.168.1.50",
            "--dashboard",
            "clock",
            "--takeover-album",
            "--hold-seconds",
            "0",
        ]
    )

    result = await device_cli.run(args, device_factory=lambda host: device, sleep=sleep)

    assert result == 0
    device.backup_pro_album_files.assert_awaited_once()
    device.clear_pro_album_files.assert_awaited_once()
    request = device.display_rendered_dashboard.await_args.args[0]
    assert request.allow_destructive_album_management is True
    assert request.try_menu_navigation is False
    sleep.assert_not_awaited()
    device.set_theme.assert_awaited_once_with(4)


@pytest.mark.asyncio
async def test_run_upload_file_uploads_path_bytes(tmp_path) -> None:
    """Test upload-file reads a path and uploads through GeekMagicDevice."""
    device = _mock_device()
    sleep = AsyncMock()
    image = tmp_path / "image.jpg"
    image.write_bytes(b"jpeg-data")
    args = device_cli.create_parser().parse_args(
        ["upload-file", "192.168.1.50", str(image), "--hold-seconds", "0"]
    )

    result = await device_cli.run(args, device_factory=lambda host: device, sleep=sleep)

    assert result == 0
    device.get_state.assert_awaited_once()
    device.display_rendered_dashboard.assert_awaited_once()
    request = device.display_rendered_dashboard.await_args.args[0]
    assert request == RenderedDashboardRequest(
        image_data=b"jpeg-data",
        filename="image.jpg",
        allow_destructive_album_management=False,
        try_menu_navigation=False,
    )
    sleep.assert_not_awaited()
    device.set_brightness.assert_awaited_once_with(85)
    device.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_upload_file_can_take_over_album(tmp_path) -> None:
    """Test upload-file takeover also exercises managed album upload."""
    device = _mock_device()
    image = tmp_path / "image.jpg"
    image.write_bytes(b"jpeg-data")
    args = device_cli.create_parser().parse_args(
        [
            "upload-file",
            "192.168.1.50",
            str(image),
            "--takeover-album",
            "--hold-seconds",
            "0",
        ]
    )

    result = await device_cli.run(args, device_factory=lambda host: device, sleep=AsyncMock())

    assert result == 0
    device.backup_pro_album_files.assert_awaited_once()
    device.clear_pro_album_files.assert_awaited_once()
    request = device.display_rendered_dashboard.await_args.args[0]
    assert request.allow_destructive_album_management is True
    assert request.try_menu_navigation is False
    device.set_album_display.assert_awaited_once_with(interval=5, gif_loop=1, autoplay=0)


@pytest.mark.asyncio
async def test_run_upload_file_can_try_enter_picture(tmp_path) -> None:
    """Test upload-file forwards the explicit Pro navigation flag."""
    device = _mock_device()
    image = tmp_path / "image.jpg"
    image.write_bytes(b"jpeg-data")
    args = device_cli.create_parser().parse_args(
        [
            "upload-file",
            "192.168.1.50",
            str(image),
            "--hold-seconds",
            "0",
            "--try-enter-picture",
        ]
    )

    result = await device_cli.run(args, device_factory=lambda host: device, sleep=AsyncMock())

    assert result == 0
    request = device.display_rendered_dashboard.await_args.args[0]
    assert request.try_menu_navigation is True


@pytest.mark.asyncio
async def test_run_render_test_stops_before_unsupported_mutation() -> None:
    """Test unsupported devices are not mutated by render-test."""
    device = _mock_device()
    device.model = "unknown"
    device.profile_id = "unknown"
    device.capabilities = FirmwareCapabilities(
        profile_id="unknown",
        display_name="SmallTV",
        supports_rendered_dashboard=False,
    )
    args = device_cli.create_parser().parse_args(["render-test", "192.168.1.50"])

    result = await device_cli.run(args, device_factory=lambda host: device, sleep=AsyncMock())

    assert result == 2
    device.get_state.assert_not_awaited()
    device.clear_images.assert_not_awaited()
    device.display_rendered_dashboard.assert_not_awaited()
    device.set_brightness.assert_not_awaited()
    device.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_upload_file_can_skip_restore(tmp_path) -> None:
    """Test upload-file can intentionally leave settings changed."""
    device = _mock_device()
    image = tmp_path / "image.jpg"
    image.write_bytes(b"jpeg-data")
    args = device_cli.create_parser().parse_args(
        ["upload-file", "192.168.1.50", str(image), "--hold-seconds", "0", "--no-restore"]
    )

    result = await device_cli.run(args, device_factory=lambda host: device, sleep=AsyncMock())

    assert result == 0
    device.get_state.assert_awaited_once()
    device.display_rendered_dashboard.assert_awaited_once()
    device.set_brightness.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_brightness_set_uses_device_method() -> None:
    """Test brightness set calls GeekMagicDevice."""
    device = _mock_device()
    args = device_cli.create_parser().parse_args(["brightness", "192.168.1.50", "set", "80"])

    result = await device_cli.run(args, device_factory=lambda host: device)

    assert result == 0
    device.set_brightness.assert_awaited_once_with(80)
    device.close.assert_awaited_once()
