# locators.py
from typing import Final


def _cls(prefix: str) -> str:
    """Match an element whose class contains `prefix`, ignoring the trailing hash.

    CSS-module classes like `ConditionTitle-module_container_vpIP9` change
    their hash suffix on redeploy. Matching on the prefix survives that.
    """
    return f'[class*="{prefix}"]'


class Sel:
    # Patient list
    PATIENT_ROW: Final = "tr" + _cls("TableWithInfiniteScroll-module_tableRow")
    PATIENT_COUNT_BADGE: Final = "span" + _cls("Filters-module_amountActive")

    # Patient report
    REPORT_CARD: Final = "div" + _cls("ReportCardLayout-module_container")
    WIDGET_CARD: Final = "section" + _cls("WidgetCard-module_container")
    CONDITION_TITLE: Final = "div" + _cls("ConditionTitle-module_container")
    CONDITION_BUTTON: Final = "button" + _cls("ConditionButton-module_container")
    MASK_FILTER_BUTTON: Final = "button" + _cls("MaskFilterButton-module_container")

    # Generic
    CANVAS: Final = "canvas"
    HUBSPOT_OVERLAY: Final = "#hs-web-interactives-top-anchor"

    @staticmethod
    def section_ending_with(suffix: str) -> str:
        return f'section[id$="{suffix}"]'


class Url:
    SIGN_IN: Final = "https://app.diagnocat.eu/sign-in"
    PATIENTS: Final = "https://app.diagnocat.eu/patients"

    @staticmethod
    def patient(patient_id: str) -> str:
        return f"{Url.PATIENTS}/{patient_id}"
