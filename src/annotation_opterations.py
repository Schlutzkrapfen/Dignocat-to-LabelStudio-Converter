
import copy
import re

from PIL import Image

from add_ai import ai_predict, get_which_ai_modell_to_use
from check_options import get_heigt, test_if_ai, test_if_height, test_if_inward, test_if_needs_combine, test_if_no_overlapp, test_if_only_edge, test_if_outward, test_if_split
from dental_logic import check_if_teeth_left, check_if_theeth_top_row, check_if_two_theeth_are_near_each_other, create_cluster, get_thooth_id_from_cluster
from geometry_utils import crop_with_padding, find_edges, get_new_rectangle, is_overlapping
from helper_functions import get_path_from_taskItem, get_user_id_from_TaskItem
from task_item import InnerAnnotation, TaskItem, Value
import statistics
def split_labels(task: TaskItem , new_width:float = 1) -> TaskItem:
    """
        Splits each "splittable" annotation (test_if_split) into two deep-copied
        annotations of width new_width, positioned at the left and right edges
        of the original box.

        Args:
            task: TaskItem with task["predictions"][0]["result"].
            new_width: width to assign to each split annotation.

        Returns:
            task with updated result (mutated in-place).
    """
    result = task["predictions"][0]["result"]
    cur_annotations: list[InnerAnnotation] = []
    half_width = new_width / 2
    teeth_ids:list[str] =[]

    for annotation in result:
        already_split = annotation["value"]["width"] == new_width or annotation["id"].endswith(("_left", "_right"))
        if not test_if_split(annotation["options"]) or already_split:
            cur_annotations.append(annotation)
            continue
        original_width = annotation["value"]["width"]
        original_x = annotation["value"]["x"]

        left_is_already_annotated, right_is_already_annotated = needs_annotation(annotation, teeth_ids)

        if  not left_is_already_annotated:
            left:InnerAnnotation = copy.deepcopy(annotation)
            left["value"]["width"] = new_width
            left["value"]["x"] = original_x - half_width
            left["id"] = f"{annotation['id']}_left"
            cur_annotations.append(left)

        if not right_is_already_annotated:
            right:InnerAnnotation = copy.deepcopy(annotation)
            right["value"]["width"] = new_width
            right["value"]["x"] = original_x - half_width + original_width
            right["id"] = f"{annotation['id']}_right"
            cur_annotations.append(right)
        teeth_ids.append(annotation["thoot_id"])

    task["predictions"][0]["result"] = cur_annotations
    return task

def needs_annotation(annotation: InnerAnnotation, teeth_ids: list[str]) -> tuple[bool, bool]:

    left_is_already_annotated = False
    right_is_already_annotated = False
    for tooth_id in teeth_ids:
        if check_if_two_theeth_are_near_each_other(int(tooth_id[1:3]), int(annotation["thoot_id"][1:3])):
            if check_if_teeth_left(annotation["thoot_id"], tooth_id):
                right_is_already_annotated = True
            else:
                left_is_already_annotated = True
    return left_is_already_annotated, right_is_already_annotated

def get_egdes(task:TaskItem,image:Image.Image,new_width:float = 1)-> TaskItem:
    """

        Args:
            task (TaskItem): Task to process.

        Returns:
            TaskItem: The same task passed in, with
                `predictions[0]["result"]` updated to contain only the
                annotations that """
    result = task["predictions"][0]["result"]
    cur_anotation:list[InnerAnnotation] = []
    half_width = new_width / 2
    teeth_ids:list[str] =[]
    for anotation in result:
        edges_already_added = anotation["value"]["width"] == new_width or anotation["id"].endswith(("_left", "_right"))
        left_is_already_annotated, right_is_already_annotated = needs_annotation(anotation, teeth_ids)
        if not  test_if_only_edge(anotation["options"]) or edges_already_added or left_is_already_annotated and right_is_already_annotated:
            cur_anotation.append(anotation)
            continue
        original_width = anotation["value"]["width"]
        original_x = anotation["value"]["x"]
        cur_image = crop_with_padding(image,original_x,anotation["value"]["y"],original_width,anotation["value"]["height"])
        _w,h = image.size
        edges = find_edges(cur_image, h, new_width)
        print(f"edges: {edges}, left_is_already_annotated: {left_is_already_annotated}, right_is_already_annotated: {right_is_already_annotated}")
        if not left_is_already_annotated and edges[0][3] != 0:
            left:InnerAnnotation = copy.deepcopy(anotation)
            left["value"]["width"] = new_width
            left["value"]["height"] = edges[0][3]
            left["value"]["x"] = original_x+edges[0][0] - half_width
            left["id"] = f"{anotation['id']}_left"
            cur_anotation.append(left)
        if not right_is_already_annotated and edges[1][3] != 0:
            right:InnerAnnotation = copy.deepcopy(anotation)
            right["value"]["width"] = new_width
            right["value"]["height"] = edges[1][3]
            right["value"]["x"] = original_x+edges[1][0] - half_width + original_width
            right["id"] = f"{anotation['id']}_left"
            cur_anotation.append(right)


    task["predictions"][0]["result"] = cur_anotation
    return task

async def remove_labels(task:TaskItem)-> TaskItem:
    """Removes labeled-as-removed annotations from a task.

        Iterates over the annotations contained in the
        first prediction's result (`predictions[0]["result"]`) and keeps
        only those for which `check_if_label_removed` returns False,
        discarding the rest. The task's result list is then replaced with
        the filtered annotations.

        Args:
            task (TaskItem): Task to process.

        Returns:
            TaskItem: The same task passed in, with
                `predictions[0]["result"]` updated to contain only the
                annotations that were not removed."""
    result = task["predictions"][0]["result"]
    user_id = get_user_id_from_TaskItem(task)
    cur_anotation:list[InnerAnnotation] = []
    for anotation in result:
        if await check_if_label_removed(anotation["options"],anotation["thoot_id"], user_id):
            continue
        cur_anotation.append(anotation)
    task["predictions"][0]["result"] = cur_anotation
    return task

def combine_labels(task:TaskItem)-> TaskItem:
    """Combines nearby annotations that share the same label.

        Groups annotations flagged by `test_if_needs_combine` by their
        rectangle label and merges each group via `combine_anotations`;
        other annotations are left untouched.

        Args:
            task (TaskItem): Task to process.

        Returns:
            TaskItem: The same task, with its result list
                updated to include the combined annotations.

        """
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
    return task

def add_ai(task:TaskItem,labels:dict[str,list[dict[str,str]]],image:Image.Image)->TaskItem:

    """Enriches task annotations with AI-predicted labels and scores.

        For each task, opens the associated image and iterates over its
        prediction results. For annotations flagged for AI processing (per
        `test_if_ai`), runs the appropriate AI model to predict a label and
        confidence amount, then updates the annotation's `from_name`,
        `rectanglelabels`, and `score` (averaged with the existing score)
        based on the predicted label's mapping.

        Args:
            task (list[TaskItem]): List of tasks to process. Each task is
                expected to contain image path info and a
                `predictions[0]["result"]` list of annotations.

        Returns:
            list[TaskItem]: The same tasks, with AI-eligible annotations
            updated in place.
    """

    result = task["predictions"][0]["result"]
    cur_anotation:list[InnerAnnotation] = []
    for anotation in result:
        if test_if_ai(anotation["options"]):
            value = anotation["value"]
            cur_amount,cur_name = ai_predict(get_which_ai_modell_to_use(anotation["options"]),crop_with_padding(image,value["x"], value["y"], value["width"], value["height"]))
            anotation["from_name"] = labels[cur_name][0]["label_category"]
            anotation["value"]["rectanglelabels"] = [str(item["code"]) for item in labels[cur_name]]
            anotation["score"] =  float(statistics.mean([anotation["score"],cur_amount]))

        cur_anotation.append(anotation)
    task["predictions"][0]["result"] = cur_anotation
    return task

def add_heigt(task: TaskItem) -> TaskItem:
    """
    Adds height information to the task annotations based on the options.

    Args:
        task (TaskItem): The task to update.

    Returns:
        TaskItem: The updated task with height information added to the annotations.

    """
    cur_anotation:list[InnerAnnotation] = []
    for anotation in task["predictions"][0]["result"]:
        if  test_if_height(anotation["options"]):
            try:
                old_height = anotation["value"]["height"]
                new_height  = old_height * get_heigt(anotation["options"])
                anotation["value"]["height"] = new_height
            except ValueError as e:
                print(e)
                cur_anotation.append(anotation)
                continue
            if check_if_theeth_top_row(anotation["thoot_id"]):
                anotation["value"]["y"] = anotation["value"]["y"] - (new_height - old_height)
        cur_anotation.append(anotation)
    task["predictions"][0]["result"] = cur_anotation
    return task


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
