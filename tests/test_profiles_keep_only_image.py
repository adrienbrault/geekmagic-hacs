"""A Pro album cleanup must not delete the user's pictures before it looks.

``keep_only_image`` runs on every push when "Manage Pro Picture Album" is
on, and the album listing it reads is scraped from an undocumented HTML
page: it can lag the upload or miss the new file. Deleting first wiped
the user's own pictures and then raised, so the push failed too and the
Picture slideshow was left empty.
"""

from __future__ import annotations

import pytest

from custom_components.geekmagic.profiles import StockProProfile

from .test_profiles import FakeTransport

ALBUM = "/filelist?dir=/image/"


def album(*names: str) -> FakeTransport:
    """A Pro whose album lists ``names``."""
    rows = "".join(
        f"<tr><td><a href='/image/{name}'>{name}</a></td><td>68</td></tr>" for name in names
    )
    return FakeTransport(text_by_path={ALBUM: f"<table>{rows}</table>"})


def deleted(transport: FakeTransport) -> list[str]:
    return [path for path, _action in transport.checked if path.startswith("/delete?file=")]


@pytest.mark.asyncio
async def test_keeps_the_album_when_the_upload_is_missing() -> None:
    """A listing without our frame leaves every picture alone."""
    transport = album("holiday.jpg", "cat.jpg")
    profile = StockProProfile(transport)

    with pytest.raises(RuntimeError, match="was not found in the album"):
        await profile.keep_only_image("dashboard.jpg")

    assert deleted(transport) == []


@pytest.mark.asyncio
async def test_deletes_the_other_pictures_when_the_upload_is_there() -> None:
    """The happy path still clears everything but our frame."""
    transport = album("holiday.jpg", "dashboard.jpg", "cat.jpg")
    profile = StockProProfile(transport)

    await profile.keep_only_image("dashboard.jpg")

    assert deleted(transport) == [
        "/delete?file=/image/holiday.jpg",
        "/delete?file=/image/cat.jpg",
    ]


@pytest.mark.asyncio
async def test_an_empty_album_keeps_nothing_and_deletes_nothing() -> None:
    """Nothing to delete is not an error, but our frame is still missing."""
    transport = album()
    profile = StockProProfile(transport)

    with pytest.raises(RuntimeError, match="was not found in the album"):
        await profile.keep_only_image("dashboard.jpg")

    assert deleted(transport) == []
