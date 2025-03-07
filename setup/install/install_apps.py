import yaml
import uiautomator2 as u2
import time
import argparse
import logging
from uiautomator2 import Device


def handle_popups(d:Device):
    """Check for pop-ups and handle them if they appear."""
    try:
        not_now_button = d.xpath('//*[@text="Not now"]')
        if not_now_button.exists:
            not_now_button.click()
            logging.info("Handled 'Not now' popup.")
    except Exception as e:
        logging.info(f"Error handling popup: {str(e)}")

def install_apps(d:Device, install_yaml_file):
    with open(install_yaml_file, 'r') as file:
        data = yaml.safe_load(file)

    apps = data['apps'] 
    for app in apps:
        installed = False
        logging.info(f"Installing {app['app_name']}")
        d.open_url(app['action_seq']['open_url'])
        time.sleep(10) 

        # Check and handle pop-ups periodically
        start_time = time.time()
        while time.time() - start_time < 10:  # Adjust the duration as needed
            handle_popups(d)
            time.sleep(2)  # Check every 2 seconds'

        try:
            element = d.xpath(app['action_seq']['click_xpath'])
            if element.wait(timeout=5):
                element.click()
                installed = True
                logging.info(f"Waiting for {app['app_name']} app to install...")
                time.sleep(60)
                logging.info(f"{app['app_name']} is installed.")
            else:
                uninstall_element = d.xpath('//*[@text="Uninstall"]')
                Update_element = d.xpath('//*[@text="Update"]')
                if uninstall_element.exists or Update_element.exists:
                    logging.info(f"{app['app_name']} is already installed.")
                    installed = True
                else:
                    logging.info(f"Install button not found for {app['app_name']}.")

        except Exception as e:
            logging.info(f"Error installing {app['app_name']}: {str(e)}")

        if not installed:
            raise Exception(f'Failed to install {app["app_name"]}.')   
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser('input android emulator serial number')
    parser.add_argument("--device_serial", help="device serial")
    args = parser.parse_args()
    device = u2.connect(args.device_serial)
    install_yaml_file = "setup/install/pre_install.yaml"
    install_apps(device,install_yaml_file)