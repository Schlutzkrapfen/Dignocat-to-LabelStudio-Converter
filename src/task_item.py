from typing import TypedDict


class Prediction(TypedDict):
    id: str
    result: list[dict[str, str]]
    model_version: str
class InnerAnnotation(TypedDict):
        from_name:str
        to_name:str
        type:str
        id: str
        value: str
        score: str

class TaskItem(TypedDict):
    id: str
    data: dict[str, str]
    predictions: list[Prediction]
