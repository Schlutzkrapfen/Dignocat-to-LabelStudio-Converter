import os
from PIL import Image
def get_info(filename: str)-> list[str]:
    """Gets the info out of the filename.

        Args:
            filename: Path to the image, expected format:
                      "Path/to/PatientId_PictureId_What-it-is_Prozent_SubId.png"

        Returns:
            list[str]: A list containing the split parts:
                       [PatientId, PictureId, What-it-is, Prozent, SubId/TheetId]
        """

    filename = os.path.basename(filename)  # removes "output/"
    name, _ext = os.path.splitext(filename)
    parts = name.split("_")
    return parts


def get_image_size(imagePath: str)->tuple[int,int]:
    """Gets the image size of a path.

        Args:
            imagePath: Path to the image.

        Returns:
            tuple[int, int]: Image size in (width, height) format.
        """
    img = Image.open(imagePath)
    return img.size


def to_percent(value: float, dimension: float) -> float:
    """Normalizes a coordinate or size value to a percentage of an image dimension.

        Args:
            value: The coordinate or size in pixels (e.g., bounding box width or X coordinate).
            dimension: The corresponding image dimension in pixels (width or height).

        Returns:
            float: The value expressed as a percentage of the dimension (between 0.0 and 100.0).
        """
    return (value / dimension) * 100

def to_confidence(value: str)->float:
    """Converts a percentage string to a float value (e.g., "50%" -> 0.5).

        Args:
            value: The percentage string to convert (e.g., "96%").

        Returns:
            float: A value between 0.0 and 1.0, or 0.0 if the conversion fails.
    """

    if "%" not in value:
        print(f"Warning: '{value}' is not a percentage!")
        return 0.0
    cleaned: str = value.strip("%").strip()
    try:
        return float(cleaned) / 100
    except ValueError:
        print(f"Warning: '{value}' could not be converted!")
        return 0.0
