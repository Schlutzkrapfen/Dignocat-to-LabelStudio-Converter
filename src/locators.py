# locators.py
from typing import Final


def _cls(prefix: str) -> str:
    """Builds a CSS selector matching classes that contain `prefix`.

        Ignores the hash suffix of CSS-module classes, which changes on redeploy.

        Args:
            prefix: Stable part of the class name, e.g. `"ConditionTitle-module_container"`.

        Returns:
            A selector such as `[class*="ConditionTitle-module_container"]` as a string.
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

    # locators.py, inside class Sel
    PATIENT_NAME: Final = "h1" + _cls("PatientPersonalInfo-module_patientName")
    PATIENT_DETAILS: Final = "div" + _cls("PatientPersonalInfo-module_patientInfoDetailsWrapper")

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
