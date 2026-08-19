

from numpy import true_divide
from torch._dynamo.utils import T
from torch.jit.annotations import Tuple

from add_ai import add_ai
from check_options import test_if_inward, test_if_needs_combine, test_if_no_overlapp, test_if_outward
from helper_functions import get_user_id_from_TaskItem
from json_maker import get_difference, get_json_cordinates
from task_item import InnerAnnotation, TaskItem, Value
from webcrawler import  get_refrence_image, get_theeh_picture, get_thooth_id

async def remove_labels(tasks:list[TaskItem])-> list[TaskItem]:
    """Removes labeled-as-removed annotations from a list of tasks.

        For each task, iterates over the annotations contained in the
        first prediction's result (`predictions[0]["result"]`) and keeps
        only those for which `check_if_label_removed` returns False,
        discarding the rest. The task's result list is then replaced with
        the filtered annotations.

        Args:
            tasks (list[TaskItem]): List of tasks to process.

        Returns:
            list[TaskItem]: The same list of tasks passed in, with
                `predictions[0]["result"]` updated to contain only the
                annotations that were not removed."""
    items:list[TaskItem] = []
    for task in tasks:
        result = task["predictions"][0]["result"]
        user_id = get_user_id_from_TaskItem(task)
        cur_anotation:list[InnerAnnotation] = []
        for anotation in result:
            if await check_if_label_removed(anotation["options"],anotation["thoot_id"], user_id):
                continue
            cur_anotation.append(anotation)
        task["predictions"][0]["result"] = cur_anotation
        items.append(task)
    return (items)

def combine_labels(tasks:list[TaskItem])-> list[TaskItem]:
    """Combines nearby annotations that share the same label.

        Groups annotations flagged by `test_if_needs_combine` by their
        rectangle label and merges each group via `combine_anotations`;
        other annotations are left untouched.

        Args:
            tasks (list[TaskItem]): List of tasks to process.

        Returns:
            list[TaskItem]: The same tasks, with each task's result list
                updated to include the combined annotations.

        """
    items:list[TaskItem] = []
    for task in tasks:
        result = task["predictions"][0]["result"]
        cur_anotation:list[InnerAnnotation] = []
        combine_annotaion: dict[str,list[ InnerAnnotation]] = {}
        for anotation in result:
            if test_if_needs_combine(anotation["options"]):

                key = anotation["value"]["rectanglelabels"]

                combine_annotaion.setdefault(key[0], []).append(anotation)
                continue
            cur_anotation.append(anotation)
        task["predictions"][0]["result"] = cur_anotation+combine_anotations(combine_annotaion)
        items.append(task)
    return items

async def check_task_options(tasks:list[TaskItem])->list[TaskItem]:
    """Applies option-based processing steps to a list of tasks.

        Currently combines nearby annotations sharing the same label via
        `combine_labels`. Acts as a central entry point for applying
        option-driven transformations to tasks before they are finalized.

        Args:
            tasks (list[TaskItem]): List of tasks to process.

        Returns:
            list[TaskItem]: The tasks after applying the option-based
                transformations.

        Note:
            This function is meant to grow as new annotation options are
            introduced (e.g. beyond "combine"). New options should be
            handled by adding further processing steps here, so this
            function stays the single place where all option-based task
            transformations are applied.
        """
    task:list[TaskItem] = combine_labels(tasks)
    task = await remove_labels(task)
    task = add_ai(task)

    return task
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

def create_cluster(annotations: list[InnerAnnotation])->list[list[InnerAnnotation]]:
    """Groups annotations into clusters of nearby teeth.

        An annotation is added to the first existing cluster where at
        least one member is "near" it, according to
        `check_if_two_theeth_are_near_each_other`, based on the tooth
        number extracted from `thoot_id` (characters at index 1:2). If no
        matching cluster is found, a new cluster is created for it.

        Args:
            annotations (list[InnerAnnotation]): Annotations to cluster.

        Returns:
            list[list[InnerAnnotation]]: List of clusters, where each
                cluster is a list of annotations considered near each
                other.
        """

    clusters: list[list[InnerAnnotation]] = []

    for item in annotations:
        placed = False
        for cluster in clusters:

            if any(
                check_if_two_theeth_are_near_each_other(
                    (int(item["thoot_id"][1:3])), (int(other["thoot_id"][1:3]))
                )
                for other in cluster
            ):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return clusters

def get_thooth_id_from_cluster(cluster:list[InnerAnnotation])-> str:
    """Returns the highest thoot_id in a cluster of annotations.

        Compares annotations by the third character (index 2) of their
        `thoot_id` — i.e. the tooth's position digit — and returns the
        full `thoot_id` of the annotation with the highest value at that
        position. If the cluster is empty, the default `"0000"` is
        returned.

        Args:
            cluster (list[InnerAnnotation]): Annotations to compare.

        Returns:
            str: The `thoot_id` of the annotation with the highest
                position digit, or `"0000"` if the cluster is empty.
        """
    highest_thood_id:str = "0000"
    for item in cluster:
        cur_thooth_id = item["thoot_id"]
        if cur_thooth_id[2] > highest_thood_id[2]:
            highest_thood_id =  cur_thooth_id

    return highest_thood_id



def combine_anotations(dict_combinations:dict[str, list[InnerAnnotation]])->list[InnerAnnotation]:
    """Merges grouped annotations into single combined annotations.

    For each label group, clusters its annotations by tooth proximity
    via `create_cluster`, then merges each cluster into a single
    annotation: the bounding box is expanded to enclose all rectangles
    in the cluster (via `get_new_rectangle`), the tooth id is derived
    from the cluster (via `get_thooth_id_from_cluster`), and all other
    fields (label, from_name, to_name, type, id, score, options) are
    copied from the cluster's first annotation.

    Args:
        dict_combinations (dict[str, list[InnerAnnotation]]): Mapping
            from rectangle label to the list of annotations sharing
            that label, to be clustered and merged.

    Returns:
        list[InnerAnnotation]: One merged annotation per cluster,
            across all label groups.
    """
    new_annotations: list[InnerAnnotation] =[]

    for annotations in dict_combinations.values():
        clusters = create_cluster(annotations)

        for cluster in clusters:
            x: float = 0
            y: float = 0
            width: float = 0
            height: float = 0
            thoot_id:str = get_thooth_id_from_cluster(cluster)

            for item in cluster:
                x, y, width, height = get_new_rectangle(item, x, y, width, height)


            value = Value({
                "rotation": 0,
                "rectanglelabels": cluster[0]["value"]["rectanglelabels"],
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            })

            annotation = InnerAnnotation({
                "from_name": cluster[0]["from_name"],
                "to_name": cluster[0]["to_name"],
                "type": cluster[0]["type"],
                "id": cluster[0]["id"],
                "value": value,
                "score": cluster[0]["score"],
                "options": cluster[0]["options"],
                "thoot_id": thoot_id,
            })
            new_annotations.append(annotation)

    return new_annotations

def check_if_two_theeth_are_near_each_other(number_one:int,number_two:int,distance:int = 1)->bool:
    """Checks whether two tooth numbers are within a given distance.

        Args:
            number_one (int): First tooth number.
            number_two (int): Second tooth number.
            distance (int): Maximum allowed difference between the two
                numbers for them to be considered near each other.
                Defaults to 1.

        Returns:
            bool: True if the absolute difference between `number_one` and
                `number_two` is less than or equal to `distance`, False
                otherwise.
        """
    if min(number_one,number_two) == 11 and max(number_one,number_two) == 21 or  min(number_one,number_two) == 31 and max(number_one,number_two) == 41:
        return True

    return  abs(number_one -number_two) <= distance




async def check_if_label_removed(options:str,thooth_id:str,user_id:int)->bool:
    """Checks whether an annotation's label should be considered removed.

        An annotation is treated as removed if it qualifies as either an
        inward duplicate (`test_if_inward`) or an outward duplicate
        (`test_if_outward`).

        Args:
            options (str): Comma-separated list of option flags.
            thooth_id (str): Identifier of the tooth the annotation
                belongs to.

        Returns:
            bool: True if the annotation should be removed, False
                otherwise.
        """
    if test_if_no_overlapp(options)and await is_overlapping(thooth_id,user_id):

         return True
    return test_if_inward(options,thooth_id) or test_if_outward(options,thooth_id)

async def is_overlapping(thooth_id:str,user_id:int,offset:float=0.1)->bool:
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
    thoot1,thoot2 =  find_thooth_id_oround(thooth_id)
    if thoot2 == None:
        return False
    thoot1_id = await get_thooth_id(thoot1)
    thoot2_id = await get_thooth_id(thoot2)
    refrence_path = await get_refrence_image(user_id)
    image_path1 = await get_theeh_picture(thoot1_id, user_id)
    image_path2 = await get_theeh_picture(thoot2_id, user_id)
    diff_path1 = await get_difference(refrence_path, image_path1)
    x_pct1, _y_pct1, w_pct1, _h_pct1 = await get_json_cordinates(diff_path1)
    diff_path2 = await get_difference(refrence_path, image_path2)
    x_pct2, _y_pct2, w_pct2, _h_pct2 = await get_json_cordinates(diff_path2)

    left_point = min(x_pct1+w_pct1, x_pct2+w_pct2)
    right_point = max(x_pct1+w_pct1, x_pct2+w_pct2)
    return left_point + offset >= right_point

def find_thooth_id_oround(thooth_id:str)-> Tuple[int,int|None]:
    thooth0 =  int(thooth_id[1:3])-1
    thooth1 =  int(thooth_id[1:3])+1
    if thooth1%10 >= 9:
        return thooth0,None
    return thooth0,thooth1
