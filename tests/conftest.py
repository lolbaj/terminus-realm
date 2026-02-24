"""
Pytest configuration and shared fixtures for Terminus Realm tests.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.ecs import EntityManager
from core.engine import GameEngine
from entities.entities import EntityManagerWrapper, EntityFactory
from world.chunk_manager import ChunkManager
from data.loader import DATA_LOADER


@pytest.fixture
def entity_manager():
    """Create a fresh EntityManager for testing."""
    return EntityManager()


@pytest.fixture
def entity_factory(entity_manager):
    """Create an EntityFactory tied to the entity_manager fixture."""
    return EntityFactory(entity_manager)


@pytest.fixture
def entity_wrapper(entity_manager):
    """Create an EntityManagerWrapper for testing."""
    return EntityManagerWrapper(entity_manager)


@pytest.fixture
def game_engine():
    """Create a GameEngine instance for integration tests."""
    engine = GameEngine()
    engine.initialize_game()
    return engine


@pytest.fixture
def chunk_manager():
    """Create a ChunkManager with default settings."""
    return ChunkManager(chunk_size=32, buffer_radius=1)


@pytest.fixture
def data_loader():
    """Get the shared DATA_LOADER instance."""
    return DATA_LOADER


@pytest.fixture
def player_entity(entity_wrapper):
    """Create a player entity at position (5, 5)."""
    return entity_wrapper.factory.create_player(5, 5)


@pytest.fixture
def monster_entity(entity_factory):
    """Create a goblin monster entity at position (10, 10)."""
    return entity_factory.create_monster(10, 10, "goblin")
