

def test_if_split(options:str) -> bool:
    """Checks whether an annotation has the option splith.
    Args:
        options (str): Comma-separated list of option flags.

    Returns:
        bool: True if the annotation has the option splith,
             False otherwise.
    """
    parts = options.split(",")
    for part in parts:
        if part == "splith":
            return True
    return False
def test_if_height(options:str):
    """Checks whether an annotation has the option height

        Args:
            options (str): Comma-separated list of option flags.

        Returns:
            bool: True if the annotation has the option height,
                    False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part[:6] == "height" :
            return True
    return False

def get_heigt(options:str) -> float:
    """Returns the height of the annotation from the options string.

        Args:
            options (str): Comma-separated list of option flags.

        Returns:
            float: The height of the annotation to multiply with.
        Raises:
            ValueError: If no height is found in the options.
        """
    parts = options.split(",")
    for part in parts:
        if part[:6] == "height" :
            return float(part.split(":")[1])
    raise ValueError("No height found in options")

def test_if_no_overlapp(options:str):
    """Checks whether an annotation has the option neighbors_connect

        Args:
            options (str): Comma-separated list of option flags.

        Returns:
            bool: True if the annotation has the option neighbors_connect,
                 False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part == "neighbors_connect":
            return True
    return False
def test_if_ownjson(options:str):
    """Checks whether an annotation has the option own_json

        Args:
            options (str): Comma-separated list of option flags.

        Returns:
            bool: True if the annotation has the option own,
                 False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part == "own_json":
            return True
    return False
def test_if_outward(options:str,thooth_id:str)->bool:
    """Checks whether an annotation should be removed as an outward duplicate.

        An annotation is considered an outward duplicate if it is flagged
        with "outward" and its tooth is not the furthest-out one for its
        position (i.e. it's a less-relevant outward annotation superseded
        by a further-out tooth).

        Args:
            options (str): Comma-separated list of option flags.
            thooth_id (str): Identifier of the tooth the annotation
                belongs to.

        Returns:
            bool: True if the annotation is an outward duplicate that
                should be removed, False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part == "outward" and not is_furthers_out(theet_id=thooth_id):
            return True
    return False
def check_if_hole(options:str)->bool:
        """Checks whether an annotation has the option hole

            Args:
                options (str): Comma-separated list of option flags.

            Returns:
                bool: True if the annotation has the option hole that
                     False otherwise.
            """
        parts = options.split(",")
        for part in parts:
            if part == "hole" :
                return True
        return False
def test_if_needs_combine(options:str)->bool:
    """Checks whether an annotation is flagged for combination.

        Args:
            options (str): Comma-separated list of option flags.

        Returns:
            bool: True if the "combine" flag is present, False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part == "combine":
            return True
    return False
def test_if_inward(options:str,thooth_id:str)->bool:
    """Checks whether an annotation should be removed as an inward duplicate.

        An annotation is considered an inward duplicate if it is flagged
        with "inward" and its tooth is the furthest-out one for its
        position (i.e. a further-out tooth already covers the same area,
        making this inward annotation redundant).

        Args:
            options (str): Comma-separated list of option flags.
            thooth_id (str): Identifier of the tooth the annotation
                belongs to.

        Returns:
            bool: True if the annotation is an inward duplicate that
                should be removed, False otherwise.
        """
    parts = options.split(",")
    for part in parts:
        if part == "inward"and is_furthers_out(theet_id=thooth_id):
            return True
    return False
def is_furthers_out(theet_id:str)->bool:
    """Checks whether a tooth is the furthest-out one in its position.

        A tooth is considered the furthest out if the third character of
        its identifier (index 2) is "8" (e.g. wisdom teeth, typically
        numbered *8 in dental notation).

        Args:
            theet_id (str): Identifier of the tooth, expected to have its
                position digit at index 2.

        Returns:
            bool: True if the tooth is the furthest-out one, False
                otherwise.
        """
    second_letter = theet_id[2]
    return second_letter == "8"

def test_if_ai(options:str):
    """Checks whether an annotation has the option ai

            Args:
                options (str): Comma-separated list of option flags.

            Returns:
                bool: True if the annotation has the option ai that
                     False otherwise.
    """
    parts = options.split(",")
    for part in parts:
        if part[:2] == "ai" :
            return True
    return False
