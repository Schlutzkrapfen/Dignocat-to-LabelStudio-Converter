
from pathlib import Path
import shutil

from json_maker import get_task
from navigation import  go_to_patient, open_tooth_page
from session import Session
from task_item import TaskItem

from playwright.async_api import   TimeoutError as PlaywrightError

OUTPUT_DIR = Path("./used_pictures")
async def  upload_pitcutres(pictures,patient_amount,label_Data,context)-> list[TaskItem]:
    """Uploads patient pictures and creates a task for each patient.

        For each picture, creates a new patient from info extracted from the
        picture, uploads the picture, and builds a task. Processed pictures are
        moved to OUTPUT_DIR.

        Args:
            pictures: Paths to the picture files to upload.
            patient_amount: Number of existing patients. Used as an offset for
                external IDs and label data indexing.
            label_Data: Label data used to build each task.
            context: Browser context used to open the new patient's page.

        Returns:
            A list of tasks, one per successfully processed picture. Pictures
            with missing patient info are skipped.

        Raises:
            FileNotFoundError: If `pictures` is empty.
        """
    tasks = []
    if len(pictures) == 0:
        raise FileNotFoundError(f"no file in folder {len(pictures)}")
    for i, picture in enumerate(pictures):
        await click_new_patient_button()
        info = get_info(picture)
        await add_patient(info["first_name"], info["last_name"], info["birthday"], info["sex"], external_id=str(patient_amount+i+1))
        patient_info = await go_to_patient(context, 0,"upload")
        await upload_patient_picture(picture,patient_info.user_id)
        await open_tooth_page(patient_info.page)

        if patient_info.info is None:
            print("couldn find patient info")
            continue

        tasks.append( await get_task(label_Data,patient_amount+i,patient_info.info))
        move_picture(picture, OUTPUT_DIR)
    return tasks


async def click_new_patient_button():
    """Navigates to the patients page and clicks the 'New Patient' button.

        If the current page is not already the patients page, navigates to it
        first. Then waits for the 'New Patient' button to appear and clicks it.

        Raises:
            LookupError: If the 'New Patient' button is not found on the page.
        """
    page = Session.page
    button = await page.wait_for_selector("button.Patients-module_newPatientButton_ACBBZ")
    if button is None:
        raise LookupError("New patient button not found")
    await button.click()
    print("button clicked")

def refine_info(picture_path: Path)-> tuple[str,str|None,str,str]:
    """Extract patient details from a picture filename.

        The stem is split by ``-``; if that yields only one or two parts, it is
        split by ``_`` instead. Supported layouts:

        - ``first-sex-age`` (3 parts, no last name)
        - ``first-last-sex-age`` (4 parts)
        - ``first-last-<ignored>-sex-age`` (5 parts)

        Args:
            picture_path: Path to the picture; only the stem is used.

        Returns:
            Tuple of ``(first_name, last_name, age, sex)``. ``last_name`` is
            None for the 3-part layout. Note that age comes before sex.

        Raises:
            ValueError: If the stem does not split into 3, 4 or 5 parts.
        """
    parts = picture_path.stem.split("-")
    if len(parts) == 1 or len(parts) == 2:
        parts = picture_path.stem.split("_")
    if len(parts) == 5:
        first_name = parts[0]
        last_name = parts[1]
        age = parts[4]
        sex = parts[3]
    elif len(parts) == 3:
        first_name = parts[0]
        last_name = None
        age = parts[2]
        sex = parts[1]
    elif len(parts) == 4:
        first_name = parts[0]
        last_name = parts[1]
        age = parts[3]
        sex = parts[2]
    else:
        raise ValueError(f"Invalid picture name: {picture_path}")
    return first_name,last_name, age, sex

def get_info(picture_path: Path):
    """Build the patient data dictionary from a picture filename.

        Keys: ``first_name``, ``last_name``, ``sex``, ``age``, ``birthday``.

        - If no last name is in the filename, ``first_name`` is used for it.
        - ``sex`` is ``"Männlich"`` if the filename says ``"M"``, otherwise
          ``"Weiblich"``.
        - ``birthday`` is an approximation: ``11-11-<2026 - age>``.

        Args:
            picture_path: Path to the picture, parsed by ``refine_info``.

        Returns:
            Dictionary with the patient details as strings.

        """
    first_name, last_name, age, sex = refine_info(picture_path)

    dictionary: dict[str, str] = {}
    dictionary["first_name"] = first_name
    if not last_name is None:
        dictionary["last_name"] = last_name
    else:
        dictionary["last_name"] = first_name
    if sex == "M":
        dictionary["sex"] = "Männlich"
    else:
        dictionary["sex"] = "Weiblich"
    dictionary["age"] = age
    year =  2026 - int(dictionary["age"])
    dictionary["birthday"] = f"11-11-{year}"
    return dictionary

def move_picture(picture_path: Path, destination_path: Path):
    """Moves a picture file into the destination directory.

        Creates `destination_path` if it doesn't exist yet.

        Args:
            picture_path: Path to the picture file to move.
            destination_path: Directory to move the picture into.
        """
    if not destination_path.exists():
        destination_path.mkdir(parents=True, exist_ok=True)
    shutil.move(str(picture_path), str(destination_path / picture_path.name))

async def add_patient(
        first_name: str,
        last_name: str,
        dob: str,                      # format: "DD.MM.YYYY" or whatever the datepicker expects
        gender: str = "Männlich",      # "Männlich" | "Weiblich" | "Andere"
        email: str = "",
        external_id: str = "",
        doctor_name: str | None = None # None = keep the pre-filled default
    ):
        """Fills out and submits the patient creation form.

            Waits for the patient form to become visible, then fills in the
            required fields (first name, last name, date of birth, gender) and
            any optional fields that are provided (email, external ID, doctor).
            Finally submits the form.

            Args:
                first_name: Patient's first name.
                last_name: Patient's last name.
                dob: Date of birth, in the format expected by the datepicker
                    (e.g. "DD.MM.YYYY").
                gender: Patient's gender. One of "Männlich", "Weiblich", or
                    "Andere". Defaults to "Männlich".
                email: Patient's email address. Skipped if empty.
                external_id: External patient ID. Skipped if empty.
                doctor_name: Name of the doctor to assign via the doctor
                    react-select field. If None, the pre-filled default doctor
                    is kept and the field is not touched.
        """
        page = Session.page
        form = page.locator("#patient-form")
        await form.wait_for(state="visible")

        await form.locator('input[name="firstName"]').fill(first_name)
        await form.locator('input[name="lastName"]').fill(last_name)

        # 3. Email (optional)
        if email:
            await form.locator('input[name="email"]').fill(email)

        # 5. External patient ID (optional)
        if external_id:
            await form.locator('input[name="patientExternalID"]').fill(external_id)

        # 6. Gender radio
        await form.locator(f'label:has(input[name="gender"][label="{gender}"])').click()
        # force=True because the actual <input> is visually hidden behind the styled <span>

        # 7. Doctor (react-select) — only touch it if a specific doctor is requested
        if doctor_name is not None:
            doctor_select = form.locator(".DoctorsSelect-module_container_SXraQ")
            # remove the currently selected doctor chip, if any
            remove_btn = doctor_select.locator('[aria-label^="Remove"]')
            if await remove_btn.count() > 0:
                await remove_btn.click()
            select_input = doctor_select.locator("input#react-select-5-input")
            await select_input.click()
            await select_input.fill(doctor_name)
            await page.get_by_text(doctor_name, exact=False).click()
        # 4. Date of birth (react-datepicker)
        dob_input = form.locator(".DatePicker-module_input_nXZlF")
        await dob_input.click()
        await dob_input.fill(dob)
            #await dob_input.press("Escape")  # closes the calendar popup without changing focus issues
        # 8. Submit
        submit_btn = page.locator('button[form="patient-form"][type="submit"]')


        await submit_btn.click()
        print(f"Patient '{first_name} {last_name}' submitted")

async def upload_patient_picture(picture_dir:Path,curren_user:int):
    """Uploads a Pano study image for the current patient.

       Clicks the "Pano" button, sets the given file on the upload input,
       and submits the form.

       Args:
           picture_dir: Path to the image file to upload.
       """

    try:
        page = Session.require_user_page()
        button = page.locator('button[type="button"]').filter(has_text="Pano")
        await button.click()
        file_input = page.locator('#upload-study-form input[type="file"]')
        await file_input.set_input_files(picture_dir,timeout= 5000)
        submit_btn = page.locator('button[type="submit"]')
    except PlaywrightError as e:
        print(f"Failed to set input files: {e}now opening patient with index {curren_user+1}")

        #curren_user =await go_to_upload_patient_report(curren_user+1)
        await upload_patient_picture(picture_dir, curren_user)
        return
    await submit_btn.click()
    # Wait until it hits 100
    await page.locator('[role="progressbar"][data-value="100"]').wait_for(timeout=300_000)
