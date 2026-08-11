

from task_item import InnerAnnotation, TaskItem, Value


def combine_labels(tasks:list[TaskItem])-> list[TaskItem]:
    """combines same labels that are near each other into one """
    items:list[TaskItem] = []
    for task in tasks:
        result = task["predictions"][0]["result"]
        cur_anotation:list[InnerAnnotation] = []
        combine_annotaion: dict[str,list[ InnerAnnotation]] = {}
        for anotation in result:
            if anotation["combine"]:

                key = anotation["value"]["rectanglelabels"]

                combine_annotaion.setdefault(key[0], []).append(anotation)
                continue

            cur_anotation.append(anotation)


        task["predictions"][0]["result"] = cur_anotation+combine_anotations(combine_annotaion)


        items.append(task)



    return items
def get_new_rectangle(item:InnerAnnotation,x,y,width,height):
    if item["value"]["x"] < x or x == 0:
        x =item["value"]["x"]
    if item["value"]["y"] < y or y == 0:
        y = item["value"]["y"]
    if item["value"]["width"]+ item["value"]["x"] > width +x:
        if item["value"]["x"] > x:
            width = item["value"]["x"]+item["value"]["width"] -x
        else:
            width = x+item["value"]["width"]-item["value"]["x"]
    else:
        if item["value"]["x"] > x:
            width = item["value"]["x"]+width -x
        else:
            width = x+width-item["value"]["x"]
    if item["value"]["height"]+ item["value"]["y"] > width +y:
        if item["value"]["y"] > y:
            height = item["value"]["y"]+item["value"]["height"] -y
        else:
            height = y+item["value"]["height"]-item["value"]["y"]
    else:
        if item["value"]["y"] > y:
            height = item["value"]["y"]+height -y
        else:
            height = x+width-item["value"]["y"]

    return x,y,width,height
def combine_anotations(dict_combinations:dict[str, list[InnerAnnotation]])->list[InnerAnnotation]:

    new_annotations: list[InnerAnnotation] =[]
    for annotaions in dict_combinations.values():

            x:float = 0
            y:float  = 0
            width:float = 0
            height:float = 0
            for item in annotaions:
                x,y,width,height = get_new_rectangle(item,x,y,width,height)


                values = Value(
                    {
                                "rotation": 0,
                                "rectanglelabels": item["value"]["rectanglelabels"],
                                "x": x,
                                "y": y,
                                "width": width,
                                "height": height,
                    })

                annotation = InnerAnnotation({
                    "from_name": item["from_name"],
                    "to_name": item["to_name"],
                    "type": item["type"],
                    "id": item["id"],
                    "value": values,
                    "score": item["score"],

                    "combine":item["combine"],
                    "thoot_id": item["thoot_id"]
                })
                new_annotations.append(annotation)
    return new_annotations











def is_furthers_out(theet_id:str)->bool:
    return theet_id[2] == "8"

def test_if_needs_combine(options:list[str])->bool:
    for option in options:
           parts = option.split(",")
           for part in parts:
               if part == "combine":
                   return True
    return False
def test_if_inward(options:list[str],thooth_id:str)->bool:
    for option in options:
        parts = option.split(",")
        for part in parts:
            if part == "inward"and is_furthers_out(theet_id=thooth_id):
                return True
    return False
def test_if_outward(options:list[str],thooth_id:str)->bool:
        for option in options:
            parts = option.split(",")
            for part in parts:
                if part == "outward" and not is_furthers_out(theet_id=thooth_id):
                    return True
        return False

def check_if_label_not_saved(options:list[str],thooth_id:str)->bool:
    return test_if_inward(options,thooth_id) or test_if_outward(options,thooth_id)
