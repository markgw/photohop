#!/usr/bin/env python3
"""
Show slideshow for images in a given directory, hopping randomly between
them..

Fullscreen UI based on code borrowed from:
https://gist.github.com/zed/8b05c3ea0302f0e2c14c

A path to the file manager can be specified using file_manager_cmd. This
should be a format string, which can include the variable substitutions
{image} and/or {image_dir}, pointing to an image path to show or the
directory containing the image, respectively.

"""
import datetime
import logging
import os
import subprocess
from collections import OrderedDict
from typing import Optional

import pyglet

from PIL import Image, ExifTags  # $ pip install pillow

from photohop.config import Config
from photohop.selector import PhotoSelector
from photohop.widgets import DirectoryPicker
from photohop.index import PhotoIndex

debug = logging.debug


def random_slideshow(index : Optional[PhotoIndex] = None):
    config = Config.load()

    if index is None:
        photo_root = choose_directory()
        if not photo_root:
            print("No photo root given: exiting")
            return None
        index = PhotoIndex.index_directory(photo_root)

    photo_selector = PhotoSelector(index)
    photo_selector.move_random()
    window = pyglet.window.Window(width=800, height=600,
                                  caption="PhotoHop slideshow",
                                  vsync=True)
    slideshow = Slideshow(window, photo_selector, config)
    pyglet.clock.schedule_once(lambda dt: slideshow.next_image(), 0.001)
    pyglet.app.run()

    return slideshow


def choose_directory(initialdir=None):
    """Open the Pyglet directory picker and return the selected directory."""
    picker = DirectoryPicker(initialdir or os.path.expanduser("~"))
    pyglet.app.run()
    return picker.result


class Slideshow(object):
    def __init__(self, window, selector, config):
        self.config = config
        self.selector : PhotoSelector = selector
        self.window = window
        self.ma = window
        self.batch = pyglet.graphics.Batch()
        self._photo_image = None
        self._sprite = None
        self.rotation = 0
        self.fullscreen = window.fullscreen
        self.info_text = ""
        self.info_lbl = pyglet.text.Label(
            "",
            font_name="Lucida Grande",
            font_size=12,
            color=(255, 255, 255, 255),
            align="center",
            anchor_x="center",
            anchor_y="bottom",
            batch=self.batch,
            multiline=True,
            width=window.width - 24,
        )
        self.previous_button = pyglet.text.Label(
            "<", font_size=16, x=12, y=12,
            anchor_x="left", anchor_y="bottom",
            color=(255, 255, 255, 255), batch=self.batch,
        )
        self.next_button = pyglet.text.Label(
            ">", font_size=16, x=0, y=12,
            anchor_x="right", anchor_y="bottom",
            color=(255, 255, 255, 255), batch=self.batch,
        )
        self._position_controls()
        self._bind_window_events()
        self.window.set_caption(
            "PhotoHop slideshow: {}".format(self.selector.index.root_dir)
        )

        self.current_image = None
        self.history = []

        # Set up viewing history
        self.viewing_history = ViewingHistory(self.history_path)
        self.viewing_history.new_session(datetime.datetime.now().strftime("%Y:%m:%d %H:%M:%S"))

    def _bind_window_events(self):
        @self.window.event
        def on_draw():
            self.window.clear()
            self.batch.draw()

        @self.window.event
        def on_resize(width, height):
            self._position_controls()
            self.fit_image(width=width, height=height)

        @self.window.event
        def on_key_press(symbol, modifiers):
            if symbol in (pyglet.window.key.ESCAPE, pyglet.window.key.Q):
                self.window.close()
            elif symbol in (pyglet.window.key.PAGEUP, pyglet.window.key.LEFT):
                self.prev_image()
            elif symbol in (pyglet.window.key.PAGEDOWN, pyglet.window.key.RIGHT,
                             pyglet.window.key.SPACE):
                self.next_image()
            elif symbol == pyglet.window.key.R:
                if modifiers & pyglet.window.key.MOD_SHIFT:
                    self.rotate270()
                else:
                    self.rotate90()
            elif symbol == pyglet.window.key.H:
                # Random hop
                self.random_image()
            elif symbol == pyglet.window.key.F11:
                self.toggle_fullscreen()
            elif symbol == pyglet.window.key.F:
                self.open_file_manager()

        @self.window.event
        def on_mouse_press(x, y, button, modifiers):
            if y <= 44:
                if x <= 44:
                    self.prev_image()
                elif x >= self.window.width - 44:
                    self.next_image()

    @property
    def file_manager_cmd(self):
        return self.config["file_manager_cmd"]

    @property
    def history_path(self):
        return self.config["history_path"]

    def toggle_fullscreen(self, event_unused=None):
        if self.fullscreen:
            self.fullscreen_off()
        else:
            self.fullscreen_on()

    def fullscreen_off(self):
        self.ma.set_fullscreen(False)
        self.fullscreen = False

    def fullscreen_on(self):
        self.ma.set_fullscreen(True)
        self.fullscreen = True

    def _slideshow(self, filenames, delay_milliseconds):
        self.show_image(filenames[0])
        if filenames[1:]:
            pyglet.clock.schedule_once(
                lambda dt: self._slideshow(filenames[1:], delay_milliseconds),
                delay_milliseconds / 1000.0,
            )

    def show_image(self, selected_image=None):
        if selected_image is None:
            # Re-displaying the same image again
            selected_image = self.current_image
            if selected_image is None:
                return
            new_image = False
        else:
            # New image selected
            self.rotation = 0
            new_image = True
            self.current_image = selected_image

        path = selected_image.abs_path
        debug("load %r", path)
        image = Image.open(path)
        image = rotate_to_exif(image)
        selected_image.timestamp = image_datatime(image)
        if self.rotation > 0:
            image = image.rotate(self.rotation, expand=True)

        w, h = self.ma.width, self.ma.height
        if w < 3 or h < 3:
            debug("window too small to show image: {}x{}".format(w, h))
            return
        if image.size[0] > w or image.size[1] > h:
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            image.thumbnail((w - 2, h - 2), resample)
            debug("resized: win %s >= img %s", (w, h), image.size)

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
        elif image.mode == "RGB":
            image = image.convert("RGBA")
        raw = image.tobytes()
        pitch = - len(raw) // image.height
        self._photo_image = pyglet.image.ImageData(
            image.width, image.height, "RGBA", raw, pitch=pitch
        )
        if self._sprite is not None:
            self._sprite.delete()
        self._sprite = pyglet.sprite.Sprite(
            self._photo_image.get_texture(), batch=self.batch
        )
        self.fit_image(width=w, height=h)

        if new_image:
            self._on_new_image(selected_image)

    def _on_new_image(self, selected_image):
        if selected_image.timestamp is not None:
            self.set_info_text(
                "{}\n{}".format(
                    selected_image.display_name,
                    selected_image.timestamp.strftime("%d/%m/%Y"),
                )
            )
        else:
            self.set_info_text(selected_image.display_name)
        self.viewing_history.add_entry(selected_image.rel_path)

    def set_info_text(self, text):
        self.info_text = text
        self.info_lbl.text = text

    def _show_image_on_next_tick(self):
        self.show_image()

    def update_image(self):
        selected = self.selector.get_photo()
        # Add new image to end of history
        self.history.append(selected)
        self.show_image(selected)

    def random_image(self, event_unused=None):
        # Make a random hop
        self.selector.move_random()
        self.update_image()

    def next_image(self, event_unused=None):
        self.selector.move_next()
        self.update_image()

    def prev_image(self, event_unused=None):
        self.selector.move_prev()
        self.update_image()

    def rotate90(self, event_unused=None):
        self.rotation = (self.rotation - 90) % 360
        self.show_image()

    def rotate270(self, event_unused=None):
        self.rotation = (self.rotation + 90) % 360
        self.show_image()

    def open_file_manager(self, event_unused=None):
        if self.file_manager_cmd is not None and self.current_image is not None:
            cmd_subst = dict(image=self.current_image.abs_path, image_dir=self.current_image.abs_dir)
            cmd_parts = self.file_manager_cmd.split()
            cmd_parts = [part.format(**cmd_subst) for part in cmd_parts]
            subprocess.call(cmd_parts)

    def fit_image(self, event=None, _last=[None] * 2, width=None, height=None):
        """Fit image inside application window on resize."""
        if event is not None:
            width = getattr(event, "width", width)
            height = getattr(event, "height", height)
        if width is None:
            width = self.ma.width
        if height is None:
            height = self.ma.height
        self._position_controls()
        if self._sprite is not None:
            image_width = self._photo_image.width
            image_height = self._photo_image.height
            scale = min(width / image_width, height / image_height)
            self._sprite.scale = scale
            self._sprite.x = (width - image_width * scale) / 2
            self._sprite.y = (height - image_height * scale) / 2

    def _position_controls(self):
        width = self.ma.width
        height = self.ma.height
        self.info_lbl.x = width // 2
        self.info_lbl.y = 12
        self.next_button.x = width - 12


class ViewingHistory(object):
    """
    Path may be set to None, meaning no output is written.

    """
    def __init__(self, path):
        self.path = path
        self.sessions = OrderedDict()
        # If the file exists, load previous viewing history
        if path is not None and os.path.exists(path):
            self.load_history()

    def _append_line(self, line):
        if self.path is not None:
            with open(self.path, "a") as f:
                f.write(line)

    def new_session(self, name):
        self.sessions[name] = []
        self._append_line("SESSION: {}\n".format(name))

    def add_entry(self, filename):
        self.current_session.append(filename)
        self._append_line("{}\n".format(filename))

    def load_history(self):
        with open(self.path, "r") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("SESSION: "):
                    session_name = line[9:]
                    self.sessions[session_name] = []
                elif len(line.strip()):
                    self.current_session.append(line)

    @property
    def current_session(self):
        return self.sessions[next(reversed(self.sessions))]


def get_image_files(rootdir):
    for path, dirs, files in os.walk(rootdir):
        dirs.sort()  # traverse directory in sorted order (by name)
        files.sort()  # show images in sorted order
        for filename in image_filenames(files):
            yield os.path.join(path, filename)


ORIENTATION_TAG = next(
    (tag for tag, name in ExifTags.TAGS.items() if name == "Orientation"),
    None,
)


def rotate_to_exif(image):
    if not hasattr(image, "_getexif"):
        return image
    try:
        exif = image._getexif()
    except (AttributeError, OSError, ValueError):
        return image
    if exif is None:
        return image
    exif = dict(exif.items())

    if ORIENTATION_TAG not in exif:
        return image

    if exif[ORIENTATION_TAG] == 3:
        image = image.rotate(180, expand=True)
    elif exif[ORIENTATION_TAG] == 6:
        image = image.rotate(270, expand=True)
    elif exif[ORIENTATION_TAG] == 8:
        image = image.rotate(90, expand=True)
    return image


def image_datatime(image):
    try:
        exif = image._getexif()
        timestamp_field = exif.get(306, None) if exif is not None else None
    except (AttributeError, OSError, ValueError):
        return None
    if timestamp_field is None:
        return None
    if not isinstance(timestamp_field, str) or timestamp_field.startswith("0000"):
        # Zero timestamp
        return None
    try:
        timestamp = datetime.datetime.strptime(
            timestamp_field.partition(" ")[0], "%Y:%m:%d"
        )
    except (TypeError, ValueError):
        return None
    return timestamp if timestamp.year != 0 else None


def hide_hidden_files(master):
    """Deprecated no-op retained for compatibility with external callers."""
    return None
