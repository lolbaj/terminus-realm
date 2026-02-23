"""
Terminal rendering engine for the Map Editor.
Handles double-buffered output, diffing, and color escape codes.
Uses numpy for performance and robust rendering.
"""

import sys
import numpy as np
import shutil


class Renderer:
    def __init__(self, cols: int, rows: int, cell_width: int = 2):
        self.cols = cols
        self.rows = rows
        self.cell_width = cell_width

        # Buffer shape based on terminal cells
        self.max_shape = (rows + 10, (cols // 1) + 10)  # Over-allocate for safety

        self.screen_buffer = np.full(self.max_shape, " ", dtype=object)
        self.fg_buffer = np.full((*self.max_shape, 3), -1, dtype=np.int16)
        self.bg_buffer = np.full((*self.max_shape, 3), -1, dtype=np.int16)

        self._prev_screen = np.full(self.max_shape, " ", dtype=object)
        self._prev_fg = np.full((*self.max_shape, 3), -1, dtype=np.int16)
        self._prev_bg = np.full((*self.max_shape, 3), -1, dtype=np.int16)

    def resize(self, cols: int, rows: int, cell_width: int = None):
        self.cols = cols
        self.rows = rows
        if cell_width is not None:
            self.cell_width = cell_width

        self.screen_buffer.fill(" ")
        self.fg_buffer.fill(-1)
        self.bg_buffer.fill(-1)
        self._prev_screen.fill(" ")
        self._prev_fg.fill(-1)
        self._prev_bg.fill(-1)

    def clear(self):
        self.screen_buffer.fill(" ")
        self.fg_buffer.fill(-1)
        self.bg_buffer.fill(-1)

    def set_cell(self, x: int, y: int, char: str, fg=(-1, -1, -1), bg=(-1, -1, -1)):
        # Cell-based coordinates
        if (
            0 <= y < self.screen_buffer.shape[0]
            and 0 <= x < self.screen_buffer.shape[1]
        ):
            # Do NOT normalize here, let flush handle padding based on visual width
            if fg is None:
                fg = (-1, -1, -1)
            if bg is None:
                bg = (-1, -1, -1)

            self.screen_buffer[y, x] = char
            self.fg_buffer[y, x] = fg
            self.bg_buffer[y, x] = bg

    def draw_text(self, x: int, y: int, text: str, fg=(255, 255, 255), bg=(-1, -1, -1)):
        if self.cell_width == 2:
            if len(text) % 2 != 0:
                text += " "
            pairs = [text[i : i + 2] for i in range(0, len(text), 2)]
            for i, pair in enumerate(pairs):
                self.set_cell(x + i, y, pair, fg, bg)
        else:
            for i, char in enumerate(text):
                self.set_cell(x + i, y, char, fg, bg)

    def draw_box(
        self, x: int, y: int, w: int, h: int, fg=(100, 100, 100), bg=(-1, -1, -1)
    ):
        horizontal = "==" if self.cell_width == 2 else "-"
        vertical = "||" if self.cell_width == 2 else "|"
        for i in range(w):
            self.set_cell(x + i, y, horizontal, fg, bg)
            self.set_cell(x + i, y + h - 1, horizontal, fg, bg)
        for j in range(h):
            self.set_cell(x, y + j, vertical, fg, bg)
            self.set_cell(x + w - 1, y + j, vertical, fg, bg)

    def flush(self):
        output_parts = []
        last_fg = (-1, -1, -1)
        last_bg = (-1, -1, -1)

        v_cursor_y = -1
        v_cursor_x = -1

        max_cols = shutil.get_terminal_size().columns
        max_rows = shutil.get_terminal_size().lines

        w = min(self.cols // self.cell_width, self.screen_buffer.shape[1])
        h = min(self.rows, self.screen_buffer.shape[0])

        for y in range(h):
            for x in range(w):
                char = str(self.screen_buffer[y, x])
                fg = tuple(self.fg_buffer[y, x])
                bg = tuple(self.bg_buffer[y, x])

                prev_char = str(self._prev_screen[y, x])
                prev_fg = tuple(self._prev_fg[y, x])
                prev_bg = tuple(self._prev_bg[y, x])

                if char != prev_char or fg != prev_fg or bg != prev_bg:
                    screen_col = x * self.cell_width + 1

                    if screen_col > max_cols or y >= max_rows:
                        continue

                    # Move cursor if needed
                    if y != v_cursor_y or x != v_cursor_x:
                        output_parts.append(f"\033[{y+1};{screen_col}H")

                    # Colors
                    if fg != last_fg:
                        if fg[0] == -1:
                            output_parts.append("\033[39m")
                        else:
                            output_parts.append(f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m")
                        last_fg = fg

                    if bg != last_bg:
                        if bg[0] == -1:
                            output_parts.append("\033[49m")
                        else:
                            output_parts.append(f"\033[48;2;{bg[0]};{bg[1]};{bg[2]}m")
                        last_bg = bg

                    # Emoji-aware padding logic
                    if self.cell_width == 2:
                        if len(char) == 1:
                            if ord(char) > 126:  # Emoji/Wide char
                                output_parts.append(char)
                                # Wide chars consume 2 columns, force cursor re-sync for next cell
                                v_cursor_x = -1
                            else:  # ASCII char
                                output_parts.append(char + " ")
                                v_cursor_x = x * self.cell_width + 3  # x+1 pos
                        else:
                            # Already 2+ chars (Box drawing or text)
                            output_parts.append(char[:2])
                            v_cursor_x = x * self.cell_width + 3
                    else:
                        # Zoom out mode (cell_width 1)
                        if ord(char[0]) > 126:
                            output_parts.append("·")
                        else:
                            output_parts.append(char[0])
                        v_cursor_x = x * self.cell_width + 2

                    v_cursor_y = y

        # Sync buffers
        self._prev_screen[:h, :w] = self.screen_buffer[:h, :w]
        self._prev_fg[:h, :w] = self.fg_buffer[:h, :w]
        self._prev_bg[:h, :w] = self.bg_buffer[:h, :w]

        if output_parts:
            output_parts.append("\033[0m")
            sys.stdout.write("".join(output_parts))
            sys.stdout.flush()
