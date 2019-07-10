#!./venv/bin/python3
import sys
import os

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "src"))

from photohop.slideshow import random_slideshow

random_slideshow()
