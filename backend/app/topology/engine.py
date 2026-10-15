"""
Topology & Virtual Display Layout Engine.

Calculates edge adjacency, relative 2D coordinate projections,
and seamless cursor handoff transitions across multi-laptop workspaces.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


@dataclass
class DisplayRect:
    device_id: str
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


class TopologyEngine:
    """Calculates cross-screen cursor handoffs and boundary projections."""

    def __init__(self, displays: Optional[List[DisplayRect]] = None, threshold: float = 60.0):
        self.displays = displays or []
        self.threshold = threshold  # Maximum gap between adjacent screens to allow transition

    def get_display(self, device_id: str) -> Optional[DisplayRect]:
        for d in self.displays:
            if d.device_id == device_id:
                return d
        return None

    def calculate_handoff(
        self,
        current_device_id: str,
        local_x: float,
        local_y: float,
        edge: str,
        is_online: Callable[[str], bool] = lambda _: True,
    ) -> Optional[Tuple[str, float, float]]:
        """
        Calculates cursor handoff destination when hitting an edge.

        Args:
            current_device_id: The ID of the currently active laptop.
            local_x: Current cursor X coordinate on the active screen.
            local_y: Current cursor Y coordinate on the active screen.
            edge: Which edge was crossed ('right', 'left', 'bottom', 'top').
            is_online: Predicate to check if destination device is online.

        Returns:
            (target_device_id, new_local_x, new_local_y) if handoff is valid, else None.
        """
        curr = self.get_display(current_device_id)
        if not curr:
            return None

        virtual_x = curr.x + local_x
        virtual_y = curr.y + local_y

        best_target: Optional[DisplayRect] = None
        best_new_x = 0.0
        best_new_y = 0.0
        min_dist = float("inf")

        if edge == "right":
            target_vx = curr.right
            for d in self.displays:
                if d.device_id == current_device_id:
                    continue
                if not is_online(d.device_id):
                    continue

                # Check if d is to the right of curr within threshold
                dist = abs(d.x - target_vx)
                if dist <= self.threshold:
                    # Check vertical overlap
                    overlap_min = max(curr.y, d.y)
                    overlap_max = min(curr.bottom, d.bottom)
                    if overlap_min <= virtual_y <= overlap_max and dist < min_dist:
                        min_dist = dist
                        best_target = d
                        best_new_x = 0.0
                        best_new_y = max(0.0, min(d.height - 1, virtual_y - d.y))

        elif edge == "left":
            target_vx = curr.x
            for d in self.displays:
                if d.device_id == current_device_id:
                    continue
                if not is_online(d.device_id):
                    continue

                # Check if d is to the left of curr within threshold
                dist = abs(d.right - target_vx)
                if dist <= self.threshold:
                    # Check vertical overlap
                    overlap_min = max(curr.y, d.y)
                    overlap_max = min(curr.bottom, d.bottom)
                    if overlap_min <= virtual_y <= overlap_max and dist < min_dist:
                        min_dist = dist
                        best_target = d
                        best_new_x = max(0.0, d.width - 1)
                        best_new_y = max(0.0, min(d.height - 1, virtual_y - d.y))

        elif edge == "bottom":
            target_vy = curr.bottom
            for d in self.displays:
                if d.device_id == current_device_id:
                    continue
                if not is_online(d.device_id):
                    continue

                # Check if d is below curr within threshold
                dist = abs(d.y - target_vy)
                if dist <= self.threshold:
                    # Check horizontal overlap
                    overlap_min = max(curr.x, d.x)
                    overlap_max = min(curr.right, d.right)
                    if overlap_min <= virtual_x <= overlap_max and dist < min_dist:
                        min_dist = dist
                        best_target = d
                        best_new_x = max(0.0, min(d.width - 1, virtual_x - d.x))
                        best_new_y = 0.0

        elif edge == "top":
            target_vy = curr.y
            for d in self.displays:
                if d.device_id == current_device_id:
                    continue
                if not is_online(d.device_id):
                    continue

                # Check if d is above curr within threshold
                dist = abs(d.bottom - target_vy)
                if dist <= self.threshold:
                    # Check horizontal overlap
                    overlap_min = max(curr.x, d.x)
                    overlap_max = min(curr.right, d.right)
                    if overlap_min <= virtual_x <= overlap_max and dist < min_dist:
                        min_dist = dist
                        best_target = d
                        best_new_x = max(0.0, min(d.width - 1, virtual_x - d.x))
                        best_new_y = max(0.0, d.height - 1)

        if best_target:
            return (best_target.device_id, best_new_x, best_new_y)
        return None
