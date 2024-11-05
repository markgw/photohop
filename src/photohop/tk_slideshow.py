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
import tkinter as tk
import tkinter.ttk as ttk
import ttkthemes
from pathlib import Path
from tkinter import filedialog
from collections import OrderedDict

from PIL import Image, ExifTags  # $ pip install pillow
from PIL import ImageTk

from photohop.config import Config
from photohop.selector import SelectedPhoto, image_filenames, PhotoSelector

debug = logging.debug


def random_slideshow(photo_root=None, exclude=[]):
    config = Config.load()

    master = tk.Tk()
    master.style = ttkthemes.ThemedStyle()
    master.style.theme_use("equilux")
    hide_hidden_files(master)

    if photo_root is None:
        # Open dialog to select root
        photo_root = filedialog.askdirectory(
            initialdir=str(Path.home()),
            title="Select a root directory to search for photos"
        )
        if not photo_root:
            print("No photo root given: exiting")
            return
    # Index collection in given dir
    photo_selector = PhotoSelector(photo_root, exclude)

    # Set up a slideshow
    Slideshow(master, photo_selector, config)
    master.focus_set()

    master.mainloop()


class Slideshow(object):
    def __init__(self, parent, selector, config):
        self.config = config
        self.selector = selector
        self.ma = parent.winfo_toplevel()
        self._photo_image = None  # must hold reference to PhotoImage
        # How much to rotate the current image by
        self.rotation = 0

        ## Build the UI
        # Label to contain current image
        self.imglbl = ttk.Label(parent, background="Black", anchor=tk.CENTER)
        self.bottom_area = ttk.Frame(self.imglbl)
        self.bottom_area.pack(side=tk.BOTTOM)
        self.l_button_frame = ttk.Frame(self.bottom_area)
        self.r_button_frame = ttk.Frame(self.bottom_area)
        # Label overlaid for name and other info
        self.info_var = tk.StringVar()
        self.info_lbl = ttk.Label(self.bottom_area, textvariable=self.info_var, justify=tk.CENTER, padding=3)
        self.l_button_frame.pack(side=tk.LEFT)
        self.info_lbl.pack(side=tk.LEFT)
        self.r_button_frame.pack(side=tk.LEFT)

        # Buttons
        self.next_button = ttk.Button(self.r_button_frame, text=">", command=self.next_image)
        self.next_button.pack(side=tk.LEFT)
        self.previous_button = ttk.Button(self.l_button_frame, text="<", command=self.prev_image)
        self.previous_button.pack(side=tk.LEFT)

        # label occupies all available space
        self.imglbl.pack(fill=tk.BOTH, expand=True)

        # Configure keybindings
        self.ma.bind("<Escape>", lambda _: self.ma.destroy())  # exit on Esc
        self.ma.bind("q", lambda _: self.ma.destroy())  # exit on q
        self.ma.bind('<Prior>', self.prev_image)
        self.ma.bind('<Left>', self.prev_image)
        self.ma.bind('<Next>', self.next_image)
        self.ma.bind('<Right>', self.next_image)
        self.ma.bind("<space>", self.next_image)
        self.ma.bind("r", self.rotate90)
        self.ma.bind("R", self.rotate270)
        self.ma.bind("d", self.queue_current_dir)
        self.ma.bind("<End>", self.random_image)

        self.ma.bind("<Configure>", self.fit_image)  # fit image on resize
        # Toggle fullscreen with F11
        self.ma.bind("<F11>", self.toggle_fullscreen)

        # Open a file manager on the current image with f
        self.ma.bind("f", self.open_file_manager)

        self.context_menu = tk.Menu(self.ma)
        self.context_menu.add_command(label="Previous", command=self.prev_image, accelerator="Left")
        self.context_menu.add_command(label="Next", command=self.next_image, accelerator="Right")
        self.context_menu.add_command(label="View directory", command=self.queue_current_dir, accelerator="d")
        self.context_menu.add_command(label="Next random jump", command=self.random_image, accelerator="End")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Rotate right", command=self.rotate90, accelerator="r")
        self.context_menu.add_command(label="Rotate left", command=self.rotate270, accelerator="Shift+r")
        self.context_menu.add_command(label="Toggle fullscreen", command=self.toggle_fullscreen, accelerator="F11")

        def popup(event):
            """ Show popup menu on right click """
            self.context_menu.tk_popup(event.x_root, event.y_root)

        self.ma.bind("<Button-3>", popup)

        # set application window title
        self.ma.wm_title("PhotoHop slideshow")
        self.ma.title("PhotoHop slideshow: {}".format(self.selector.root_dir))

        self.current_image = None
        self.history = []
        # None when at the last item (most of the time)
        self.history_cursor = None

        # The queue allows you to go through a list of photos before making
        # the next random leap
        self.queue = []

        # Set initial size
        self.ma.geometry("800x600")
        # Don't start in fullscreen
        self.fullscreen_off()

        # Haven't got this working yet
        self.viewing_history = ViewingHistory(self.history_path)
        self.viewing_history.new_session(datetime.datetime.now().strftime("%Y:%m:%d %H:%M:%S"))

        # Start with a random image
        self.ma.after(1, self.next_image)

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
        self.ma.attributes("-fullscreen", False)
        self.fullscreen = False

    def fullscreen_on(self):
        self.ma.attributes("-fullscreen", True)
        self.fullscreen = True

    def _slideshow(self, filenames, delay_milliseconds):
        self.show_image(filenames[0])
        self.imglbl.after(delay_milliseconds, self._slideshow, filenames[1:], delay_milliseconds)

    def show_image(self, selected_image=None):
        if selected_image is None:
            selected_image = self.current_image
            if selected_image is None:
                return
            new_image = False
        else:
            # Loading a new image
            self.rotation = 0
            new_image = True
        path = selected_image.abs_path
        debug("load %r", path)
        image = Image.open(path)  # note: let OS manage file cache
        image = rotate_to_exif(image)
        selected_image.timestamp = image_datatime(image)
        if self.rotation > 0:
            image = image.rotate(self.rotation, expand=True)
        self.current_image = selected_image

        # shrink image inplace to fit in the application window
        w, h = self.ma.winfo_width(), self.ma.winfo_height()
        if image.size[0] > w or image.size[1] > h:
            # note: ImageOps.fit() copies image
            # preserve aspect ratio
            if w < 3 or h < 3:  # too small
                debug("window too small to show image: {}x{}".format(w, h))
                return  # do nothing
            image.thumbnail((w - 2, h - 2), Image.ANTIALIAS)
            debug("resized: win %s >= img %s", (w, h), image.size)

        # note: pasting into an RGBA image that is displayed might be slow
        # create new image instead
        self._photo_image = ImageTk.PhotoImage(image)
        self.imglbl.configure(image=self._photo_image)

        if new_image:
            self._on_new_image(selected_image)

    def _on_new_image(self, selected_image):
        if selected_image.timestamp is not None:
            self.info_var.set("{}\n{}".format(selected_image.display_name, selected_image.timestamp.strftime("%d/%m/%Y")))
        else:
            self.info_var.set(selected_image.display_name)
        self.viewing_history.add_entry(selected_image.rel_path)

    def set_info_text(self, text):
        self.info_var.set(text)

    def _show_image_on_next_tick(self):
        self.show_image()

    def random_image(self, event_unused=None):
        selected = self.selector.get_photo()
        # Add new image to end of history
        self.history.append(selected)
        self.history_cursor = None
        # If anything's queued and we explicitly jump to a random image,
        # empty the queue
        if len(self.queue):
            self.queue = []
        self.show_image(selected)

    def next_image(self, event_unused=None):
        if self.history_cursor is None:
            # At end of history already
            # Take an image from the queue if anything's queued
            if len(self.queue):
                next_image = self.queue.pop(0)
                self.history.append(next_image)
                # Now this has been viewed, don't select it randomly in future
                self.selector.remove(next_image.rel_dir, next_image.filename)
                self.show_image(next_image)
            else:
                self.random_image()
        elif self.history_cursor == len(self.history) - 2:
            # Been going through history, but now reaching end
            self.history_cursor = None
            self.show_image(self.history[-1])
        else:
            self.history_cursor += 1
            self.show_image(self.history[self.history_cursor])

    def prev_image(self, event_unused=None):
        if self.history_cursor is None:
            # At end of history (fresh image): start going backwards
            self.history_cursor = len(self.history) - 1
        if self.history_cursor == 0:
            # No further to go: do nothing
            return
        self.history_cursor -= 1
        self.show_image(self.history[self.history_cursor])

    def rotate90(self, event_unused=None):
        self.rotation = (self.rotation - 90) % 360
        self.show_image()

    def rotate270(self, event_unused=None):
        self.rotation = (self.rotation + 90) % 360
        self.show_image()

    def queue_current_dir(self, event_unused=None):
        """
        Add the whole directory containing the current image to the queue
        and start on the first image
        """
        current = self.current_image
        current_dir = current.abs_dir
        filenames = image_filenames(os.listdir(current_dir))
        if len(filenames):
            self.queue = [
                SelectedPhoto(
                    current.rel_dir, fn, current.root_dir,
                    display_name="{} [{}/{}] ({})".format(current.rel_dir, i, len(filenames), fn)
                ) for i, fn in enumerate(filenames, start=1)
            ]
            self.next_image()

    def open_file_manager(self, event_unused=None):
        if self.file_manager_cmd is not None:
            cmd_subst = dict(image=self.current_image.abs_path, image_dir=self.current_image.abs_dir)
            cmd_parts = self.file_manager_cmd.split()
            cmd_parts = [part.format(**cmd_subst) for part in cmd_parts]
            subprocess.call(cmd_parts)

    def fit_image(self, event=None, _last=[None] * 2):
        """Fit image inside application window on resize."""
        if event is not None and event.widget is self.ma and (
                _last[0] != event.width or _last[1] != event.height):
            # size changed; update image
            _last[:] = event.width, event.height
            self.show_image()


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


for ORIENTATION_TAG in ExifTags.TAGS.keys():
    if ExifTags.TAGS[ORIENTATION_TAG] == 'Orientation':
        break


def rotate_to_exif(image):
    if not hasattr(image, "_getexif"):
        return image
    exif = image._getexif()
    if exif is None:
        return image
    else:
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
        timestamp_field = image._getexif().get(306, None)
    except:
        return None
    if timestamp_field is None:
        return None
    if timestamp_field.startswith("0000"):
        # Zero timestamp
        return None
    timestamp = datetime.datetime.strptime(timestamp_field.partition(" ")[0], "%Y:%m:%d")
    if timestamp.year == 0:
        return None
    else:
        return timestamp


def hide_hidden_files(master):
    """Major incantations to hide hidden files in file browser"""
    try:
        # call a dummy dialog with an impossible option to initialize the file
        # dialog without really getting a dialog window; this will throw a
        # TclError, so we need a try...except :
        try:
            master.tk.call('tk_getOpenFile', '-foobarbaz')
        except tk.TclError:
            pass
        # now set the magic variables accordingly
        master.tk.call('set', '::tk::dialog::file::showHiddenBtn', '1')
        master.tk.call('set', '::tk::dialog::file::showHiddenVar', '0')
    except:
        pass
