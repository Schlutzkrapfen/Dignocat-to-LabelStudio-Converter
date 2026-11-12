from dataclasses import dataclass
from playwright.async_api import Page
@dataclass
class PatientResult:
    """Result of opening a patient page.

    Attributes:
        user_id: Index of the row that was actually opened (may differ from the
            requested index if patients were skipped).
        page: The page navigated to the patient.
        info: Patient information. Only populated in "report" mode.
    """

    user_id: int
    page: Page
    info: dict[str, str] | None = None
