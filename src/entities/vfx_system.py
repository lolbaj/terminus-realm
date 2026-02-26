"""
VFX system for managing transient visual effects.
"""

from typing import Tuple
from core.ecs import EntityManager
from entities.components import Position, VFX


class VFXSystem:
    """System for managing transient visual effects like floating damage numbers and hit flashes."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager

    def add_floating_text(
        self,
        x: int,
        y: int,
        text: str,
        color: Tuple[int, int, int] = (255, 255, 255),
        duration: float = 1.0,
    ):
        """Add floating text at a position."""
        vfx_eid = self.entity_manager.create_entity()
        self.entity_manager.add_component(vfx_eid, Position(x=x, y=y))
        self.entity_manager.add_component(
            vfx_eid,
            VFX(
                type="float_text",
                text=text,
                color=color,
                duration=duration,
                time_left=duration,
                y_offset=0.0,
            ),
        )
        return vfx_eid

    def add_hit_flash(
        self,
        target_eid: int,
        color: Tuple[int, int, int] = (255, 255, 255),
        duration: float = 0.2,
    ):
        """Add a hit flash effect to an entity."""
        # We need a position to render the flash if it's separate,
        # or we just mark the target entity as flashing.
        # For simplicity, we create a VFX entity that references the target.
        vfx_eid = self.entity_manager.create_entity()
        self.entity_manager.add_component(
            vfx_eid,
            VFX(
                type="flash",
                color=color,
                duration=duration,
                time_left=duration,
                target_eid=target_eid,
            ),
        )
        return vfx_eid

    def update(self, dt: float):
        """Update all active VFX entities."""
        vfx_components = self.entity_manager.get_all_entities_with_component(VFX)

        for eid in list(vfx_components):
            vfx = self.entity_manager.get_component(eid, VFX)
            if not vfx:
                continue

            vfx.time_left -= dt

            # Update specific effect logic
            if vfx.type == "float_text":
                # Float upwards
                vfx.y_offset -= 1.5 * dt  # Move up 1.5 cells per second

            # Remove expired VFX
            if vfx.time_left <= 0:
                self.entity_manager.destroy_entity(eid)
