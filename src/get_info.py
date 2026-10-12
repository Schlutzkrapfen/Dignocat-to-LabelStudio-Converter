
from typing import cast

from locators import Sel
from session import Session


async def get_tooth_descriptions() -> list[dict[str, str]]:
    """Extracts tooth names and identifiers from the page.

        Locates all tooth condition title elements on `user_page` and splits
        each one's text into a type and an id.

        Returns:
            A list of dictionaries, where each dictionary contains the "type"
            and "id" of a tooth.

        Raises:
            ValueError: If `user_page` is not initialized.
    """

    user_page = Session.require_user_page()

    divs = await user_page.locator("div.ConditionTitle-module_container_vpIP9").all()
    tooth_types: list[dict[str, str]] = []
    for div in divs:
        part = await div.inner_text()
        parts = part.split()
        tooth_types.append({"type": parts[0], "id": parts[1]})
    return tooth_types
async def get_thooth_id( thoot_id: int)->str:
    """Finds the trailing 4 characters of a section's ID matching the given tooth ID.

        This function searches through dental widget cards on the page, extracts
        the numeric identifier from their condition titles, and matches it against
        the requested tooth_id.

        Args:
            thoot_id: The numerical ID of the tooth to locate.

        Returns:
            The last 4 characters of the matching section's HTML id attribute,
            or raises a Valuerror if no match is found.
        Raises:
                   ValueError: If no section matching the given tooth ID is found.
         """
    user_page = Session.require_user_page()
    sections = await user_page.locator("section.WidgetCard-module_container_1PPfu").all()
    for section in sections:
        div = section.locator("div.ConditionTitle-module_container_vpIP9")
        if await div.count() == 0:
            continue
        token = await div.inner_text()
        tokens = token.split()
        # check for just numbers
        numeric_tokens = [t for t in tokens if t.isdigit()]
        if not numeric_tokens:
            continue
        id = int(numeric_tokens[-1])
        if id == thoot_id:
            section_id:str = cast(str, await section.evaluate("el => el.id"))
            return section_id[-4:]

    raise ValueError(f"Couldn't find thooth {thoot_id}")

async def get_patient_information() -> dict[str, str]:
    """Reads name, age, sex and ID from the open patient page.

    Returns:
        A dict with the keys "name", "age", "sex" and "id".
    """
    user_page = Session.require_user_page()

    name = await user_page.locator(Sel.PATIENT_NAME).inner_text()
    details = await user_page.locator(Sel.PATIENT_DETAILS).locator("p").all_inner_texts()
    # details == ["19 Jahre", "Männlich", "ID: 1106"]

    return {
        "name": name.strip(),
        "age": details[0],
        "sex": details[1],
        "id": details[2].removeprefix("ID:").strip(),
    }
