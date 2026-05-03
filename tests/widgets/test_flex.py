"""Direct unit tests for the in-tree flexbox shim (widgets/_flex.py).

The shim is also exercised indirectly via test_flex_layout.py and
test_components.py, but those go through higher-level helpers. These tests
target the public surface (Node / Edge / AUTO / PCT / enums) so a
regression in the layout solver fails here with a small, focused test.
"""

from __future__ import annotations

import pytest

from custom_components.geekmagic.widgets._flex import (
    AUTO,
    PCT,
    AlignItems,
    Edge,
    FlexDirection,
    JustifyContent,
    Node,
)


class TestSentinels:
    def test_auto_repr(self) -> None:
        assert repr(AUTO) == "AUTO"

    def test_pct_rmul_returns_percent(self) -> None:
        p = 50 * PCT
        # 50% of 200 == 100, exercised through resolution
        root = Node(flex_direction=FlexDirection.ROW, size=(200, 100))
        root.add(Node(key="a", size=(p, 100 * PCT)))
        root.compute_layout()
        assert root.find("/a").get_box(Edge.CONTENT).width == 100

    def test_pct_supports_float(self) -> None:
        root = Node(flex_direction=FlexDirection.ROW, size=(200, 100))
        root.add(Node(key="a", size=(12.5 * PCT, 100 * PCT)))
        root.compute_layout()
        assert root.find("/a").get_box(Edge.CONTENT).width == 25.0


class TestNodeConstruction:
    def test_defaults(self) -> None:
        n = Node(size=(10, 10))
        assert n.flex_direction is FlexDirection.ROW
        assert n.justify_content is JustifyContent.START
        assert n.align_items is AlignItems.STRETCH
        assert n.gap == 0
        assert n.flex_grow == 0
        assert n.children == []

    def test_unsupported_kwargs_raise(self) -> None:
        with pytest.raises(NotImplementedError, match="padding"):
            Node(size=(10, 10), padding=5)

    def test_add_returns_self_for_chaining(self) -> None:
        root = Node(size=(10, 10))
        result = root.add(Node(key="a", size=(5, 5)))
        assert result is root
        assert len(root.children) == 1


class TestFind:
    def test_finds_direct_child(self) -> None:
        root = Node(size=(10, 10))
        a = Node(key="a", size=(5, 10))
        root.add(a)
        assert root.find("/a") is a

    def test_path_must_start_with_slash(self) -> None:
        root = Node(size=(10, 10))
        root.add(Node(key="a", size=(5, 10)))
        with pytest.raises(ValueError, match="must start with '/'"):
            root.find("a")

    def test_missing_key_raises(self) -> None:
        root = Node(size=(10, 10))
        root.add(Node(key="a", size=(5, 10)))
        with pytest.raises(KeyError):
            root.find("/missing")


class TestComputeLayoutBasics:
    def test_root_must_have_size(self) -> None:
        root = Node()
        with pytest.raises(ValueError, match="explicit size"):
            root.compute_layout()

    def test_root_size_must_be_concrete(self) -> None:
        root = Node(size=(AUTO, 100))
        with pytest.raises(ValueError, match="concrete pixels"):
            root.compute_layout()

    def test_no_children_is_noop(self) -> None:
        root = Node(size=(100, 50))
        root.compute_layout()  # must not raise
        assert root.get_box(Edge.CONTENT).width == 100
        assert root.get_box(Edge.CONTENT).height == 50


class TestRowJustifyContent:
    def _row(self, justify: JustifyContent) -> dict[str, tuple[float, float]]:
        root = Node(
            flex_direction=FlexDirection.ROW,
            justify_content=justify,
            align_items=AlignItems.CENTER,
            size=(300, 100),
        )
        # 3 fixed children, 30 each = 90 px used, 210 px free
        for i, w in enumerate([30, 30, 30]):
            root.add(Node(key=f"c{i}", size=(w, 50)))
        root.compute_layout()
        return {
            f"c{i}": (root.find(f"/c{i}").get_box().x, root.find(f"/c{i}").get_box().width)
            for i in range(3)
        }

    def test_start(self) -> None:
        b = self._row(JustifyContent.START)
        assert b["c0"][0] == 0
        assert b["c1"][0] == 30
        assert b["c2"][0] == 60

    def test_end(self) -> None:
        b = self._row(JustifyContent.END)
        assert b["c0"][0] == 210  # 300 - 90
        assert b["c1"][0] == 240
        assert b["c2"][0] == 270

    def test_center(self) -> None:
        b = self._row(JustifyContent.CENTER)
        assert b["c0"][0] == 105  # (300 - 90) / 2
        assert b["c1"][0] == 135
        assert b["c2"][0] == 165

    def test_space_between(self) -> None:
        b = self._row(JustifyContent.SPACE_BETWEEN)
        # 210 free / 2 gaps = 105 each
        assert b["c0"][0] == 0
        assert b["c1"][0] == 135  # 30 + 105
        assert b["c2"][0] == 270  # 30 + 105 + 30 + 105

    def test_space_around(self) -> None:
        b = self._row(JustifyContent.SPACE_AROUND)
        # 210 free / 3 children = 70 each, half-gap 35 at start
        assert b["c0"][0] == 35
        assert b["c1"][0] == 135  # 35 + 30 + 70
        assert b["c2"][0] == 235  # 135 + 30 + 70

    def test_space_between_single_child_no_zero_division(self) -> None:
        root = Node(
            flex_direction=FlexDirection.ROW,
            justify_content=JustifyContent.SPACE_BETWEEN,
            size=(200, 100),
        )
        root.add(Node(key="only", size=(30, 50)))
        root.compute_layout()  # must not raise
        assert root.find("/only").get_box().x == 0


class TestAlignItems:
    def _row_align(self, align: AlignItems) -> tuple[float, float]:
        root = Node(
            flex_direction=FlexDirection.ROW,
            align_items=align,
            size=(100, 200),
        )
        root.add(Node(key="a", size=(50, 60)))
        root.compute_layout()
        box = root.find("/a").get_box()
        return (box.y, box.height)

    def test_start(self) -> None:
        assert self._row_align(AlignItems.START) == (0, 60)

    def test_center(self) -> None:
        assert self._row_align(AlignItems.CENTER) == (70, 60)  # (200 - 60) / 2

    def test_end(self) -> None:
        assert self._row_align(AlignItems.END) == (140, 60)  # 200 - 60

    def test_stretch_overrides_size(self) -> None:
        # STRETCH ignores the cross-axis spec and fills the container.
        assert self._row_align(AlignItems.STRETCH) == (0, 200)

    def test_stretch_with_auto_cross(self) -> None:
        root = Node(
            flex_direction=FlexDirection.ROW,
            align_items=AlignItems.STRETCH,
            size=(100, 200),
        )
        root.add(Node(key="a", size=(50, AUTO)))
        root.compute_layout()
        assert root.find("/a").get_box().height == 200


class TestFlexGrow:
    def test_single_grow_consumes_free_space(self) -> None:
        root = Node(flex_direction=FlexDirection.ROW, size=(200, 50))
        root.add(Node(key="fixed", size=(40, 50)))
        root.add(Node(key="grow", size=(AUTO, 50), flex_grow=1))
        root.compute_layout()
        assert root.find("/grow").get_box().width == 160

    def test_two_grow_share_equally(self) -> None:
        root = Node(flex_direction=FlexDirection.ROW, size=(200, 50))
        root.add(Node(key="a", size=(AUTO, 50), flex_grow=1))
        root.add(Node(key="b", size=(AUTO, 50), flex_grow=1))
        root.compute_layout()
        assert root.find("/a").get_box().width == 100
        assert root.find("/b").get_box().width == 100

    def test_grow_proportional_to_weight(self) -> None:
        root = Node(flex_direction=FlexDirection.ROW, size=(300, 50))
        root.add(Node(key="a", size=(AUTO, 50), flex_grow=1))
        root.add(Node(key="b", size=(AUTO, 50), flex_grow=2))
        root.compute_layout()
        # 300 free / 3 weight = 100 per unit
        assert root.find("/a").get_box().width == 100
        assert root.find("/b").get_box().width == 200

    def test_grow_with_fixed_and_gap(self) -> None:
        root = Node(flex_direction=FlexDirection.ROW, gap=10, size=(200, 50))
        root.add(Node(key="left", size=(30, 50)))
        root.add(Node(key="mid", size=(AUTO, 50), flex_grow=1))
        root.add(Node(key="right", size=(40, 50)))
        root.compute_layout()
        # 200 - 30 - 40 - 2*10 = 110
        assert root.find("/mid").get_box().width == 110
        # mid starts after left + gap
        assert root.find("/mid").get_box().x == 40
        # right starts after mid + gap
        assert root.find("/right").get_box().x == 160


class TestColumnDirection:
    def test_axis_swap(self) -> None:
        root = Node(
            flex_direction=FlexDirection.COLUMN,
            align_items=AlignItems.STRETCH,
            size=(100, 200),
        )
        root.add(Node(key="a", size=(100 * PCT, 30)))
        root.add(Node(key="b", size=(100 * PCT, AUTO), flex_grow=1))
        root.compute_layout()
        a, b = root.find("/a").get_box(), root.find("/b").get_box()
        assert a.x == 0 and a.y == 0 and a.width == 100 and a.height == 30
        assert b.x == 0 and b.y == 30 and b.width == 100 and b.height == 170


class TestGap:
    def test_gap_adds_between_children_only(self) -> None:
        root = Node(flex_direction=FlexDirection.ROW, gap=20, size=(200, 50))
        root.add(Node(key="a", size=(30, 50)))
        root.add(Node(key="b", size=(30, 50)))
        root.add(Node(key="c", size=(30, 50)))
        root.compute_layout()
        assert root.find("/a").get_box().x == 0
        assert root.find("/b").get_box().x == 50  # 30 + 20
        assert root.find("/c").get_box().x == 100  # 50 + 30 + 20

    def test_gap_combines_with_space_between(self) -> None:
        root = Node(
            flex_direction=FlexDirection.ROW,
            justify_content=JustifyContent.SPACE_BETWEEN,
            gap=10,
            size=(200, 50),
        )
        root.add(Node(key="a", size=(30, 50)))
        root.add(Node(key="b", size=(30, 50)))
        root.compute_layout()
        # 200 - 60 = 140 used by gap+extra; gap=10, extra_gap=130
        assert root.find("/a").get_box().x == 0
        assert root.find("/b").get_box().x == 170
