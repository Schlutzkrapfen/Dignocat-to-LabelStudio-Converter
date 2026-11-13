import hashlib
from pathlib import Path
import os

from playwright.async_api import TimeoutError as PlaywrightTimeoutError


def get_all_ids() -> list[str]:
    """Collect the IDs of all files already saved in the ``output`` folder.

        The ID is expected as the fifth ``_``-separated part of the filename,
        without the file extension. Files with fewer than five parts are skipped.

        Returns:
            List of ID strings found in the filenames.
        """
    ids: list[str] = []

    for filename in os.listdir("output"):
        parts = filename.split("_")
        if len(parts) > 4:
            id = parts[4].split(".")
            ids.append(id[0])
    return ids
def find_duplaceted_info(info):
    """Returns true when there is found a id 2 types
    Args:
          info: Entry data containing an ``"id"`` key.

      Returns:
          True if ``info["id"]`` matches an ID already present in the
          ``output`` folder. False if the entry has no ID or the ID is new.
      """
    if not info.get("id"):
        return False
    ids=  get_all_ids()
    return info["id"] in ids



async def check_preview_image(page, expected_alt: str = "Pano AI")-> bool:
    """Checks whether a preview image or loading indicator with the given alt text is present.

        Args:
            page: Playwright page to search in.
            expected_alt: Alt text of the image to look for. Defaults to "Pano AI".

        Returns:
            True if at least one matching image, loading or preview is found, False otherwise.
        """
    loading = page.locator('.ReportGenerationStatus-module_container_6AYLt')
    try:
        await loading.wait_for(state="detached", timeout=20000)
    except PlaywrightTimeoutError:
        print("Loading indicator not detached within 20 seconds")
    loading = page.locator('.ReportGenerationStatus-module_container_6AYLt')
    preview = page.locator('[data-testid^="preview-report-Pano-"]')
    locator = page.locator(f'img[alt="{expected_alt}"]')

    return  await locator.count() != 0 or await preview.count() != 0 or await loading.count() != 0

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
