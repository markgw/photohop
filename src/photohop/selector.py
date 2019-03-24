import os
import random


class PhotoSelector(object):
    """
    Random selection of photos by various methods.

    For now, this just selects randomly from the whole collection.

    """
    def __init__(self, root_dir, exclude):
        self.root_dir = root_dir
        self.exclude = exclude
        self.exclude_paths = [os.path.join(root_dir, x) for x in exclude]

        self.photo_dir_images = {}
        self.photo_dirs = []

        for dirname, dirs, filenames in os.walk(self.root_dir):
            if dirname in self.exclude_paths:
                dirs.clear()
                continue
            # See if there are any image files in this dir
            image_fns = image_filenames(filenames)
            if len(image_fns):
                rel_dir = os.path.relpath(dirname, root_dir)
                self.photo_dirs.append(rel_dir)
                self.photo_dir_images[rel_dir] = image_fns
        if len(self.photo_dirs) == 0:
            raise ValueError("no photos found")

    def get_photo(self):
        # For now, just choose dirs at random, then choose a random photo
        dir = random.choice(self.photo_dirs)
        filenames = self.photo_dir_images[dir]
        # Choose a random photo
        filename = random.choice(filenames)
        return SelectedPhoto(dir, filename, self.root_dir)


class SelectedPhoto(object):
    def __init__(self, rel_dir, filename, root_dir, display_name=None):
        self.rel_dir = rel_dir
        self.filename = filename
        self.root_dir = root_dir

        if display_name is None:
            self.display_name = os.path.join(self.rel_dir, self.filename)
        else:
            self.display_name = display_name

        self.timestamp = None

    @property
    def abs_path(self):
        return os.path.join(self.root_dir, self.rel_dir, self.filename)

    @property
    def rel_path(self):
        return os.path.join(self.rel_dir, self.filename)

    @property
    def abs_dir(self):
        return os.path.join(self.root_dir, self.rel_dir)


def image_filenames(filenames):
    return [
        filename for filename in filenames
        if filename.lower().rpartition(".")[2] in ["jpg", "png"]
    ]