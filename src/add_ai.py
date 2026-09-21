
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

from check_options import get_which_ai_modell_to_use, test_if_local_ai
from helper_functions import get_path_from_taskItem
from json_maker import inner_json
from task_item import InnerAnnotation, TaskItem

def add_annotations_to_task(task:TaskItem, inneranotation:list[InnerAnnotation])-> TaskItem:
    """Appends new annotations to a task's first prediction result.

        Extends the ``result`` list inside ``task["predictions"][0]`` with the
        provided annotations and writes it back to the task.

        Args:
            task: The task item to update. Must contain at least one entry in
                ``task["predictions"]``, with a ``"result"`` key holding a list.
            inneranotation: The list of annotations to append to the task's
                existing result list.

        Returns:
            The same ``task`` object, with its first prediction's ``result``
            list extended in place.
    """
    result = task["predictions"][0]["result"]
    result.extend(inneranotation)
    task["predictions"][0]["result"] = result
    return task


def add_local_ai(task:TaskItem,labels:dict[str,list[dict[str,str]]]):
    """Runs local AI models on a task for applicable labels and merges results.

        For each label group, checks if a local AI model applies, runs
        prediction if so, and adds the resulting annotations to the task.

        Args:
            task: Task item to annotate.
            labels: Mapping of label group names to lists of label dicts,
                each possibly containing "option", "label_category", "code".

        Returns:
            The updated task item.
        """
    for list in labels.values():

        ai_path:Path |None = None
        label_category:str = ""
        label_name:str = ""


        for key,value in list[0].items():
            if key == "option" and test_if_local_ai(value):
                ai_path = get_which_ai_modell_to_use(value)
            elif key == "label_category" :
                label_category = value
            elif key == "code":
                label_name = value



            if ai_path is not None:
                inner = ai_make_predtioction(ai_path,task,value,label_category,label_name)
                task = add_annotations_to_task(task,inner)

        ai_path = None
    return task


def ai_make_predtioction(ai_path: Path, task: TaskItem, label_cotegory: str, name: str) -> list[InnerAnnotation]:
    """Runs YOLO on a task's image and builds annotations from the top detections.

        Args:
            ai_path: Path to the YOLO model weights.
            task: Task item whose image will be used for prediction.
            label_cotegory: Label category for the annotations.
            name: Annotation name/code.

        Returns:
            Up to 2 annotations for the highest-confidence class-0 detections,
            with coordinates as percentages of image size.

        Raises:
            ValueError: If the image can't be read, no boxes are detected,
                or no annotations could be built.
        """
    image_path = get_path_from_taskItem(task)

    model = YOLO(ai_path)
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to read image: {image_path}")

    img_h, img_w = img.shape[:2]

    results = model.predict(source=image_path, conf=0.05, iou=0.5)

    boxes = results[0].boxes
    if not boxes or len(boxes) == 0:
        raise ValueError(f"No boxes found in image: {image_path}")

    cap_class_id = 0
    mask = boxes.cls == cap_class_id
    cap_boxes = boxes[mask]
    sorted_idx = (-cap_boxes.conf).argsort()
    top_k_boxes = cap_boxes[sorted_idx][:2]

    result_item: list[InnerAnnotation] = []
    i =0
    for  box in top_k_boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        x = x1 / img_w * 100
        y = y1 / img_h * 100
        width = (x2 - x1) / img_w * 100
        height = (y2 - y1) / img_h * 100
        result_item.append( inner_json(name, x, y, width, height, 10000 +i , str(f"{conf*100}%"), label_cotegory, "", thoot_id="0000"))
        i += 1
    if len(result_item) == 0:
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
