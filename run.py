#!./.venv/bin/python3
"""
For now, there's no proper commnd-line interface. You just
configure your slideshow by setting the variables in this
file and then run something like:
  PYTHONPATH=$PYTHONPATH:./src python3 -m photohop.run

"""
import sys
import os

from pathlib import Path

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "src"))

from photohop.index import PhotoIndex
from photohop.slideshow import random_slideshow
from photohop.config import Config

config = Config.load()

# Set these variables for configure the slideshow
# Root directory of your photo collection
#photo_root = "/run/media/mark/PHOTOS_BACK/2017"
photo_root = Path.home() / "pictures" / "photos" / "2017"
# Immediate subdirectories to exclude from index
exclude = ["music", "collections", "utils"]
# File to write viewing history to: a text file recording
# all the photos you looked at
# Set to None, or leave off arguments, to record no history
history = os.path.join(os.getcwd(), "viewing_history.txt")
# Command to open file manager on current image
# Can also be left off if you don't want this feature
file_manager_cmd = "nemo {image}"

# Index the collection
# TODO Store the index, so we don't have to re-index every time
#print(f"Indexing {photo_root}...")
#index = PhotoIndex.index_directory(photo_root, exclude)

# Load an index
index = PhotoIndex.load(config, photo_root)

# Set the slideshow going
random_slideshow(index)
