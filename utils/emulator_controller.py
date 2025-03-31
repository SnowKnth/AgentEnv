import subprocess
import logging
import time

class EmulatorController:
    def __init__(self,avd_name,device_serial,params):
        self.avd_name = avd_name
        self.device_serial = device_serial
        self.params = params
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state = "off" # off or on， the state of the emulator

    def load_emulator_with_snapshot(self, snapshot_name="default_boot") -> int:
        """
        Start the emulator and load the specified snapshot.

        Args:
        snapshot_name (str): the name of snapshot.
        """
        try:
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
            logging.info(f"**********************cmd: {cmd}*************************")
            
            self.logger.info(f"Loading emulator '{self.avd_name}' with snapshot '{snapshot_name}'.")
            with open("log/emulator.log", "w") as log_file_handle:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file_handle,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                )

                # 启动日志监控
                if self.monitor_log_for_string(log_file_handle, "Failed to load snapshot 'default_boot'"):
                    self.logger.error("Snapshot default_boot can't be loaded, terminate emulator...")
                    self.exit_emulator()  # 终止子进程
                    return -1
                else:                   
                    self.state = "on"
                    return 1
        except Exception as e:
            self.logger.exception(f"Error loading emulator with snapshot: {e}")
            return -1

    def monitor_log_for_string(self, log_file_handle, target_string):
        """
        监控日志文件是否包含目标字符串。

        Args:
            log_file (str): 日志文件路径。
            target_string (str): 要查找的目标字符串。
        """
        try:
            # 移动到文件末尾
            import os
            log_file_handle.seek(0, os.SEEK_END)
            start_time = time.time()
            timeout = 30  # 30秒
            lineCount = 0
            while not (time.time() - start_time > timeout and lineCount > 35):
                line = log_file_handle.readline()
                if line:
                    if target_string in line:
                        self.logger.error(f"检测到目标字符串: {target_string}")
                        return True  # 检测到目标字符串
                else:
                    lineCount += 1
                    time.sleep(0.2)  # 等待文件更新
        except KeyboardInterrupt:
             self.logger.warning("监控被中断")
        return False

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
    #     logging.info(f"**********************cmd: {cmd}*************************")
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
        is_new_load=self.load_emulator_with_snapshot()
        while is_new_load<0:
            self.logger.info("loading emulator failed, retrying...")
            is_new_load=self.load_emulator_with_snapshot()
            time.sleep(10)
        if is_new_load==1:
            self.logger.info("emulator loaded successfully!")
            time.sleep(30) # waiting for emulator to start
