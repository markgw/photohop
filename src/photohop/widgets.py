"""Reusable Pyglet widgets used by PhotoHop."""
import os
import time
from pathlib import Path

import pyglet


class DirectoryPicker:
    """A small, keyboard-friendly directory browser rendered with Pyglet."""

    WIDTH = 760
    HEIGHT = 560
    HEADER_HEIGHT = 112
    FOOTER_HEIGHT = 72
    ROW_HEIGHT = 38
    BACKGROUND = (25, 28, 35, 255)
    PANEL = (35, 39, 48, 255)
    TEXT = (235, 238, 244, 255)
    MUTED = (155, 164, 178, 255)
    ACCENT = (67, 117, 207, 255)

    def __init__(self, initialdir):
        self.window = pyglet.window.Window(
            width=self.WIDTH,
            height=self.HEIGHT,
            caption="Choose a photo folder",
            resizable=True,
            vsync=True,
        )
        self.current_path = os.path.abspath(os.path.expanduser(initialdir))
        if not os.path.isdir(self.current_path):
            self.current_path = str(Path.home())
        self.result = None
        self.finished = False
        self.entries = []
        self.selected_index = None
        self.scroll = 0
        self.status = "Choose a folder, then select it or double-click to open it."
        self._last_click = (None, 0.0)
        self._elements = []
        self._batch = pyglet.graphics.Batch()
        self._refresh_entries()

        @self.window.event
        def on_draw():
            self.window.clear()
            self._batch.draw()

        @self.window.event
        def on_resize(width, height):
            self._rebuild()

        @self.window.event
        def on_mouse_press(x, y, button, modifiers):
            if button == pyglet.window.mouse.LEFT:
                self._on_click(x, y)

        @self.window.event
        def on_mouse_scroll(x, y, scroll_x, scroll_y):
            self._scroll_by(int(scroll_y))

        @self.window.event
        def on_key_press(symbol, modifiers):
            if symbol == pyglet.window.key.ESCAPE:
                self._finish(None)
            elif symbol == pyglet.window.key.ENTER:
                self._finish(self.current_path)
            elif symbol == pyglet.window.key.BACKSPACE:
                self._navigate(os.path.dirname(self.current_path))
            elif symbol == pyglet.window.key.HOME:
                self._navigate(str(Path.home()))
            elif symbol == pyglet.window.key.UP:
                self._move_selection(-1)
            elif symbol == pyglet.window.key.DOWN:
                self._move_selection(1)
            elif symbol == pyglet.window.key.RIGHT:
                if self.selected_index is not None:
                    self._navigate(os.path.join(
                        self.current_path, self.entries[self.selected_index]
                    ))
            elif symbol == pyglet.window.key.LEFT:
                self._navigate(os.path.dirname(self.current_path))
            elif symbol == pyglet.window.key.PAGEUP:
                self._scroll_by(1)
            elif symbol == pyglet.window.key.PAGEDOWN:
                self._scroll_by(-1)

        @self.window.event
        def on_close():
            if not self.finished:
                self.finished = True
                self.result = None
                pyglet.app.exit()

        self._rebuild()

    def _finish(self, result):
        if self.finished:
            return
        self.finished = True
        self.result = result
        self.window.close()
        pyglet.app.exit()

    def _refresh_entries(self):
        try:
            with os.scandir(self.current_path) as directory:
                self.entries = sorted(
                    (
                        entry.name for entry in directory
                        if not entry.name.startswith(".")
                        and entry.is_dir()
                    ),
                    key=str.casefold,
                )
            self.status = (
                "Choose a folder, then select it or double-click to open it."
            )
        except OSError as error:
            self.entries = []
            self.status = "Cannot read this folder: {}".format(error)
        self.selected_index = 0 if self.entries else None
        self.scroll = 0

    def _navigate(self, path):
        if not path:
            return
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            self.status = "That folder is no longer available."
            self._rebuild()
            return
        self.current_path = path
        self._refresh_entries()
        self._rebuild()

    def _clear_elements(self):
        for element in self._elements:
            element.delete()
        self._elements.clear()
        self._batch = pyglet.graphics.Batch()

    def _rectangle(self, x, y, width, height, color):
        shape = pyglet.shapes.Rectangle(
            x, y, width, height, color=color, batch=self._batch
        )
        self._elements.append(shape)

    def _label(self, text, x, y, *, size=12, color=None, bold=False,
               anchor_x="left"):
        label = pyglet.text.Label(
            text,
            x=x,
            y=y,
            font_name="Arial",
            font_size=size,
            weight="bold" if bold else "normal",
            color=color or self.TEXT,
            anchor_x=anchor_x,
            anchor_y="center",
            batch=self._batch,
        )
        self._elements.append(label)

    def _button(self, text, x, y, width, *, active=False):
        color = self.ACCENT if active else (55, 61, 73, 255)
        self._rectangle(x, y, width, 36, color)
        self._label(text, x + width // 2, y + 18, size=12,
                    color=self.TEXT, bold=True, anchor_x="center")

    def _rebuild(self):
        self._clear_elements()
        width, height = self.window.width, self.window.height
        self._rectangle(0, 0, width, height, self.BACKGROUND)
        self._rectangle(0, height - self.HEADER_HEIGHT, width,
                        self.HEADER_HEIGHT, self.PANEL)
        self._rectangle(0, 0, width, self.FOOTER_HEIGHT, self.PANEL)

        self._label("Choose a photo folder", 24, height - 30,
                    size=19, bold=True)
        max_path_chars = max(20, (width - 48) // 8)
        path_display = self.current_path
        if len(path_display) > max_path_chars:
            path_display = "..." + path_display[-(max_path_chars - 3):]
        self._label(path_display, 24, height - 64, color=self.MUTED)

        self._button("Home", width - 196, height - 98, 76)
        self._button("Up", width - 108, height - 98, 76)

        list_top = height - self.HEADER_HEIGHT - 8
        list_bottom = self.FOOTER_HEIGHT + 8
        visible = max(1, (list_top - list_bottom) // self.ROW_HEIGHT)
        max_scroll = max(0, len(self.entries) - visible)
        self.scroll = min(self.scroll, max_scroll)
        for row in range(visible):
            index = self.scroll + row
            if index >= len(self.entries):
                break
            y = list_top - (row + 1) * self.ROW_HEIGHT
            if index == self.selected_index:
                self._rectangle(16, y, width - 32, self.ROW_HEIGHT - 2,
                                self.ACCENT)
            elif row % 2 == 0:
                self._rectangle(16, y, width - 32, self.ROW_HEIGHT - 2,
                                (30, 34, 42, 255))
            self._label(self.entries[index], 32, y + 18)

        if not self.entries and self.status.startswith("Choose"):
            self._label("No subfolders here.", 28, height // 2,
                        color=self.MUTED)
        self._label(self.status, 20, 54, size=10, color=self.MUTED)
        self._label("Cancel", width - 232, 28, color=self.TEXT,
                    bold=True, anchor_x="center")
        self._button("Select this folder", width - 198, 10, 178, active=True)

    def _on_click(self, x, y):
        width, height = self.window.width, self.window.height
        if y >= height - self.HEADER_HEIGHT:
            if height - 98 <= y <= height - 62 and width - 120 <= x <= width - 32:
                self._navigate(os.path.dirname(self.current_path))
            elif height - 98 <= y <= height - 62 and width - 208 <= x < width - 120:
                self._navigate(str(Path.home()))
            return
        if y < self.FOOTER_HEIGHT:
            if width - 250 <= x < width - 210 and y < 50:
                self._finish(None)
            elif width - 208 <= x <= width - 16 and y < 54:
                self._finish(self.current_path)
            return

        list_top = height - self.HEADER_HEIGHT - 8
        list_bottom = self.FOOTER_HEIGHT + 8
        if not list_bottom <= y <= list_top:
            return
        row = int((list_top - y) // self.ROW_HEIGHT)
        visible_index = self.scroll + row
        if visible_index >= len(self.entries):
            return
        now = time.monotonic()
        previous_index, previous_time = self._last_click
        if previous_index == visible_index and now - previous_time < 0.35:
            self._navigate(os.path.join(self.current_path,
                                        self.entries[visible_index]))
            self._last_click = (None, 0.0)
        else:
            self.selected_index = visible_index
            self._last_click = (visible_index, now)
            self.status = "Double-click a folder to open it, or select this folder."
            self._rebuild()

    def _scroll_by(self, amount):
        width, height = self.window.width, self.window.height
        visible = max(
            1,
            (height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT - 16)
            // self.ROW_HEIGHT,
        )
        self.scroll = max(0, min(len(self.entries) - visible,
                                 self.scroll - amount))
        self._rebuild()

    def _move_selection(self, amount):
        if not self.entries:
            return
        if self.selected_index is None:
            self.selected_index = 0
        else:
            self.selected_index = max(
                0, min(len(self.entries) - 1, self.selected_index + amount)
            )
        height = self.window.height
        visible = max(
            1,
            (height - self.HEADER_HEIGHT - self.FOOTER_HEIGHT - 16)
            // self.ROW_HEIGHT,
        )
        if self.selected_index < self.scroll:
            self.scroll = self.selected_index
        elif self.selected_index >= self.scroll + visible:
            self.scroll = self.selected_index - visible + 1
        self._rebuild()
