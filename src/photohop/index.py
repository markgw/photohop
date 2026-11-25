import re
from pathlib import Path
from typing import Sequence
import pandas as pd
from tqdm import tqdm
import json
from datetime import datetime

from PIL import Image, ExifTags

from .config import Config

FILENAME_DATE_REGEXPS = (
    re.compile(r"^IMG-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})-WA\d+(?:\(\d+\))?\.[^.]+$", re.IGNORECASE),
    re.compile(r"^GridArt_(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})_\d+\.[^.]+$", re.IGNORECASE),
    re.compile(r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})-DSC\d+\.[^.]+$", re.IGNORECASE),
    re.compile(r"^IMG_(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})_\d+(?:_.*)?\.[^.]+$", re.IGNORECASE),
    re.compile(r"^photo_(?P<year>\d{4})_(?P<month>\d{2})_(?P<day>\d{2})_IMG-\d{8}-WA\d+\.[^.]+$", re.IGNORECASE),
    re.compile(r"^IMG_(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})_\d+\.[^.]+$", re.IGNORECASE),
    re.compile(r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})_\d+_WhatsApp\.[^.]+$", re.IGNORECASE),
)



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
            if dir in exclude_paths or dir.name.startswith("."):
                # This subdir is excluded, don't index it
                dirs.clear()
                continue
            # See if there are any image files in this dir
            image_fns = image_filenames(filenames)
            if len(image_fns):
                for filename in image_fns:
                    image_path = (dir / filename).relative_to(root_dir)
                    image_list.append(image_path)

        # Get a timestamp for every image if possible
        if progress:
            im_iter = tqdm(image_list, desc="Reading EXIF data")
        else:
            im_iter = image_list
        missing_datetime = 0
        image_datetimes = []
        for image_path in im_iter:
            date_taken = exif_date_taken(root_dir / image_path)
            image_datetimes.append(date_taken)
            if date_taken is None:
                print(f"Warning: No EXIF date found for {image_path}")
                missing_datetime += 1
        if missing_datetime:
            print(f"Warning: {missing_datetime}/{len(image_list)} images had no EXIF date")

        dataframe = pd.DataFrame({
            "image_path": image_list,
            "image_datetime": image_datetimes,
        })
        dataframe["image_datetime"] = pd.to_datetime(dataframe["image_datetime"], errors="coerce")
        dataframe.sort_values(by="image_datetime", inplace=True, na_position="last")
        print(dataframe)
        
        return PhotoIndex(root_dir, dataframe)


def exif_date_taken(image_path: Path) -> datetime | None:
    """Return the photo's EXIF capture date, when one is available."""
    try:
        with Image.open(image_path) as image:
            exif = image.getexif()
            tags = {ExifTags.TAGS.get(tag, tag): value for tag, value in exif.items()}

        for tag in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
            timestamp_str = tags.get(tag)
            if timestamp_str is not None:
                if isinstance(timestamp_str, bytes):
                    timestamp_str = timestamp_str.decode("utf-8", errors="replace")
                timestamp = datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
                return timestamp

        # No EXIF datetime found
        # Try XMP instead (panoramas end up with these sometimes)
        xmp = image.getxmp()
        if xmp is not None:
            # Try getting the "First Photo Date" from the XMP metadata
            try:
                first_photo_date = xmp.get("xmpmeta", {}).get("RDF", {}).get("Description", {}).get("FirstPhotoDate", None)
            except:
                first_photo_date = None
            if first_photo_date is not None:
                timestamp = datetime.strptime(first_photo_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                return timestamp
    except (OSError, ValueError) as e:
        return None

    # Try getting the date/datetime from the filename
    filename = image_path.name
    for regexp in FILENAME_DATE_REGEXPS:
        match = regexp.match(filename)
        if match:
            year = int(match.group("year"))
            month = int(match.group("month"))
            day = int(match.group("day"))
            try:
                timestamp = datetime(year, month, day)
                return timestamp
            except ValueError:
                # Invalid date, continue to next regexp
                continue

    # Worst case, look in the directory structure for a year
    for part in reversed(image_path.parts):
        year_match  = re.match(r"^(?P<year>\d{4})(-\d+)?$", part)
        if year_match:
            try:
                year = int(year_match.group("year"))
                timestamp = datetime(year, 1, 1)
                return timestamp
            except ValueError:
                continue
    return None


def image_filenames(filenames):
    return [
        filename for filename in filenames
        if filename.lower().rpartition(".")[2] in ["jpg", "png"] and not filename.startswith(".")
    ]
