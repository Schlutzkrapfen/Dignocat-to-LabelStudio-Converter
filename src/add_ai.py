
from __future__ import annotations

from typing_extensions import Tuple

import torch
import statistics
from pathlib import Path
from torch import nn
from typing import cast
from torchvision import transforms, models

from PIL import Image


from helper_functions import  get_path_from_taskItem
from label_converter import load_label_mapping
from task_item import InnerAnnotation, TaskItem
AI_DIR:Path = Path("AI-Models")
PADDING_PERCENT:int = 5 #the padding was also used in the training

def add_ai(tasks:list[TaskItem]):
    items:list[TaskItem] = []
    labels = load_label_mapping(ai=True)
    print(labels)
    for task in tasks:
        image =Image.open( get_path_from_taskItem(task))
        result = task["predictions"][0]["result"]
        cur_anotation:list[InnerAnnotation] = []
        for anotation in result:
            if test_if_ai(anotation["options"]):
                cur_amount,cur_name = ai_predict(get_which_ai_modell_to_use(anotation["options"]),image)
                anotation["from_name"] = labels[cur_name][0]["label_category"]
                anotation["value"]["rectanglelabels"] = [str(item["code"]) for item in labels[cur_name]]
                anotation["score"] =  float(statistics.mean([anotation["score"],cur_amount]))

            cur_anotation.append(anotation)
        task["predictions"][0]["result"] = cur_anotation
        items.append(task)
    return items


def ai_predict(ai_path: Path, image: Image.Image) -> Tuple[float,str]:
    IMG_SIZE = 224
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    checkpoint = torch.load(ai_path, map_location=device)
    class_names = checkpoint["class_names"]

    model = models.resnet18(weights=None)
    model.fc = nn.Sequential(  # type: ignore[assignment]
        nn.Dropout(0.3),
        nn.Linear(model.fc.in_features, len(class_names)),
    )
    model.load_state_dict(checkpoint["model_state"])
    model = model.to(device)
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                              std=[0.229, 0.224, 0.225]),
    ])

    tensor_image = cast(torch.Tensor, transform(image))
    input_tensor = tensor_image.unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(input_tensor)
        probs = torch.softmax(outputs, dim=1)[0]
        predicted_idx = int(torch.argmax(probs).item())

    print(f"Predicted class: {class_names[predicted_idx]}")
    print(f"Confidence: {probs[predicted_idx]*100:.1f}%")
    confidence = probs[predicted_idx].item()
    predicted_class = class_names[predicted_idx]
    return confidence,predicted_class

def crop_with_padding(image: Image.Image, x_pct, y_pct, w_pct, h_pct, padding_pct):
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
def get_which_ai_modell_to_use(options:str)-> Path:
   path= Path(AI_DIR /  options.split(":")[1])
   return path
def test_if_ai(options:str):
        parts = options.split(",")
        for part in parts:
            if part[:2] == "ai" :
                return True
        return False
