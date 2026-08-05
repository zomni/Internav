import pytest

from app.application.svg_analyzer import WalkabilityMask, compute_walkability, parse_svg_dimensions
from app.domain.errors import DomainValidationError

BOX = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000">'
    b'<rect width="1000" height="1000" fill="white"/>'
    b'<rect x="200" y="200" width="600" height="600" fill="none" stroke="black"/>'
    b"</svg>"
)


def test_parse_svg_dimensions() -> None:
    assert parse_svg_dimensions(b'<svg width="2000" height="3000"></svg>') == (2000, 3000)


def test_parse_svg_dimensions_missing() -> None:
    with pytest.raises(DomainValidationError):
        parse_svg_dimensions(b"<svg></svg>")


def test_parse_svg_dimensions_ignores_child_attributes() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="3000">'
        b'<rect width="1600" height="2600" fill="white"/>'
        b"</svg>"
    )
    assert parse_svg_dimensions(svg) == (2000, 3000)


def test_closed_box_walkability() -> None:
    mask = compute_walkability(BOX, width=1000, height=1000, cell_size=100)
    assert mask.rows == 10
    assert mask.cols == 10
    assert mask.get(0, 0) is False
    assert mask.get(2, 2) is False
    assert mask.get(4, 4) is True
    assert mask.get(5, 5) is True
    walkable_count = sum(mask.walkable)
    assert walkable_count == 16


def test_gray_fill_counts_as_wall() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000">'
        b'<rect width="1000" height="1000" fill="white"/>'
        b'<rect x="200" y="200" width="600" height="600" fill="none" stroke="black"/>'
        b'<rect x="300" y="300" width="100" height="100" fill="#D9D9D9"/>'
        b"</svg>"
    )
    mask = compute_walkability(svg, width=1000, height=1000, cell_size=100)
    assert mask.get(3, 3) is False
    assert mask.get(4, 4) is True


def test_interior_wall_blocks_cells() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000">'
        b'<rect width="1000" height="1000" fill="white"/>'
        b'<rect x="200" y="200" width="600" height="600" fill="none" stroke="black"/>'
        b'<path d="M550 200V800" stroke="black"/>'
        b"</svg>"
    )
    mask = compute_walkability(svg, width=1000, height=1000, cell_size=100)
    assert mask.get(4, 5) is False
    assert mask.get(4, 4) is True
    assert mask.get(4, 6) is True


def test_doorway_does_not_flood_interior() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000">'
        b'<rect width="1000" height="1000" fill="white"/>'
        b'<path d="M200 200H800V400" stroke="black"/>'
        b'<path d="M800 500V800H200V200" stroke="black"/>'
        b"</svg>"
    )
    mask = compute_walkability(svg, width=1000, height=1000, cell_size=100)
    assert mask.get(0, 0) is False
    assert mask.get(4, 4) is True
    assert mask.get(4, 5) is True
    assert mask.get(6, 6) is True


def test_walkability_mask_dataclass() -> None:
    mask = WalkabilityMask(rows=2, cols=3, walkable=[True, False, True, False, True, True])
    assert mask.get(1, 2) is True
    assert mask.get(0, 1) is False


def test_compute_walkability_invalid_size() -> None:
    with pytest.raises(DomainValidationError):
        compute_walkability(BOX, width=0, height=1000, cell_size=100)
