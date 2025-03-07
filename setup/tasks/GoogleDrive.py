import time
from uiautomator2 import Device
import logging
from setup.tasks.BaseTaskSetup import BaseTaskSetup,SetupFailureException
# Google Drive app version: 2.21.241.10.80

def get_screenshot(d: Device) -> None:
    screenshot = d.screenshot("screenshot.png")
    d.push("screenshot.png", "/sdcard/Pictures/") 
    time.sleep(2)

def create_sheet(d: Device, sheet_name: str = "Testbed") -> None:
    """
    Creates a new Google Sheet in Google Drive and renames it to 'sheet_name'.
    Starts and ends with the user on the Google Drive main page.
    Raises exceptions if any of the required UI elements are not found or interactions fail.
    """
    try:
        # Navigate to "Files" and open "My Drive"
        files_button = d(description="Files")
        if not files_button.wait(timeout=5):
            raise SetupFailureException("Files button not found.")
        files_button.click()

        my_drive = d(text="My Drive")
        if not my_drive.wait(timeout=5):
            raise SetupFailureException("My Drive option not found.")
        my_drive.click()

        # Start the process to create a new Google Sheet
        create_button = d(description="Create")
        if not create_button.wait(timeout=5):
            raise SetupFailureException("Create button not found.")
        create_button.click()

        google_sheets_option = d(description="Google Sheets")
        if not google_sheets_option.wait(timeout=5):
            raise SetupFailureException("Google Sheets option not found.")
        google_sheets_option.click()

        # Return to the main page
        d.press("back")

        # Rename the newly created sheet
        more_actions = d(description="More actions for Untitled spreadsheet")
        if not more_actions.wait(timeout=5):
            raise SetupFailureException("More actions for Untitled spreadsheet not found.")
        more_actions.click()

        rename_option = d(text="Rename")
        if not rename_option.wait(timeout=5):
            raise SetupFailureException("Rename option not found.")
        rename_option.click()

        sheet_name_field = d(resourceId="com.google.android.apps.docs:id/edit_text")
        if not sheet_name_field.wait(timeout=5):
            raise SetupFailureException("Sheet name edit text field not found.")
        sheet_name_field.set_text(sheet_name)

        save_button = d(resourceId="com.google.android.apps.docs:id/positive_button")
        if not save_button.wait(timeout=5):
            raise SetupFailureException("Save button not found.")
        save_button.click()
        
    except Exception as e:
        raise SetupFailureException(f"An error occurred while creating or renaming the sheet: {e}") 


def check_sheet_exist(d: Device, sheet_name: str ="Testbed") -> bool:
    try:
        # Navigate to "Files" 
        files_button = d(description="Files")
        if not files_button.wait(timeout=5):
            raise SetupFailureException("Files button not found.")
        files_button.click()
        
        # Navigate to "My Drive"
        my_drive = d(text="My Drive")
        if not my_drive.wait(timeout=5):
            raise SetupFailureException("My Drive option not found.")
        my_drive.click()

        # Check for the existence of the sheet
        sheet_exists = d(className="android.widget.TextView", description=f"{sheet_name}, Google Sheets").wait(timeout=5)
        return sheet_exists
        
    except Exception as e:
        raise SetupFailureException(f"An error occurred while checking for the sheet: {e}")

class GoogleDriveTask01(BaseTaskSetup):
    '''
    instruction: Upload the latest photo from my device to a new folder named 'Selfie2024' on Google Drive app.
    setup: make sure there is a photo in the device.
    '''
    def __init__(self, device, instruction):
        super().__init__(device, instruction)

    def setup(self):
        # start app
        self.d.app_start("com.google.android.apps.docs", use_monkey=True)
        time.sleep(2)
        get_screenshot(self.d)
        # stop app
        self.d.press("home")
        time.sleep(2)
        self.d.app_stop("com.google.android.apps.docs")


class GoogleDriveTask02(BaseTaskSetup):
    '''
    instruction: Share the 'Testbed' spreadsheet on Google Drive by copy link, make sure anyone with the link can view.
    setup: make sure there is 'Testbed' spreadsheet on Google Drive.
    '''
    def __init__(self, device, instruction):
        super().__init__(device, instruction)

    def setup(self):
        # start app
        self.d.app_start("com.google.android.apps.docs", use_monkey=True)
        time.sleep(2)
        if not check_sheet_exist(self.d):
            create_sheet(self.d)
        else:
            logging.info("Sheet already exists.")
        
        # stop app
        self.d.press("home")
        time.sleep(2)
        self.d.app_stop("com.google.android.apps.docs")