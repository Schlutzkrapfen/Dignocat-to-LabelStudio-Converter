


from collections import defaultdict

import copy

from annotation_opterations import add_ai, combine_labels, remove_labels, split_labels
from check_options import test_if_ownjson
from label_converter import load_label_mapping
from task_item import InnerAnnotation, TaskItem






async def check_task_options(tasks:list[TaskItem])->dict[str,list[TaskItem]]:
    """Applies option-based processing steps to a list of tasks.

        Combines nearby annotations sharing the same label (`combine_labels`),
        removes annotations flagged as removed (`remove_labels`), applies AI
        processing (`add_ai`), and splits the results into separate tasks
        grouped by label (`split_tasks`). Acts as a central entry point for
        applying option-driven transformations to tasks before they are
        finalized.

        Args:
            tasks (list[TaskItem]): List of tasks to process.


        Note:
            This function is meant to grow as new annotation options are
            introduced (e.g. beyond "combine"). New options should be
            handled by adding further processing steps here, so this
            function stays the single place where all option-based task
            transformations are applied.
            Returns:
                    dict[str, list[TaskItem]]: The processed tasks, grouped by label
                        key (or "main") after combining, removing, and splitting
                        annotations.
                """
    labels = load_label_mapping(ai=True)

    for i, task in enumerate(tasks):
        task = combine_labels(task)
        task = split_labels(task)
        task = await remove_labels(task)
        task = add_ai(task, labels)
        tasks[i] = task
    task_dir:dict[str,list[TaskItem]] = split_tasks(tasks)

    return task_dir

def split_tasks(tasks: list[TaskItem]) -> dict[str, list[TaskItem]]:
    """Splits each task's annotations into separate tasks grouped by label.

        Annotations flagged via `test_if_ownjson` are grouped by their
        rectangle label; all others go under "main". For each group, a deep
        copy of the task is created containing only that group's annotations.

        Args:
            tasks (list[TaskItem]): List of tasks to process.

        Returns:
            dict[str, list[TaskItem]]: Label key -> list of task copies
                containing only the annotations belonging to that key.
        """
    items: dict[str, list[TaskItem]] = defaultdict(list)

    for task in tasks:
        result = task["predictions"][0]["result"]
        cur_anotation: dict[str, list[InnerAnnotation]] = defaultdict(list)

        for anotation in result:
            if test_if_ownjson(anotation["options"]):
                key = anotation["value"]["rectanglelabels"][0]
            else:
                key = "main"
            cur_anotation[key].append(anotation)

        for key, value in cur_anotation.items():
            new_task = copy.deepcopy(task)
            new_task["predictions"][0]["result"] = value
            items[key].append(new_task)

    return dict(items)
