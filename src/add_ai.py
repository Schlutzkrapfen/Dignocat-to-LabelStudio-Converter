
from __future__ import annotations
from os import path
import uuid



import cv2
import torch
from pathlib import Path
from torch import nn
from typing import cast
from torchvision import transforms, models

from PIL import Image
from ultralytics.models.yolo import YOLO

from annotation_opterations import add_annotation_to_task
from check_options import test_if_local_ai
from helper_functions import get_path_from_taskItem
from json_maker import inner_json, outer_json
from task_item import InnerAnnotation, TaskItem
import task_item


AI_DIR:Path = Path("AI-Models")

def add_local_ai(task:TaskItem,labels:dict[str,list[dict[str,str]]]):
    for list in labels.values():
        print(f"DRUGS:{list}")
        for option in list:
            ai_path:Path |None = None
            label_category:str = ""
            label_name:str = ""


            for key,value in option.items():
                if key == "options" and test_if_local_ai(value):
                    ai_path = get_which_ai_modell_to_use(value)
                elif key == "label_category" :
                    label_category = value
                elif key == "code":
                    label_name = value


            if ai_path is not None:
                inner = ai_make_predtioction(ai_path,task,label_category,label_name)
                add_annotation_to_task(task,inner)

            ai_path = None




    return task


def ai_make_predtioction(ai_path:Path,task:TaskItem,label_cotegory:str,name:str)-> InnerAnnotation:
    image_path = get_path_from_taskItem(task)

    model = YOLO(ai_path)
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to read image: {image_path}")


    img_h, img_w = img.shape[:2]

    results =model.predict(source=image_path, conf=0.05, iou=0.5)

    boxes = results[0].boxes
    if not boxes or len(boxes) == 0:
        raise ValueError(f"No boxes found in image: {image_path}")


    mask = boxes.cls == model.cap_class_id
    cap_boxes = boxes[mask]
    sorted_idx = (-cap_boxes.conf).argsort()
    top_k_boxes = cap_boxes[sorted_idx][:2]

    result_item :InnerAnnotation | None = None
    for box in top_k_boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        x = x1 / img_w * 100
        y = y1 / img_h * 100
        width = (y2 - y1) / img_h * 100
        height = (y2 - y1) / img_h * 100
        result_item = inner_json(name,x,y,width,height,222,str(f"{conf*100}%"),label_cotegory,"",thoot_id="0000")

    if result_item is None:
        raise ValueError("resultItem is null")


    return result_item


def ai_predict(ai_path: Path, image: Image.Image) -> tuple[float,str]:
    """Runs image classification inference using a saved ResNet18 checkpoint.

        Loads a ResNet18 model and its class names from a checkpoint file,
        preprocesses the input image (resize, tensor conversion, and
        normalization), and runs inference to predict the most likely class.

        Args:
            ai_path (Path): Path to the model checkpoint file. The checkpoint
                must contain a "model_state" (state dict) and "class_names"
                (list of class labels).
            image (Image.Image): The PIL image to classify.

        Returns:
            tuple[float, str]: A tuple of (confidence, predicted_class), where
            `confidence` is the softmax probability (0-1) of the predicted
            class, and `predicted_class` is the predicted class name.
    """
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

    confidence = probs[predicted_idx].item()
    predicted_class = class_names[predicted_idx]
    return confidence,predicted_class


def get_which_ai_modell_to_use(options:str)-> Path:
    """Resolves the AI model path from an options string.
        Args:
            options (str): A string containing the model identifier in the
                format "ai:model_name" (e.g. "ai:gpt4"). The part
                after the colon is used as the model's filename/subpath.
        Returns:
            Path: Full path to the model, obtained by joining AI_DIR with
            the value after the colon in `options`.
            Raises:
                ValueError: If no AI model is found in the options string.
    """
    for part in options.split(","):
        if part[:2] == "ai":
            path= Path(AI_DIR /  options.split(":")[1])
            return path
    raise ValueError(f"No AI model found in options: {options}")
