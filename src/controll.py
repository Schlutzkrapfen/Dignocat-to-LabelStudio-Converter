import hashlib
from collections import defaultdict
import os

def find_duplicates_of(image_path: str, images_path: str) -> list:
    """Returns a list of files in images_path that are duplicates of image_path."""
    target_hash = _hash_file(image_path)
    duplicates = []

    for filename in os.listdir(images_path):
        filepath = os.path.join(images_path, filename)
        if not os.path.isfile(filepath) or filepath == image_path:
            continue

        if _hash_file(filepath) == target_hash:
            duplicates.append(filepath)

    return duplicates
def _hash_file(filepath, chunk_size=8192):
    """Returns an MD5 hash of the file's contents."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

