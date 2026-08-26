
from __future__ import annotations


import torch
from pathlib import Path
from torch import nn
from typing import cast
from torchvision import transforms, models

from PIL import Image


AI_DIR:Path = Path("AI-Models")




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
