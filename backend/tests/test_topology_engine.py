"""Tests for cross-screen edge adjacency and seamless cursor handoff."""

import pytest
from app.topology.engine import TopologyEngine, DisplayRect


def test_horizontal_side_by_side_handoff():
    # Laptop 1 (1920x1080) at (0, 0)
    # Laptop 2 (2560x1440) at (1920, 0) immediately to the right
    d1 = DisplayRect("laptop-1", x=0.0, y=0.0, width=1920.0, height=1080.0)
    d2 = DisplayRect("laptop-2", x=1920.0, y=0.0, width=2560.0, height=1440.0)

    engine = TopologyEngine([d1, d2])

    # 1. Laptop 1 right edge -> Laptop 2 left edge
    result = engine.calculate_handoff("laptop-1", local_x=1919.0, local_y=540.0, edge="right")
    assert result is not None
    target_id, new_x, new_y = result
    assert target_id == "laptop-2"
    assert new_x == 0.0
    assert new_y == 540.0

    # 2. Laptop 2 left edge -> Laptop 1 right edge
    result = engine.calculate_handoff("laptop-2", local_x=0.0, local_y=720.0, edge="left")
    assert result is not None
    target_id, new_x, new_y = result
    assert target_id == "laptop-1"
    assert new_x == 1919.0
    assert new_y == 720.0


def test_vertical_stacked_handoff():
    # Laptop 1 on top at (0, 0)
    # Laptop 2 on bottom at (0, 1080)
    d1 = DisplayRect("laptop-1", x=0.0, y=0.0, width=1920.0, height=1080.0)
    d2 = DisplayRect("laptop-2", x=0.0, y=1080.0, width=1920.0, height=1080.0)

    engine = TopologyEngine([d1, d2])

    # Laptop 1 bottom -> Laptop 2 top
    result = engine.calculate_handoff("laptop-1", local_x=960.0, local_y=1079.0, edge="bottom")
    assert result is not None
    target_id, new_x, new_y = result
    assert target_id == "laptop-2"
    assert new_x == 960.0
    assert new_y == 0.0

    # Laptop 2 top -> Laptop 1 bottom
    result = engine.calculate_handoff("laptop-2", local_x=960.0, local_y=0.0, edge="top")
    assert result is not None
    target_id, new_x, new_y = result
    assert target_id == "laptop-1"
    assert new_x == 960.0
    assert new_y == 1079.0


def test_partial_overlap_rejection():
    # Laptop 1 at (0, 0, 1920, 1080)
    # Laptop 2 at (1920, 800, 1920, 1080) - only overlaps between Y=800 and Y=1080
    d1 = DisplayRect("laptop-1", x=0.0, y=0.0, width=1920.0, height=1080.0)
    d2 = DisplayRect("laptop-2", x=1920.0, y=800.0, width=1920.0, height=1080.0)

    engine = TopologyEngine([d1, d2])

    # Cursor at Y=200 has no adjacent screen on the right
    result_none = engine.calculate_handoff("laptop-1", local_x=1919.0, local_y=200.0, edge="right")
    assert result_none is None

    # Cursor at Y=900 overlaps and can transition
    result_ok = engine.calculate_handoff("laptop-1", local_x=1919.0, local_y=900.0, edge="right")
    assert result_ok is not None
    target_id, new_x, new_y = result_ok
    assert target_id == "laptop-2"
    assert new_x == 0.0
    assert new_y == 100.0  # 900 - 800


def test_offline_destination_blocked():
    d1 = DisplayRect("laptop-1", x=0.0, y=0.0, width=1920.0, height=1080.0)
    d2 = DisplayRect("laptop-2", x=1920.0, y=0.0, width=1920.0, height=1080.0)

    engine = TopologyEngine([d1, d2])

    def is_online(device_id: str) -> bool:
        return device_id == "laptop-1"  # laptop-2 is offline

    result = engine.calculate_handoff(
        "laptop-1", local_x=1919.0, local_y=540.0, edge="right", is_online=is_online
    )
    assert result is None  # Does not transition to offline laptop
