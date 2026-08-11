
def combine_labels():
    """combines same labels that are near each other into one """
    pass

def is_furthers_out(theet_id:str)->bool:
    return theet_id[2] == "8"

def test_if_needs_combine(options:str)->bool:
    for option in options:
           parts = option.split(",")
           for part in parts:
               if part == "combine":
                   return True
    return False
def test_if_inward(options:list[str],thooth_id:str)->bool:
    for option in options:
        parts = option.split(",")
        for part in parts:
            if part == "inward"and is_furthers_out(theet_id=thooth_id):
                return True
    return False
def test_if_outward(options:list[str],thooth_id:str)->bool:
        for option in options:
            parts = option.split(",")
            for part in parts:
                if part == "outward" and not is_furthers_out(theet_id=thooth_id):
                    return True
        return False

def check_if_label_not_saved(options:list[str],thooth_id:str)->bool:
    return test_if_inward(options,thooth_id) or test_if_outward(options,thooth_id)
