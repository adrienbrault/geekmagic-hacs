# Layouts

A view's layout splits the 240×240 screen into slots; each slot holds one widget. Pick it in the View Editor's **Layout** picker. Widgets adapt to the slot size they get (see every widget at every size in [Widgets](widgets.md)).

There are 19 layouts. The ID column is the value stored in the view config.

## Fullscreen & grids

<p align="center">
  <img src="../samples/layouts/layout_fullscreen.png" alt="Fullscreen" width="200">
  <img src="../samples/layouts/layout_grid_2x2.png" alt="Grid 2x2" width="200">
  <img src="../samples/layouts/layout_grid_2x3.png" alt="Grid 2x3" width="200">
  <img src="../samples/layouts/layout_grid_3x2.png" alt="Grid 3x2" width="200">
  <img src="../samples/layouts/layout_grid_3x3.png" alt="Grid 3x3" width="200">
</p>

| Layout | ID | Slots | Description |
|--------|----|:-----:|-------------|
| Fullscreen | `fullscreen` | 1 | Single widget fills the entire display |
| Grid 2x2 | `grid_2x2` | 4 | 2×2 grid of equal widgets |
| Grid 2x3 | `grid_2x3` | 6 | 2 rows, 3 columns |
| Grid 3x2 | `grid_3x2` | 6 | 3 rows, 2 columns |
| Grid 3x3 | `grid_3x3` | 9 | 3×3 grid of equal widgets |

## Splits

<p align="center">
  <img src="../samples/layouts/layout_split_horizontal.png" alt="Split horizontal" width="200">
  <img src="../samples/layouts/layout_split_vertical.png" alt="Split vertical" width="200">
  <img src="../samples/layouts/layout_split_h_1_2.png" alt="Split 1:2" width="200">
  <img src="../samples/layouts/layout_split_h_2_1.png" alt="Split 2:1" width="200">
</p>

| Layout | ID | Slots | Description |
|--------|----|:-----:|-------------|
| Split horizontal | `split_horizontal` | 2 | Left/right, side by side |
| Split vertical | `split_vertical` | 2 | Top/bottom, stacked |
| Split 1:2 | `split_h_1_2` | 2 | Narrow left (1/3), wide right (2/3) |
| Split 2:1 | `split_h_2_1` | 2 | Wide left (2/3), narrow right (1/3) |

## Columns & rows

<p align="center">
  <img src="../samples/layouts/layout_three_column.png" alt="Three columns" width="200">
  <img src="../samples/layouts/layout_three_row.png" alt="Three rows" width="200">
</p>

| Layout | ID | Slots | Description |
|--------|----|:-----:|-------------|
| Three columns | `three_column` | 3 | 3 vertical columns |
| Three rows | `three_row` | 3 | 3 horizontal rows |

## Hero

<p align="center">
  <img src="../samples/layouts/layout_hero.png" alt="Hero" width="200">
  <img src="../samples/layouts/layout_hero_simple.png" alt="Hero simple" width="200">
  <img src="../samples/layouts/layout_hero_corner_tl.png" alt="Hero corner TL" width="200">
  <img src="../samples/layouts/layout_hero_corner_tr.png" alt="Hero corner TR" width="200">
  <img src="../samples/layouts/layout_hero_corner_bl.png" alt="Hero corner BL" width="200">
  <img src="../samples/layouts/layout_hero_corner_br.png" alt="Hero corner BR" width="200">
</p>

| Layout | ID | Slots | Description |
|--------|----|:-----:|-------------|
| Hero | `hero` | 4 | Large hero + 3 footer widgets |
| Hero simple | `hero_simple` | 2 | Large hero + 1 footer widget |
| Hero corner TL | `hero_corner_tl` | 6 | 2×2 hero top-left + 5 small widgets |
| Hero corner TR | `hero_corner_tr` | 6 | 2×2 hero top-right + 5 small widgets |
| Hero corner BL | `hero_corner_bl` | 6 | 2×2 hero bottom-left + 5 small widgets |
| Hero corner BR | `hero_corner_br` | 6 | 2×2 hero bottom-right + 5 small widgets |

## Sidebars

<p align="center">
  <img src="../samples/layouts/layout_sidebar_left.png" alt="Sidebar left" width="200">
  <img src="../samples/layouts/layout_sidebar_right.png" alt="Sidebar right" width="200">
</p>

| Layout | ID | Slots | Description |
|--------|----|:-----:|-------------|
| Sidebar left | `sidebar_left` | 4 | Wide left panel + 3 rows on the right |
| Sidebar right | `sidebar_right` | 4 | 3 rows on the left + wide right panel |
