

from pathlib import Path

from PIL.Image import Image


from task_item import InnerAnnotation, TaskItem
AI_DIR:Path = Path("AI-Models")
PADDING_PERCENT:int = 5 #the padding was also used in the training

def add_ai(tasks:list[TaskItem]):
    items:list[TaskItem] = []
    for task in tasks:
        result = task["predictions"][0]["result"]
        cur_anotation:list[InnerAnnotation] = []
        combine_annotaion: dict[str,list[ InnerAnnotation]] = {}
        for anotation in result:
            if test_if_ai(anotation["options"]):
                key = anotation["value"]["rectanglelabels"]
                continue
            cur_anotation.append(anotation)
        items.append(task)
    return items

def crop_with_padding(image: Image, x_pct, y_pct, w_pct, h_pct, padding_pct):
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
def get_which_ai_modell_to_use(options:str):
   return options.split(":")[1]
def test_if_ai(options:str):
        parts = options.split(",")
        for part in parts:
            if part[:2] == "ai" :
                return True
        return False
