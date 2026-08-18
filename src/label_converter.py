import csv
import os

from numpy.ma.core import empty


def load_label_mapping(ai:bool=False)-> dict[str,list[dict[str,str]]]:
    """
        Load the Diagnocat label mapping from a TSV file.

        Reads `label_mapping.csv` (tab-separated) located one directory above
        this file, and builds a mapping from each `diagnocat_label` to its
        corresponding `code`, `label_category`and 'options'.
        Args:
            ais:

        Returns:
            dict[str, dict[str, str]]: Mapping from label name to a dict with
                "code" and "label_category" keys.
        """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if ai:
        csv_path = os.path.join(base_dir, "AI-Models/ai-labels.csv")
    else:
        csv_path = os.path.join(base_dir, "label_mapping.csv")
    mapping: dict[str, list[dict[str, str]]] = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            code = (row.get("code") or "").strip()
            if not code:
                continue
            if ai:
                label:str = row["ai_label"].strip()
            else:
                label:str = row["diagnocat_label"].strip()
            mapping.setdefault(label, []).append({
                "code": code,
                "label_category": (row.get("label_category") or "").strip(),
                "option": (row.get("option") or "").strip(),
            })
    return mapping


def map_label(
    diagnocat_label: str, labels: dict[str, list[dict[str, str]]]
) -> tuple[list[str], list[str], list[str]] :
    """
        Look up the code and category for a Diagnocat label.

        Args:
            diagnocat_label (str): The label name to look up.
            labels (dict[str, dict[str, str]]): Mapping from label names to
                their info, each containing "code", "label_category" and "options".

        Returns:
            tuple[list[str], list[str], list[str]]   (list of code, list of label_category, list of options) if found

        Raises:
            ValueError: when there are no entries in class
        """
    entries = labels.get(diagnocat_label)
    if not entries:
          raise ValueError(f"{diagnocat_label} not used")
    codes:list[str] = []
    label_categorie:list[str] = []
    options:list[str] = []

    for entry in entries:
        if entry["label_category"] is empty:
            entry["label_category"] = "label"

        codes.append(entry["code"])
        label_categorie.append(entry["label_category"])
        options.append(entry["option"])

    return codes,label_categorie,options
