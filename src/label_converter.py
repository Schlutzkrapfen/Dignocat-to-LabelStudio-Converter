import csv
import os

from numpy.ma.core import empty


def load_label_mapping()-> dict["str",dict["str","str"]]:
    """
        Load the Diagnocat label mapping from a TSV file.

        Reads `label_mapping.csv` (tab-separated) located one directory above
        this file, and builds a mapping from each `diagnocat_label` to its
        corresponding `code` and `label_category`.

        Returns:
            dict[str, dict[str, str]]: Mapping from label name to a dict with
                "code" and "label_category" keys.
        """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "label_mapping.csv")
    mapping:dict[str,dict[str,str]] = {}
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
    """
        Look up the code and category for a Diagnocat label.

        Args:
            diagnocat_label (str): The label name to look up.
            labels (dict[str, dict[str, str]]): Mapping from label names to
                their info, each containing "code" and "label_category".

        Returns:
            tuple[str, str] | tuple[None, None]: (code, label_category) if
                found, or (None, None) if `diagnocat_label` is not in `labels`.
        """
    entry = labels.get(diagnocat_label)
    if entry is None:
        return None, None
    if entry["label_category"] is empty:
        entry["label_category"] = "label"
    return entry["code"], entry["label_category"]
