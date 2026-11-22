from pathlib import Path
import random
from .index import PhotoIndex


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
        return SelectedPhoto(photo_path, self.index.root_dir)


class SelectedPhoto(object):
    def __init__(self, rel_path : Path, root_path : Path, display_name=None):
        self.rel_path = rel_path
        self.root_path = root_path

        if display_name is not None:
            self.display_name = display_name
        else:
            self.display_name = str(self.rel_path.parent)

        self.timestamp = None

    @property
    def abs_path(self):
        return self.root_path / self.rel_path

    @property
    def abs_dir(self):
        return self.root_path / self.rel_path.parent
