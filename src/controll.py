import hashlib
from pathlib import Path
import os



def get_all_ids() -> list[str]:
    ids: list[str] = []

    for filename in os.listdir("output"):
        parts = filename.split("_")
        if len(parts) > 4:
            id = parts[4].split(".")
            ids.append(id[0])
    return ids
def find_duplaceted_info(info):
    """Returns true when there is found a id 2 types"""
    if not info.get("id"):
        return False
    ids=  get_all_ids()
    return info["id"] in ids




def find_duplicates_of(image_path: Path, images_path: Path) -> list[Path]:
    """Finds duplicate images in a directory by comparing file hashes.

        Args:
            image_path: Path to the target image file.
            images_path: Path to the directory of images to search.

        Returns:
            A list of file paths that are duplicates of the target image.
        """
    target_hash = _hash_file(image_path)
    duplicates: list[Path] = []
    for filepath in images_path.iterdir():
        if not filepath.is_file() or filepath == image_path:
            continue
        if _hash_file(filepath) == target_hash:
            duplicates.append(filepath)
    return duplicates

def _hash_file(filepath: Path, chunk_size: int = 8192):
    """Calculates the MD5 hash of a file by reading it in chunks.

        Args:
            filepath: Path to the file to hash.
            chunk_size: Buffer size in bytes for reading the file. Defaults to 8192.

        Returns:
            The MD5 hash hex string of the file's contents.
        """
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()
