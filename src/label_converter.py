LABEL_MAPPING = {
    "Endodontisch behandelter Zahn": "1.4.2.",
    "Füllung": "1.1.1./1.2.1./1.3.1.",
    "Künstliche Zahnkrone": "1.1.2./1.2.2./1.3.2",
    "Parodontaler Knochenverlust": "2.3.2.",
    "Periapikale Radioluzenz": "2.2.1.",
    "Periimplantitis": "2.2.1.",
    "Sekundäre Karies": "2.1.",
    "Wurzel": "2.10.",
    "Zeichen von Karies": "2.1.",
}

def map_label(diagnocat_label):
    """Maps a Diagnocat label to our label, returns None if not usable."""
    return LABEL_MAPPING.get(diagnocat_label, None)