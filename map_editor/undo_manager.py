"""
Undo and redo management for the Map Editor.
Supports multi-layer undo.
"""

from typing import List, Dict
from .models import UndoAction


class UndoManager:
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.undo_stack: List[List[UndoAction]] = []
        self.redo_stack: List[List[UndoAction]] = []
        self._current_group: List[UndoAction] = None

    def start_group(self):
        self._current_group = []

    def end_group(self):
        if self._current_group:
            self.undo_stack.append(self._current_group)
            self.redo_stack.clear()
            if len(self.undo_stack) > self.max_history:
                self.undo_stack.pop(0)
        self._current_group = None

    def push_action(self, x: int, y: int, old_char: str, new_char: str, layer: str):
        if old_char == new_char:
            return

        action = UndoAction(x, y, old_char, new_char, layer)
        if self._current_group is not None:
            self._current_group.append(action)
        else:
            self.undo_stack.append([action])
            self.redo_stack.clear()
            if len(self.undo_stack) > self.max_history:
                self.undo_stack.pop(0)

    def undo(self, layers: Dict[str, List[List[str]]]) -> bool:
        if not self.undo_stack:
            return False

        group = self.undo_stack.pop()
        # To redo an undo, we need to re-apply the new_chars
        self.redo_stack.append(group)

        for action in reversed(group):
            layers[action.layer][action.y][action.x] = action.old_char
        return True

    def redo(self, layers: Dict[str, List[List[str]]]) -> bool:
        if not self.redo_stack:
            return False

        group = self.redo_stack.pop()
        self.undo_stack.append(group)

        for action in group:
            layers[action.layer][action.y][action.x] = action.new_char
        return True

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._current_group = None
