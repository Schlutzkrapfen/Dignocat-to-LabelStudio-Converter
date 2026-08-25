
from task_item import InnerAnnotation


def create_cluster(annotations: list[InnerAnnotation])->list[list[InnerAnnotation]]:
    """Groups annotations into clusters of nearby teeth.

        An annotation is added to the first existing cluster where at
        least one member is "near" it, according to
        `check_if_two_theeth_are_near_each_other`, based on the tooth
        number extracted from `thoot_id` (characters at index 1:2). If no
        matching cluster is found, a new cluster is created for it.

        Args:
            annotations (list[InnerAnnotation]): Annotations to cluster.

        Returns:
            list[list[InnerAnnotation]]: List of clusters, where each
                cluster is a list of annotations considered near each
                other.
        """

    clusters: list[list[InnerAnnotation]] = []

    for item in annotations:
        placed = False
        for cluster in clusters:

            if any(
                check_if_two_theeth_are_near_each_other(
                    (int(item["thoot_id"][1:3])), (int(other["thoot_id"][1:3]))
                )
                for other in cluster
            ):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return clusters
def get_thooth_id_from_cluster(cluster:list[InnerAnnotation])-> str:
        """Returns the highest thoot_id in a cluster of annotations.

            Compares annotations by the third character (index 2) of their
            `thoot_id` — i.e. the tooth's position digit — and returns the
            full `thoot_id` of the annotation with the highest value at that
            position. If the cluster is empty, the default `"0000"` is
            returned.

            Args:
                cluster (list[InnerAnnotation]): Annotations to compare.

            Returns:
                str: The `thoot_id` of the annotation with the highest
                    position digit, or `"0000"` if the cluster is empty.
            """
        highest_thood_id:str = "0000"
        for item in cluster:
            cur_thooth_id = item["thoot_id"]
            if cur_thooth_id[2] > highest_thood_id[2]:
                highest_thood_id =  cur_thooth_id

        return highest_thood_id

def convert_thooth_id_to_number(thooth_id:int)->int:
    """
        Convert an FDI-style tooth id into a sequential tooth number (1-32).

        Maps each quadrant to its numeric range, with quadrants 1 and 3
        reversed:
            - Quadrant 1 (11-18) -> 8 down to 1
            - Quadrant 2 (21-28) -> 9 up to 16
            - Quadrant 3 (31-38) -> 24 down to 17
            - Quadrant 4 (41-48) -> 25 up to 32

        Args:
            thooth_id (int): FDI-style tooth id (e.g. 11, 26, 38, 47).

        Returns:
            int: Sequential tooth number in the range 1-32.

        Example:
            >>> convert_thooth_id_to_number(11)
            8
    """
    if thooth_id <20:
        return 8 - (thooth_id - 11)
    elif thooth_id> 20 and thooth_id <30:
        return thooth_id - 12
    elif thooth_id > 30 and thooth_id < 40:
         return 24 - (thooth_id - 31)
    else:
        return thooth_id -16

def check_if_two_theeth_are_near_each_other(number_one:int,number_two:int,distance:int = 1)->bool:
    """Checks whether two tooth numbers are within a given distance. needs the 11-48 format.

        Args:
            number_one (int): First tooth number.
            number_two (int): Second tooth number.
            distance (int): Maximum allowed difference between the two
                numbers for them to be considered near each other.
                Defaults to 1.

        Returns:
            bool: True if the absolute difference between `number_one` and
                `number_two` is less than or equal to `distance`, False
                otherwise.
        """
    if min(number_one,number_two) == 11 and max(number_one,number_two) == 21 or  min(number_one,number_two) == 31 and max(number_one,number_two) == 41:
        return True

    return  abs(number_one -number_two) <= distance

def find_tooth_id_around(tooth_id:str)-> tuple[int,int|None]:
    """
        Get the previous and next tooth numbers within the same quadrant.

        The tooth number is read from `tooth_id[1:3]` (FDI-style notation:
        first digit = quadrant, second digit = tooth position 1-8).

        Args:
            tooth_id (str): Tooth identifier, e.g. "T18" -> tooth number 18.

        Returns:
            Tuple[int, int | None]: (previous_tooth, next_tooth).
                - previous_tooth wraps to the neighboring quadrant when it
                  would fall below position 1 (10->21, 20->11, 30->41, 40->31).
                - next_tooth is None if incrementing would exceed the quadrant
                  (i.e. its last digit would be >= 9).

        Example:
            >>> find_tooth_id_oround("T18")
            (17, None)
            >>> find_tooth_id_oround("T13")
            (12, 14)
            >>> find_tooth_id_oround("T11")
            (21, 12)
        """
    tooth0 =  int(tooth_id[1:3])-1
    tooth1 =  int(tooth_id[1:3])+1
    if tooth0 == 10:
        tooth0 = 21
    elif tooth0 == 20:
        tooth0 = 11
    elif tooth0 == 30:
        tooth0 = 41
    elif tooth0 == 40:
        tooth0 = 31


    if tooth1%10 >= 9:
        return tooth0,None
    return tooth0,tooth1
def check_if_teeth_left(tooth_id1:str, tooth_id2:str)->bool:
    """
        Returns True if tooth_id1 is positioned to the left of tooth_id2,
        based on FDI quadrant/position (left quadrants 1,4; right quadrants 2,3).
        Within the same side, lower/higher position determines order;
        across sides, quadrant alone decides.

        Args:
            tooth_id1, tooth_id2: FDI tooth ids, e.g. "T11", "T48".

        Returns:
            bool: True if tooth_id1 is to the left of tooth_id2.
        """
    quadrant1 = int(tooth_id1[1:2])
    position1 = int(tooth_id1[2:3])
    quadrant2 =  int(tooth_id2[1:2])
    position2 = int(tooth_id2[2:3])
    if quadrant1 == 1 or quadrant1 == 4:
        if quadrant2 == 1 or quadrant2 == 4:
            return position1 > position2
        else:
            return True
    else:
        if quadrant2 == 2 or quadrant2 == 3:
            return position1 < position2
        else:
            return False
