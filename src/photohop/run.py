"""
For now, there's no proper commnd-line interface. You just
configure your slideshow by setting the variables in this
file and then run something like:
  PYTHONPATH=$PYTHONPATH:./src python3 -m photohop.run

"""
from photohop.slideshow import random_slideshow
import os

# Set these variables for configure the slideshow
# Root directory of your photo collection
photo_root = "/media/magranro/PHOTOS/"
# Immediate subdirectories to exclude from index
exclude = ["music", "collections", "utils"]
# File to write viewing history to: a text file recording
# all the photos you looked at
# Set to None, or leave off arguments, to record no history
history = os.path.join(os.getcwd(), "viewing_history.txt")
# Command to open file manager on current image
# Can also be left off if you don't want this feature
file_manager_cmd = "nemo {image}"

# Set the slideshow going
random_slideshow(photo_root, history=history, exclude=exclude, file_manager_cmd=file_manager_cmd)
