
from __future__ import annotations


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
    """Enriches task annotations with AI-predicted labels and scores.

        For each task, opens the associated image and iterates over its
        prediction results. For annotations flagged for AI processing (per
        `test_if_ai`), runs the appropriate AI model to predict a label and
        confidence amount, then updates the annotation's `from_name`,
        `rectanglelabels`, and `score` (averaged with the existing score)
        based on the predicted label's mapping.

        Args:
            tasks (list[TaskItem]): List of tasks to process. Each task is
                expected to contain image path info and a
                `predictions[0]["result"]` list of annotations.

        Returns:
            list[TaskItem]: The same tasks, with AI-eligible annotations
            updated in place.
    """
    items:list[TaskItem] = []
    labels = load_label_mapping(ai=True)
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

def crop_with_padding(image: Image.Image, x_pct, y_pct, w_pct, h_pct, padding_pct):
    """Crops a region of an image, adding padding around it.

        Args:
            image (Image.Image): The PIL image to crop.
            x_pct (float): X coordinate of the region's top-left corner, as % of image width.
            y_pct (float): Y coordinate of the region's top-left corner, as % of image height.
            w_pct (float): Width of the region, as % of image width.
            h_pct (float): Height of the region, as % of image height.
            padding_pct (float): Padding around the region, as % of the region's own size.

        Returns:
            Image.Image: The cropped image, clamped to the original image's bounds.
        """
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
    """Resolves the AI model path from an options string.
        Args:
            options (str): A string containing the model identifier in the
                format "ai:model_name" (e.g. "ai:gpt4"). The part
                after the colon is used as the model's filename/subpath.
        Returns:
            Path: Full path to the model, obtained by joining AI_DIR with
            the value after the colon in `options`.
    """
    path= Path(AI_DIR /  options.split(":")[1])
    return path
def test_if_ai(options:str):
    """Checks whether an annotation has the option ai

            Args:
                options (str): Comma-separated list of option flags.

            Returns:
                bool: True if the annotation has the option ai that
                     False otherwise.
    """
    parts = options.split(",")
    for part in parts:
        if part[:2] == "ai" :
            return True
    return False
