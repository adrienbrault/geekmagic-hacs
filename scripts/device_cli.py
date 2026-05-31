#!/usr/bin/env python3
"""Live-device smoke tests for GeekMagic displays.

Examples:
    uv run python scripts/device_cli.py probe 192.168.1.100
    uv run python scripts/device_cli.py render-test 192.168.1.100 --dashboard clock
    uv run python scripts/device_cli.py upload-file 192.168.1.100 ./dashboard.jpg
    uv run python scripts/device_cli.py brightness 192.168.1.100 get
    uv run python scripts/device_cli.py brightness 192.168.1.100 set 80
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import MODEL_PRO, MODEL_SD_PRO
from custom_components.geekmagic.device import GeekMagicDevice
from custom_components.geekmagic.live_transaction import (
    backup_and_clear_album,
    backup_settings,
    cleanup_uploaded_sdpro_photo,
    restore_settings,
)
from custom_components.geekmagic.models import DeviceSettingsBackup, RenderedDashboardRequest
from custom_components.geekmagic.renderer import Renderer
from scripts.debug_render import DASHBOARDS

DeviceFactory = Callable[[str], GeekMagicDevice]
SleepFunc = Callable[[float], Awaitable[None]]

DEFAULT_HOLD_SECONDS = 15.0


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(description="Test GeekMagic devices from the repo")
    device_parent = argparse.ArgumentParser(add_help=False)
    device_parent.add_argument(
        "--bind-address",
        help="Local source IP to bind live-device HTTP connections to",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser(
        "probe",
        parents=[device_parent],
        help="Detect and inspect a device",
    )
    probe.add_argument("host", help="Device IP, hostname, or URL")

    render_test = subparsers.add_parser(
        "render-test",
        parents=[device_parent],
        help="Render a test dashboard, upload it, and display it",
    )
    render_test.add_argument("host", help="Device IP, hostname, or URL")
    render_test.add_argument(
        "--dashboard",
        choices=list(DASHBOARDS.keys()),
        default="clock",
        help="Debug dashboard to render",
    )
    render_test.add_argument("--filename", default="cli-test.jpg", help="Device filename")
    render_test.add_argument(
        "--hold-seconds",
        type=float,
        default=DEFAULT_HOLD_SECONDS,
        help="Seconds to keep the test image visible before restoring settings",
    )
    render_test.add_argument(
        "--no-restore",
        action="store_true",
        help="Leave device settings changed after the test",
    )
    render_test.add_argument(
        "--takeover-album",
        action="store_true",
        help=(
            "Back up and clear device images first, then restore them afterward. "
            "Makes Pro display tests deterministic."
        ),
    )
    render_test.add_argument(
        "--try-enter-picture",
        action="store_true",
        help="Try Pro Enter/Right/Enter button navigation after upload.",
    )

    upload_file = subparsers.add_parser(
        "upload-file",
        parents=[device_parent],
        help="Upload and display an image file",
    )
    upload_file.add_argument("host", help="Device IP, hostname, or URL")
    upload_file.add_argument("path", type=Path, help="Local image path")
    upload_file.add_argument(
        "--hold-seconds",
        type=float,
        default=DEFAULT_HOLD_SECONDS,
        help="Seconds to keep the uploaded image visible before restoring settings",
    )
    upload_file.add_argument(
        "--no-restore",
        action="store_true",
        help="Leave device settings changed after the upload",
    )
    upload_file.add_argument(
        "--takeover-album",
        action="store_true",
        help=(
            "Back up and clear device images first, then restore them afterward. "
            "Makes Pro display tests deterministic."
        ),
    )
    upload_file.add_argument(
        "--try-enter-picture",
        action="store_true",
        help="Try Pro Enter/Right/Enter button navigation after upload.",
    )

    brightness = subparsers.add_parser(
        "brightness",
        parents=[device_parent],
        help="Get or set display brightness",
    )
    brightness.add_argument("host", help="Device IP, hostname, or URL")
    brightness_sub = brightness.add_subparsers(dest="brightness_command", required=True)
    brightness_sub.add_parser("get", help="Read brightness")
    brightness_set = brightness_sub.add_parser("set", help="Set brightness")
    brightness_set.add_argument("value", type=int, help="Brightness 0-100")

    return parser


def _identity_text(device: GeekMagicDevice) -> str:
    """Return a human-readable device identity."""
    capabilities = device.capabilities
    identity = capabilities.display_name or device.profile_id
    if capabilities.firmware_version:
        return f"{identity} ({capabilities.firmware_version})"
    return identity


def _format_backup(backup: DeviceSettingsBackup) -> str:
    """Return a concise settings snapshot summary."""
    parts: list[str] = []
    if backup.state is not None:
        parts.append(f"theme={backup.state.theme}")
        parts.append(f"image={backup.state.current_image or 'unknown'}")
    if backup.brightness is not None:
        parts.append(f"brightness={backup.brightness}")
    if backup.album is not None:
        parts.append(
            "album="
            f"interval:{backup.album.interval},"
            f"gif_loop:{backup.album.gif_loop},"
            f"autoplay:{backup.album.autoplay}"
        )
    if backup.pro_album_files is not None:
        parts.append(f"pro_album_files={len(backup.pro_album_files)}")
    if backup.sdpro_photos is not None:
        enabled = sum(1 for photo in backup.sdpro_photos.files if photo.enabled)
        parts.append(
            f"sdpro_photos={len(backup.sdpro_photos.files)} files,"
            f"{enabled} enabled,interval:{backup.sdpro_photos.interval}"
        )
    if backup.sdpro_themes is not None:
        enabled = sum(1 for theme in backup.sdpro_themes.themes if theme.enabled)
        parts.append(
            f"sdpro_themes={len(backup.sdpro_themes.themes)} themes,"
            f"{enabled} enabled,interval:{backup.sdpro_themes.interval}"
        )
    if backup.sdpro_active_theme is not None:
        parts.append(f"sdpro_active_theme={backup.sdpro_active_theme}")
    return ", ".join(parts) if parts else "nothing readable"


async def _detect(device: GeekMagicDevice) -> None:
    """Detect model and print identity."""
    print("Step 1: detect model")
    model = await device.detect_model()
    print(f"  detected: {_identity_text(device)}")
    print(f"  profile: {model}")


async def _run_probe(device: GeekMagicDevice) -> int:
    """Run non-mutating probe command."""
    await _detect(device)

    print("Step 2: read storage")
    try:
        space = await device.get_space()
        used = space.total - space.free
        print(f"  storage: {used} used / {space.total} total ({space.free} free)")
    except Exception as err:
        print(f"  storage: unavailable ({err})")

    print("Step 3: read brightness")
    try:
        brightness = await device.get_brightness()
        print(f"  brightness: {brightness}")
    except Exception as err:
        print(f"  brightness: unavailable ({err})")

    print("Step 4: capabilities")
    supports_rendering = _supports_rendering(device)
    print(f"  rendered dashboard: {supports_rendering}")
    if supports_rendering:
        print(f"  display mechanism: {device.capabilities.display_mechanism}")
        print(f"  custom image theme: {device.capabilities.custom_image_theme}")
        print(f"  built-in modes: {', '.join(device.capabilities.builtin_modes)}")
    else:
        print(f"  display mechanism: {device.capabilities.display_mechanism}")
        print("  custom image theme: unavailable")
        print("  built-in modes: unavailable")
    for warning in device.capabilities.user_warnings:
        print(f"  warning: {warning}")
    return 0


def _supports_rendering(device: GeekMagicDevice) -> bool:
    """Return whether the stock render/upload/display path is supported."""
    return device.capabilities.supports_rendered_dashboard


async def _backup_settings(device: GeekMagicDevice, step: int) -> DeviceSettingsBackup:
    """Back up settings before mutating a live device."""
    print(f"Step {step}: back up device settings")
    backup = await backup_settings(device)
    print(f"  backup: {_format_backup(backup)}")
    return backup


async def _hold_for_viewing(hold_seconds: float, sleep: SleepFunc, step: int) -> None:
    """Keep the test visible long enough for human verification."""
    if hold_seconds <= 0:
        return
    print(f"Step {step}: hold test image for {hold_seconds:g}s")
    await sleep(hold_seconds)
    print("  hold: complete")


async def _restore_settings(
    device: GeekMagicDevice,
    backup: DeviceSettingsBackup,
    step: int,
) -> None:
    """Restore settings captured before a mutating test."""
    print(f"Step {step}: restore original settings")
    await restore_settings(device, backup)
    print("  restore: success")


async def _maybe_takeover_album(
    device: GeekMagicDevice,
    backup: DeviceSettingsBackup,
    takeover_album: bool,
    step: int,
) -> None:
    """Optionally clear the device album before uploading."""
    if takeover_album:
        print(f"Step {step}: back up and clear image album")
        if device.profile_id == MODEL_PRO:
            count = await backup_and_clear_album(device, backup)
            print(f"  backed up: {count or 0} album files")
            print("  cleared: all existing device images were removed")
        elif device.profile_id == MODEL_SD_PRO:
            await backup_and_clear_album(device, backup)
            print("  SD_PRO: using slideshow toggles instead of deleting photos")
        else:
            await backup_and_clear_album(device, backup)
            print("  cleared: all existing device images were removed")
    elif device.profile_id == MODEL_PRO:
        print("Note: Pro Picture mode cycles the device album.")
        print("      Use --takeover-album for deterministic display on a Pro.")
    elif device.profile_id == MODEL_SD_PRO:
        print(
            "Note: SD_PRO test temporarily makes the uploaded photo the only active slideshow item."
        )


async def _run_render_test(
    device: GeekMagicDevice,
    dashboard: str,
    filename: str,
    takeover_album: bool,
    try_enter_picture: bool,
    hold_seconds: float,
    restore: bool,
    sleep: SleepFunc,
) -> int:
    """Render a test dashboard and display it."""
    await _detect(device)

    if not _supports_rendering(device):
        print("Step 2: stop before mutation")
        print(f"  unsupported: profile '{device.profile_id}' has no upload/display path")
        return 2

    backup = await _backup_settings(device, 2)
    try:
        print(f"Step 3: render dashboard '{dashboard}'")
        renderer = Renderer()
        _, render_func = DASHBOARDS[dashboard]
        image_data = render_func(renderer)
        print(f"  rendered: {len(image_data)} bytes")

        await _maybe_takeover_album(device, backup, takeover_album, 4)

        print(f"Step 5: upload and display as {filename}")
        print(f"  custom image theme: {device.capabilities.custom_image_theme}")
        await device.display_rendered_dashboard(
            RenderedDashboardRequest(
                image_data=image_data,
                filename=filename,
                allow_destructive_album_management=takeover_album,
                try_menu_navigation=try_enter_picture,
            )
        )
        print("  success: device should now show the rendered dashboard")
        if device.profile_id == MODEL_PRO:
            print("  note: if it is not visible, manually select the Picture app on the device")

        await _hold_for_viewing(hold_seconds, sleep, 6)
    finally:
        if restore:
            await _restore_settings(device, backup, 7)
            if device.profile_id == MODEL_SD_PRO:
                print("Step 8: remove uploaded SD_PRO test photo")
                try:
                    removed = await cleanup_uploaded_sdpro_photo(device, backup, filename)
                except Exception as err:
                    print(f"  cleanup warning: {err}")
                else:
                    print("  cleanup: success" if removed else "  cleanup: not needed")
        else:
            print("Step 7: restore skipped (--no-restore)")
    return 0


async def _run_upload_file(
    device: GeekMagicDevice,
    path: Path,
    takeover_album: bool,
    try_enter_picture: bool,
    hold_seconds: float,
    restore: bool,
    sleep: SleepFunc,
) -> int:
    """Upload an existing image and display it."""
    await _detect(device)

    if not _supports_rendering(device):
        print("Step 2: stop before mutation")
        print(f"  unsupported: profile '{device.profile_id}' has no upload/display path")
        return 2

    backup = await _backup_settings(device, 2)
    try:
        print(f"Step 3: read image file {path}")
        image_data = await asyncio.to_thread(path.read_bytes)
        print(f"  read: {len(image_data)} bytes")

        await _maybe_takeover_album(device, backup, takeover_album, 4)

        print(f"Step 5: upload and display as {path.name}")
        print(f"  custom image theme: {device.capabilities.custom_image_theme}")
        await device.display_rendered_dashboard(
            RenderedDashboardRequest(
                image_data=image_data,
                filename=path.name,
                allow_destructive_album_management=takeover_album,
                try_menu_navigation=try_enter_picture,
            )
        )
        print("  success: device should now show the uploaded image")
        if device.profile_id == MODEL_PRO:
            print("  note: if it is not visible, manually select the Picture app on the device")

        await _hold_for_viewing(hold_seconds, sleep, 6)
    finally:
        if restore:
            await _restore_settings(device, backup, 7)
            if device.profile_id == MODEL_SD_PRO:
                print("Step 8: remove uploaded SD_PRO test photo")
                try:
                    removed = await cleanup_uploaded_sdpro_photo(device, backup, path.name)
                except Exception as err:
                    print(f"  cleanup warning: {err}")
                else:
                    print("  cleanup: success" if removed else "  cleanup: not needed")
        else:
            print("Step 7: restore skipped (--no-restore)")
    return 0


async def _run_brightness(device: GeekMagicDevice, args: argparse.Namespace) -> int:
    """Run brightness get/set command."""
    await _detect(device)

    if args.brightness_command == "get":
        print("Step 2: read brightness")
        brightness = await device.get_brightness()
        print(f"  brightness: {brightness}")
        return 0

    print(f"Step 2: set brightness to {args.value}")
    await device.set_brightness(args.value)
    print("  success")
    return 0


async def run(
    args: argparse.Namespace,
    device_factory: DeviceFactory = GeekMagicDevice,
    sleep: SleepFunc = asyncio.sleep,
) -> int:
    """Run a parsed CLI command."""
    bind_address = getattr(args, "bind_address", None)
    if bind_address and device_factory is GeekMagicDevice:
        device = GeekMagicDevice(args.host, source_address=bind_address)
    else:
        device = device_factory(args.host)
    try:
        if args.command == "probe":
            return await _run_probe(device)
        if args.command == "render-test":
            return await _run_render_test(
                device,
                args.dashboard,
                args.filename,
                args.takeover_album,
                args.try_enter_picture,
                args.hold_seconds,
                not args.no_restore,
                sleep,
            )
        if args.command == "upload-file":
            return await _run_upload_file(
                device,
                args.path,
                args.takeover_album,
                args.try_enter_picture,
                args.hold_seconds,
                not args.no_restore,
                sleep,
            )
        if args.command == "brightness":
            return await _run_brightness(device, args)
        raise ValueError(f"Unknown command: {args.command}")
    finally:
        await device.close()


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
