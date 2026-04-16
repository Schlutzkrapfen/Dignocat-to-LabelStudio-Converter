import csv

import os
LABEL_MAPPING = None 

def load_label_mapping():
    # Always finds the CSV relative to this script file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "label_mapping.csv")
    
    mapping = {}
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        print(reader.fieldnames)  # keep this for now to debug
        for row in reader:
            mapping[row["diagnocat_label"]] = row["code"]
    LABEL_MAPPING =  mapping


def map_label(diagnocat_label):
    return LABEL_MAPPING.get(diagnocat_label, None)
