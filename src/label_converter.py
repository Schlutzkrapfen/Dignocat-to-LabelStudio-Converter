import csv
import os
def load_label_mapping():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "label_mapping.csv")
    mapping = {}
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            mapping[row["diagnocat_label"]] = {
                "code": row["code"],
                "label_category": row["label_category"]
            }
    return mapping

def map_label(diagnocat_label, labels):
    entry = labels.get(diagnocat_label, None)
    if entry is None:
        return None, None
    return entry["code"], entry["label_category"]