from app_factory import app_factory
import yaml
import uiautomator2 as u2
import argparse

'''Open the apps and keep running for 10 seconds using Monkey mode.'''
def login_apps(d, app_names):
    for app_name in app_names:
        try:
            app = app_factory(d, app_name)
            app.login()
        except Exception as e:
            print(f"Error in login_apps for app {app_name}: {e}")
            continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser('input android emulator serial number')
    parser.add_argument("--device_serial", help="device serial")
    args = parser.parse_args()
    device = u2.connect(args.device_serial)
    login_yaml_file = "setup/login/login_apps.yaml"
    with open(login_yaml_file, 'r') as file:
        data = yaml.safe_load(file)
    login_apps(device,app_names=data["apps"])