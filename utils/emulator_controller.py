import subprocess
import logging
import time

class EmulatorController:
    def __init__(self,avd_name,device_serial,params):
        self.avd_name = avd_name
        self.device_serial = device_serial
        self.params = params
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state = "off"

    def load_emulator_with_snapshot(self, snapshot_name="default_boot") -> int:
        """
        Start the emulator and load the specified snapshot.

        Args:
        snapshot_name (str): the name of snapshot.
        """
        # Check if the emulator is already running
        devices = self.get_adb_devices()
        for device in devices:
            if not device.startswith("emulator"):
                continue
            avd_name = self.get_avd_name_from_device(device)
            if avd_name:
                if avd_name.strip() == self.avd_name:
                    self.logger.info(f"Emulator '{self.avd_name}' is already running. Skipping start.")
                    return 0

        # Build the command to start the emulator
        cmd = ["emulator", "-avd", self.avd_name, "-port", self.device_serial.split("-")[1] , "-snapshot", snapshot_name, "-no-snapshot-save", "-feature", "-Vulkan"]
        for key, value in self.params.items():
            if key == "no-window":
                if value == "true":
                    cmd.append(f"-{key}")
            else:
                cmd.append(f"-{key}")
                cmd.append(f"{value}")

        self.logger.info(f"cmd: {cmd}")
        print(f"**********************cmd: {cmd}*************************")
        try:
            self.logger.info(f"Loading emulator '{self.avd_name}' with snapshot '{snapshot_name}'.")
            subprocess.Popen(cmd)
            self.state = "on"
            return 1
        except Exception as e:
            self.logger.error(f"Error loading emulator with snapshot: {e}")
            return -1

    def get_adb_devices(self):
        """
        Get the list of connected devices using adb devices.

        Returns:
        list: A list of connected device IDs.
        """
        try:
            output = subprocess.check_output(["adb", "devices"]).decode("utf-8")
            devices = [line.split()[0] for line in output.splitlines() if line.strip() and not line.startswith("List of devices attached")]
            return devices
        except Exception as e:
            self.logger.error(f"Error getting adb devices: {e}")
            return []

    def get_avd_name_from_device(self, device_id):
        """
        Get the AVD name from the device ID using adb emu avd name.

        Args:
        device_id (str): The device ID returned by adb devices.

        Returns:
        str: The AVD name or None if not found.
        """
        try:
            output = subprocess.check_output(["adb", "-s", device_id, "emu", "avd", "name"]).decode("utf-8")
            # Extract the AVD name from the output
            avd_name = output.strip().split('\r\n')[0]
            return avd_name
        except Exception as e:
            self.logger.error(f"Error getting AVD name for device {device_id}: {e}")
            return None

    # def load_emulator_with_snapshot(self,snapshot_name="default_boot"):
    #     """
    #     start the emulator and load the specified snapshot.

    #     Args:
    #     snapshot_name (str): the name of snapshot。
    #     """
    #     # cmd = ["emulator", "-avd", self.avd_name, "-snapshot", snapshot_name, "-no-snapshot-save"]
    #     # "no-window"
    #     cmd = ["emulator", "-avd", self.avd_name,"-no-snapshot-save",  "-feature", "-Vulkan"]
    #     for key, value in self.params.items():
    #         if key == "no-window":
    #             if value == "true":
    #                 cmd.append(f"-{key}")
    #         else:
    #             cmd.append(f"-{key}")
    #             cmd.append(f"{value}")

    #     self.logger.info(f"cmd: {cmd}")
    #     print(f"**********************cmd: {cmd}*************************")
    #     try:
    #         self.logger.info(f"Loading emulator '{self.avd_name}' with snapshot '{snapshot_name}'.")
    #         subprocess.Popen(cmd)
    #         self.state = "on"
    #     except Exception as e:
    #         self.logger.error(f"Error loading emulator with snapshot: {e}")

    def exit_emulator(self):
        """
        exit the current running emulator instance.
        """
        try:
            self.logger.info(f"Exiting emulator '{self.avd_name}'.")
            subprocess.run(["adb", "-s", f"{self.device_serial}", "emu", "kill"], check=True)
            self.state = "off"
        except Exception as e:
            self.logger.error(f"Error exiting emulator: {e}")

    def reload_snapshot(self, snapshot_name="default_boot"):
        """
        reload the specified snapshot.

        Args:
        snapshot_name (str): the name of snapshot。
        """
        if self.state == "on":
            # first exit the emulator
            self.exit_emulator()
            time.sleep(20)
            # restart the emulator with the specified snapshot
            self.load_emulator_with_snapshot(snapshot_name)
        else:
            self.load_emulator_with_snapshot(snapshot_name)
