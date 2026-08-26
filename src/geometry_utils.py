

from PIL import Image

from dental_logic import convert_thooth_id_to_number, find_tooth_id_around

from json_maker import get_difference, get_json_cordinates
from task_item import InnerAnnotation
from webcrawler import get_refrence_image, get_theeh_picture, get_thooth_id


def get_new_rectangle(item:InnerAnnotation,x,y,width,height):
    """Expands a bounding box to also enclose a new annotation's rectangle.

        Computes the smallest bounding box that contains both the current
        box (given by `x`, `y`, `width`, `height`) and the rectangle of
        `item`. A `width`/`height` of 0 is treated as "no box yet", so the
        result is based solely on `item`'s rectangle in that case.

        Args:
            item (InnerAnnotation): Annotation whose rectangle should be
                merged into the current bounding box.
            x (float): X coordinate of the current bounding box.
            y (float): Y coordinate of the current bounding box.
            width (float): Width of the current bounding box.
            height (float): Height of the current bounding box.

        Returns:
            tuple[float, float, float, float]: The new bounding box as
                `(x, y, width, height)`.
        """
    item_x = item["value"]["x"]
    item_y = item["value"]["y"]
    item_width = item["value"]["width"]
    item_height = item["value"]["height"]

    # Right/bottom edges of the current bounding box (before this item)
    right = x + width
    bottom = y + height

    # Right/bottom edges of the new item
    item_right = item_x + item_width
    item_bottom = item_y + item_height

    # New bounding box: min of the left/top edges, max of the right/bottom edges
    new_x = item_x if x == 0 else min(x, item_x)
    new_y = item_y if y == 0 else min(y, item_y)
    new_right = max(right, item_right) if width != 0 else item_right
    new_bottom = max(bottom, item_bottom) if height != 0 else item_bottom

    new_width = new_right - new_x
    new_height = new_bottom - new_y

    return new_x, new_y, new_width, new_height

async def is_overlapping(thooth_id:str,user_id:int,offset:float=2.0)->bool:
    """
        Checks whether the teeth adjacent to `thooth_id` have overlapping
        bounding boxes on the x-axis, based on diff images against the
        user's reference image.

        Args:
            thooth_id: Tooth to find neighbors around.
            user_id: User whose images to use.
            offset: Horizontal tolerance when comparing bounding boxes.

        Returns:
            True if the two teeth's boxes overlap horizontally, else False.
            Returns False if there's no following tooth.
        Note:
            Only the x and width values from `get_json_cordinates` are used;
            the y and height values are discarded and not considered
        """
    thoot1,thoot2 =  find_tooth_id_around(thooth_id)
    if thoot2 == None:
        return False
    try:
        thoot1_id = await get_thooth_id(convert_thooth_id_to_number(thoot1))

        thoot2_id = await get_thooth_id(convert_thooth_id_to_number(thoot2))
        refrence_path = await get_refrence_image(user_id)
        image_path1 = await get_theeh_picture(thoot1_id, user_id)
        image_path2 = await get_theeh_picture(thoot2_id, user_id)
        diff_path1 = await get_difference(refrence_path, image_path1)
        x_pct1, _y_pct1, w_pct1, _h_pct1 = await get_json_cordinates(diff_path1)
        diff_path2 = await get_difference(refrence_path, image_path2)
        x_pct2, _y_pct2, w_pct2, _h_pct2 = await get_json_cordinates(diff_path2)
    except ValueError as er:
        print(er)
        return False

    left_point = min(x_pct1+w_pct1, x_pct2+w_pct2)
    right_point = max(x_pct1, x_pct2)
    return left_point + offset >= right_point

def crop_with_padding(image: Image.Image, x_pct:float, y_pct:float, w_pct:float, h_pct:float, padding_pct:float=5) -> Image.Image:
    """Crops a region of an image, adding padding around it.

        Args:
            image (Image.Image): The PIL image to crop.
            x_pct (float): X coordinate of the region's top-left corner, as % of image width.
            y_pct (float): Y coordinate of the region's top-left corner, as % of image height.
            w_pct (float): Width of the region, as % of image width.
            h_pct (float): Height of the region, as % of image height.
            padding_pct (float): Padding around the region, as % of the region's own size.

        Returns:
            Image.Image: The cropped image, clamped to the original image's bounds.
    """
    img_w, img_h = image.size

    x = x_pct / 100 * img_w
    y = y_pct / 100 * img_h
    w = w_pct / 100 * img_w
    h = h_pct / 100 * img_h

    pad_x = w * (padding_pct / 100)
    pad_y = h * (padding_pct / 100)

    left = max(0, x - pad_x)
    top = max(0, y - pad_y)
    right = min(img_w, x + w + pad_x)
    bottom = min(img_h, y + h + pad_y)

    return image.crop((int(left), int(top), int(right), int(bottom)))

def enhance_contrast(img_gray: Image.Image, black_point=60, white_point=200) -> Image.Image:
    """Stretch the histogram: everything below black_point becomes 0,
    everything above white_point becomes 255."""
    scale = 255.0 / (white_point - black_point)

    def stretch(p):
        val = (p - black_point) * scale
        return int(max(0, min(255, val)))

    # point() builds a 256-entry lookup table and applies it to every pixel
    return img_gray.point(stretch)


def find_edges(img_gray: Image.Image,image_height:int, default_width: float = 1,
              strip_width: int = 3, bright_thresh: int = 200
              ) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    """
    Finds the bounding box (x, y, width, height) of the bright region
    (tooth) touching the left edge and the right edge of the image.

    strip_width: how many pixels wide the border strip is, used only to
                 decide if a bright pixel counts as "touching" that edge.
    default_heigth: fallback size used for width/height if nothing bright
                     is found near that edge (so we never return 0).

    Returns: (left_box, right_box), each as (x, y, width, height).
    """
    img_gray = enhance_contrast(img_gray)

    w, h = img_gray.size
    pixels = img_gray.load()
    if pixels is None:
        raise ValueError("Image pixels are None")

    def find_bright_box(is_left: bool):
        x_check_range = range(0, strip_width) if is_left else range(w - strip_width, w)


        touching_rows = [
            y for y in range(h)
            if any(pixels[x, y] > bright_thresh for x in x_check_range)
        ]

        if not touching_rows:
            x0 = 0 if is_left else w - default_width
            return (x0, 0, default_width, default_width)

        min_y, max_y = min(touching_rows), max(touching_rows)

        # 2. within those rows, find how far the bright region extends
        #    horizontally (full width, not just inside the strip)
        xs = [
            x for y in range(min_y, max_y + 1)
            for x in range(w)
            if pixels[x, y] > bright_thresh
        ]

        if not xs:
            x0 = 0 if is_left else w - default_width
            return (x0, min_y, default_width, max_y - min_y + 1)

        min_x =  min(xs)
        height = (max_y - min_y + 1)*100/image_height

        return (min_x, min_y, default_width, height)

    left_box = find_bright_box(is_left=True)
    right_box = find_bright_box(is_left=False)

    return left_box, right_box
