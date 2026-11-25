from pathlib import Path
import random
from .index import PhotoIndex
from datetime import datetime


class PhotoSelector(object):
    """
    Random selection of photos by various methods.

    For now, this just selects randomly from the whole collection.

    """
    def __init__(self, index : PhotoIndex):
        self.index = index
        self.current_photo = 0

    def move_random(self):
        self.current_photo = random.randint(0, len(self.index) - 1)

    def move_next(self):
        self.current_photo += 1
        if self.current_photo >= len(self.index):
            self.current_photo = 0

    def move_prev(self):
        self.current_photo -= 1
        if self.current_photo < 0:
            self.current_photo = len(self.index) - 1

    def get_photo(self):
        photo_path = Path(self.index[self.current_photo])
        return SelectedPhoto(photo_path, self.index.root_dir, self.index.df.iloc[self.current_photo]["image_datetime"])


class SelectedPhoto(object):
    def __init__(self, rel_path : Path, root_path : Path, timestamp : datetime | None = None):
        self.rel_path = rel_path
        self.root_path = root_path
        self.timestamp = timestamp

        self.display_name = str(self.rel_path)

    @property
    def abs_path(self):
        return self.root_path / self.rel_path

    @property
    def abs_dir(self):
        return self.root_path / self.rel_path.parent
