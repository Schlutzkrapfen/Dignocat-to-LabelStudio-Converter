from typing import TypedDict


class InnerAnnotation(TypedDict):
        from_name:str
        to_name:str
        type:str
        id: str
        value:  dict[str, int | list[str] | float]
        score: str

class Prediction(TypedDict):
    id: str
    result: list[InnerAnnotation]
    model_version: str
class TaskItem(TypedDict):
    id: int
    data: dict[str, str]
    predictions: list[Prediction]
