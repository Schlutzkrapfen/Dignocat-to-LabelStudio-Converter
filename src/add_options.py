

from task_item import InnerAnnotation, TaskItem, Value

def remove_labels(tasks:list[TaskItem])-> list[TaskItem]:
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
        cur_anotation:list[InnerAnnotation] = []
        for anotation in result:
            if check_if_label_removed(anotation["options"],anotation["thoot_id"]):
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

def check_task_options(tasks:list[TaskItem])->list[TaskItem]:
    task:list[TaskItem] = combine_labels(tasks)

    return remove_labels(task)
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
                    (int(item["thoot_id"][1:2])), (int(other["thoot_id"][1:2]))
                )
                for other in cluster
            ):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])

    return clusters

def combine_anotations(dict_combinations:dict[str, list[InnerAnnotation]])->list[InnerAnnotation]:

    new_annotations: list[InnerAnnotation] =[]

    for annotations in dict_combinations.values():
        clusters = create_cluster(annotations)

        for cluster in clusters:
            x: float = 0
            y: float = 0
            width: float = 0
            height: float = 0

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
                "thoot_id": cluster[0]["thoot_id"],
            })
            new_annotations.append(annotation)

    return new_annotations

def check_if_two_theeth_are_near_each_other(number_one:int,number_two:int,distance:int = 1)->bool:
    return  abs(number_one -number_two) <= distance


def is_furthers_out(theet_id:str)->bool:
    second_letter = theet_id[2]
    return second_letter == "8"




def test_if_needs_combine(options:str)->bool:
    """Checks whether an annotation is flagged for combination.

        Args:
            options (str): Comma-separated list of option flags.

        Returns:
            bool: True if the "combine" flag is present, False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part == "combine":
            return True
    return False
def test_if_inward(options:str,thooth_id:str)->bool:
    """Checks whether an annotation should be removed as an inward duplicate.

        An annotation is considered an inward duplicate if it is flagged
        with "inward" and its tooth is the furthest-out one for its
        position (i.e. a further-out tooth already covers the same area,
        making this inward annotation redundant).

        Args:
            options (str): Comma-separated list of option flags.
            thooth_id (str): Identifier of the tooth the annotation
                belongs to.

        Returns:
            bool: True if the annotation is an inward duplicate that
                should be removed, False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part == "inward"and is_furthers_out(theet_id=thooth_id):
            return True
    return False
def test_if_outward(options:str,thooth_id:str)->bool:
    """Checks whether an annotation should be removed as an outward duplicate.

        An annotation is considered an outward duplicate if it is flagged
        with "outward" and its tooth is not the furthest-out one for its
        position (i.e. it's a less-relevant outward annotation superseded
        by a further-out tooth).

        Args:
            options (str): Comma-separated list of option flags.
            thooth_id (str): Identifier of the tooth the annotation
                belongs to.

        Returns:
            bool: True if the annotation is an outward duplicate that
                should be removed, False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part == "outward" and not is_furthers_out(theet_id=thooth_id):
            return True
    return False

def check_if_label_removed(options:str,thooth_id:str)->bool:
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
    return test_if_inward(options,thooth_id) or test_if_outward(options,thooth_id)
