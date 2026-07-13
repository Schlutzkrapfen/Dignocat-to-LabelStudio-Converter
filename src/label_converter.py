import csv
import os

from numpy.ma.core import empty


def load_label_mapping()-> dict["str",dict["str","str"]]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "label_mapping.csv")
    mapping:dict["str",dict["str","str"]] = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if not isinstance(row["code"], str):
                 continue
            mapping[row["diagnocat_label"]] = {
                "code": row["code"],
                "label_category": row["label_category"].strip(),
            }
    return mapping


def map_label(
    diagnocat_label: str, labels: dict[str, dict[str, str]]
) -> tuple[str, str] | tuple[None, None]:
    entry = labels.get(diagnocat_label)
    if entry is None:
        return None, None
    if entry["label_category"] is empty:
        entry["label_category"] = "label"
    return entry["code"], entry["label_category"]
