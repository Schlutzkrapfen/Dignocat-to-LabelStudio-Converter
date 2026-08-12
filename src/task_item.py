from typing import TypedDict


class Value(TypedDict):
    rotation: int
    rectanglelabels:  list[str]
    x: float
    y: float
    width: float
    height: float
class InnerAnnotation(TypedDict):
        from_name:str
        to_name:str
        type:str
        id: str
        value: Value
        score: float
        options: list[str]
        thoot_id: str



class Prediction(TypedDict):
    id: str
    result: list[InnerAnnotation]
    model_version: str
class TaskItem(TypedDict):
    id: int
    data: dict[str, str]
    predictions: list[Prediction]
