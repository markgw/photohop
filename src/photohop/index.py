from pathlib import Path
from typing import Sequence
import pandas as pd
from tqdm import tqdm
import json

from PIL import Image, ExifTags

from .config import Config


class PhotoIndex:
    def __init__(self, root_dir : Path, dataframe : pd.DataFrame):
        self.root_dir = root_dir
        self.df = dataframe

    def __len__(self):
        return len(self.df)

    def __getitem__(self, index):
        return self.df.iloc[index]["image_path"]

    def save(self, config : Config):
        index_index_path = config.config_dir / "index.json"
        if index_index_path.exists():
            with index_index_path.open("r") as f:
                index_index = json.load(f)
        else:
            index_index = {}

        if str(self.root_dir) in index_index:
            filename = index_index[str(self.root_dir)]
        else:
            filename = f"index_{len(index_index):02d}.csv"
            index_index[str(self.root_dir)] = filename
            with index_index_path.open("w") as f:
                json.dump(index_index, f)
        
        self.df.to_csv(config.config_dir / filename, index=False)

    @staticmethod
    def load(config : Config, root_dir : Path):
        index_index_path = config.config_dir / "index.json"
        if not index_index_path.exists():
            raise FileNotFoundError(f"No index found for {root_dir}")
        with index_index_path.open("r") as f:
            index_index = json.load(f)
        if str(root_dir) not in index_index:
            raise FileNotFoundError(f"No index found for {root_dir}")
        filename = index_index[str(root_dir)]
        dataframe = pd.read_csv(config.config_dir / filename)
        return PhotoIndex(root_dir, dataframe)

    @staticmethod
    def index_directory(root_dir : Path|str, exclude : Sequence[str|Path] = [], progress : bool = True):
        root_dir = Path(root_dir).absolute()
        exclude_paths = [root_dir / Path(ex_pth) for ex_pth in exclude]

        # Build an index
        if progress:
            print(f"Reading file list from {root_dir}...")
        image_list = []
        image_datetimes = {}
        for dir, dirs, filenames in root_dir.walk():
            if dir in exclude_paths:
                # This subdir is excluded, don't index it
                dirs.clear()
                continue
            # See if there are any image files in this dir
            image_fns = image_filenames(filenames)
            if len(image_fns):
                for filename in image_fns:
                    image_path = (dir / filename).relative_to(root_dir)
                    image_list.append(image_path)

        if progress:
            im_iter = tqdm(image_list, desc="Reading EXIF data")
        else:
            im_iter = image_list
        for image_path in im_iter:
            date_taken = exif_date_taken(image_path)
            if date_taken is not None:
                image_datetimes[image_path] = date_taken

        # Sort the images by date taken, with unknown dates at the end
        image_list.sort(key=lambda image_path: (
            image_path not in image_datetimes,
            image_datetimes.get(image_path, ""),
        ))
        
        dataframe = pd.DataFrame({
            "image_path": image_list,
            "image_datetime": [image_datetimes.get(image_path, None) for image_path in image_list],
        })
        return PhotoIndex(root_dir, dataframe)


def exif_date_taken(image_path: Path) -> str | None:
    """Return the photo's EXIF capture date, when one is available."""
    try:
        with Image.open(image_path) as image:
            exif = image.getexif()
            tags = {ExifTags.TAGS.get(tag, tag): value for tag, value in exif.items()}
    except (OSError, ValueError):
        return None

    for tag in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        date_taken = tags.get(tag)
        if date_taken is not None:
            if isinstance(date_taken, bytes):
                date_taken = date_taken.decode("utf-8", errors="replace")
            return str(date_taken)
    return None


def image_filenames(filenames):
    return [
        filename for filename in filenames
        if filename.lower().rpartition(".")[2] in ["jpg", "png"]
    ]
