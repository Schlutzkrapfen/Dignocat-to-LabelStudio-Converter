

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
