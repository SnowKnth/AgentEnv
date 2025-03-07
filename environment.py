from typing import Any, Dict, Iterator
import os
from device import Device
import time
import logging
import pandas as pd
import json
import re
import subprocess

from utils.parse_action import parse_action_string, parse_action
from utils.emulator_controller import EmulatorController
from setup.tasks.TaskSetUp import TaskSetUp
from utils.transxml2vh import xml_string_to_json

class PrepareApps:
    def __init__(self, device_serial) -> None:
        self.device_serial = device_serial
        pass
    
    def get_apk_path(self, package_name):
    # 获取 APK 文件路径
        result = subprocess.run(
            ["adb", "-s", self.device_serial, "shell", "pm", "path", package_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            apk_path = result.stdout.strip().replace("package", "")
            if apk_path:
                pp = apk_path.split(":")
                return apk_path.split(":")[1].strip()
            else:
                raise Exception(f"APK path not found for package: {package_name}")
        else:
            raise Exception(f"Failed to get APK path for package: {package_name}")

    def pull_apk(self, apk_path, local_path):
        # 将 APK 文件从设备中拉取到本地
        result = subprocess.run(
            ["adb", "-s", self.device_serial, "pull", apk_path, local_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"Failed to pull APK file: {result.stderr}")



    def pull_installed_apps(self, local_apk_dir, instruction_fp="docs/instructions/llamatouch_task_metadata.csv") -> None:
        # 设置日志记录
        # logging.basicConfig(filename='pull_installed_apps.log', level=logging.ERROR, 
                            # format='%(asctime)s - %(levelname)s - %(message)s')
        
        try:
            instructions = pd.read_csv(instruction_fp, sep='\t')
        except Exception as e:
            logging.error(f"Error reading CSV file: {e}")
            return
        
        app_dict = {} # {episode: [package_name, app_short]}

        for _, row in instructions.iterrows():
            try:
                path = row['path']
                app_short = row['app']
                episode = row['episode']

                # 连接路径
                full_path = os.path.join("../dataset/llamatouch_dataset_0521/", path)
                dest_path = os.path.join(local_apk_dir, app_short+'.apk')

                # 检查路径是否存在
                if not os.path.exists(full_path):
                    logging.error(f"Path does not exist: {full_path}")
                    continue

                # 获取目录下的所有i.activity文件
                activity_files = [f for f in os.listdir(full_path) if re.match(r'\d+\.activity', f)]

                # 提取文件名中的数字并逆序排序
                activity_files.sort(key=lambda x: int(re.search(r'\d+', x).group()), reverse=True)

                for activity_file in activity_files:
                    activity_file_path = os.path.join(full_path, activity_file)

                    # 读取文件内容
                    try:
                        with open(activity_file_path, 'r') as file:
                            content = file.read().strip()
                            # 分割内容并提取包名
                            package_name = content.split('/')[0]
                            apk_path = self.get_apk_path(package_name)
                            self.pull_apk(apk_path, dest_path)
                            logging.info(f"Extracted package name: {package_name} from {activity_file_path}")
                            # 更新 app_dict
                            if episode not in app_dict:
                                app_dict[episode] = [package_name, app_short]
                            break
                    except Exception as e:
                        logging.error(f"Error reading or processing file {activity_file_path}: {e}")

            except Exception as e:
                logging.error(f"Error processing row: {e}")
        # 将 app_dict 写入 JSON 文件
        self.save_app_dict(app_dict, "app_dict.json")
    
    def save_app_dict(self, app_dict, json_file_path):
        try:
            with open(json_file_path, 'w') as json_file:
                json.dump(app_dict, json_file, indent=4)
            logging.info(f"app_dict saved to {json_file_path}")
        except Exception as e:
            logging.error(f"Error saving app_dict to JSON file: {e}")

    @staticmethod
    def load_app_dict(json_file_path):
        try:
            with open(json_file_path, 'r') as json_file:
                app_dict = json.load(json_file)
            logging.info(f"app_dict loaded from {json_file_path}")
            return app_dict
        except Exception as e:
            logging.error(f"Error loading app_dict from JSON file: {e}")
            return None
            


class AgentEnv:
    def __init__(self, avd_name = None, emulator_controller_args=None,\
                 max_steps=30,local_output_path="exec_output",instruction_fp="docs/instructions/llamatouch_task_metadata.csv") -> None:
        
        self.device_serial = f"emulator-{emulator_controller_args['port']}"
        self.logger = logging.getLogger(self.__class__.__name__)
        self.local_output_path = local_output_path
        os.makedirs(self.local_output_path, exist_ok=True)
        self.device = Device(device_serial=self.device_serial)
        self.emulator_controller = EmulatorController(avd_name=avd_name,device_serial=self.device_serial,params=emulator_controller_args)
        
        self.instructions = pd.read_csv(instruction_fp, sep='\t')
        self.instruction_generator = self._generate_instruction()
        self.max_steps = max_steps

        self.current_action = "None|None|None"
        self.state_history = []
        self.episode_end = False
        self.current_steps = 0
    

    def _generate_instruction(self) -> Iterator[tuple[str, str]]:
        for _, row in self.instructions.iterrows(): # add: gr_path, app_short, episode,
            yield row['description'], row['path'], row['app'], row['episode'], os.path.join(self.local_output_path, row['category'], str(row['episode']))


    def _setup_directories(self, base_path, subdirectories) -> list[str]:
        paths = []
        for subdir in subdirectories:
            dir_path = os.path.join(base_path, f'captured_data/{subdir}')
            os.makedirs(dir_path, exist_ok=True)
            paths.append(dir_path)
        return paths
    
    def _execute_action(self, action_type, action_para) -> bool:
        status = None
        w, h = self.device.get_screen_size()
        if action_type == "CLICK":
            status = self.device.click(action_para[0] * w, action_para[1] * h)
        elif action_type == "SWIPE":
            status = self.device.swipe(action_para[0] * w, action_para[1] * h, action_para[2] * w, action_para[3] * h)
        elif action_type == "TYPE":
            # have already processed special characters
            status = self.device.input_text(action_para)
        elif action_type == "PRESS_ENTER":
            status = self.device.enter()
        elif action_type == "PRESS_BACK":
            status = self.device.back()
        elif action_type == "PRESS_HOME":
            status = self.device.home()
        return status

    def _trans_action_format(self,action_type, action_para) -> Any:

        width, height = self.get_device_size()
        if action_type == "CLICK":
            return f"{action_type}|{str(action_para)}|NULL|{width}|{height}"
        elif action_type == "SWIPE":
            return f"{action_type}|{str(action_para[:2])}|{str(action_para[2:])}|{width}|{height}"
        elif action_type == "TYPE":
            # action_para.replace("\ ", " ")
            return f"{action_type}|{action_para}|NULL|{width}|{height}"
        elif action_type == "PRESS_BACK":
            return f"{action_type}|NULL|NULL|{width}|{height}"
        elif action_type == "PRESS_HOME":
            return f"{action_type}|NULL|NULL|{width}|{height}"
        elif action_type == "PRESS_ENTER":
            return f"{action_type}|NULL|NULL|{width}|{height}"
        elif action_type == "STATUS_TASK_COMPLETE":
            return f"{action_type}|NULL|NULL|{width}|{height}"
        elif action_type == "STATUS_TASK_IMPOSSIBLE":
            return f"{action_type}|NULL|NULL|{width}|{height}"
        else:
            raise ValueError("action_type not supported")
    
    def _backtohome(self) -> None:
        self.device.home()
    
    def set_up(self) -> None:
        self.logger.info("loading emulator...")
        is_new_load=self.emulator_controller.load_emulator_with_snapshot()
        while is_new_load<0:
            self.logger.info("loading emulator failed, retrying...")
            is_new_load=self.emulator_controller.load_emulator_with_snapshot()
            time.sleep(10)
        if is_new_load==1:
            self.logger.info("emulator loaded successfully!")
            time.sleep(30) # waiting for emulator to start
        self.logger.info("connecting to device...")
        self.device.connect()
        self._backtohome()
        time.sleep(2)
        self.logger.info("AgentEnv setup over!")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the device
        """
        # save view hierarchy, screenshot, top activity name and agent action in local
        
        screenshot_dir_path, activity_dir_path, vh_dir_path, vh_json_dir_path = self._setup_directories(\
                  self.task_output_path, ['screenshot', 'activity', 'xml', 'vh'])

        self.logger.info("getting the agent env state...")
        
        view_hierarchy = self.device.get_viewhierachy()
        view_hierarchy_json = xml_string_to_json(view_hierarchy)
        activity_name = self.device.get_top_activity_name()
        screenshot = self.device.get_screenshot()
        
        tag = self.current_steps
        view_hierarchy_path = os.path.join(vh_dir_path, f"{tag}.xml")
        view_hierarchy_json_path = os.path.join(vh_json_dir_path, f"{tag}.vh")
        activity_path = os.path.join(activity_dir_path, f"{tag}.activity")
        screenshot_path = os.path.join(screenshot_dir_path, f"{tag}.png")

        with open(view_hierarchy_path, "w", encoding="utf-8") as vh_file:#.xml
            vh_file.write(view_hierarchy)

        with open(view_hierarchy_json_path, "w", encoding="utf-8") as vh_json_file:#.vh
            json.dump(view_hierarchy_json, vh_json_file, ensure_ascii=False, indent=4)
        
        with open(activity_path, "w", encoding="utf-8") as activity_file:#.activity
            activity_file.write(activity_name)
        
        screenshot.save(screenshot_path)#.png

        self.logger.info(f"View hierarchy saved to: {view_hierarchy_path}")
        self.logger.info(f"Activity saved to {activity_path}")
        self.logger.info(f"Screenshot saved to: {screenshot_path}")
        
        state = {
            "screenshot": screenshot, # Pillow.Image
            "screenshot_path": screenshot_path, # str
            "view_hierarchy": view_hierarchy, # str
            "view_hierarchy_path": view_hierarchy_path, # str
            "view_hierarchy_json": view_hierarchy_json, # json
            "view_hierarchy_json_path": view_hierarchy_json_path # str
            # view_hierarchy_json example
            # [
            # {'bounds': [[0, 0], [0, 0]], 'checkable': False, 'checked': False, 'children': [1, 30, 48], 'class': None, 'clickable': False, 
            # 'content_description': None, 'editable': False, 'enabled': True, 'focusable': False, 'focused': False, 'is_password': False, 'long_clickable': False, 'package': '', 
            # 'parent': -1, 'resource_id': None, 'scrollable': False, 'selected': False, 'size': '1080*2400', 'temp_id': 0, 'text': None, 'visible': True, 'child_count': 3}, 

            # {'bounds': [[0, 0], [1080, 2400]], 'checkable': False, 'checked': False, 'children': [2], 'class': 'android.widget.FrameLayout', 'clickable': False, 'content_description': '', 
            # 'editable': False, 'enabled': True, 'focusable': False, 'focused': False, 'is_password': False, 'long_clickable': False, 'package': 'com.google.android.apps.nexuslauncher', 
            # 'parent': 0, 'resource_id': '', 'scrollable': False, 'selected': False, 'size': '1080*2400', 'temp_id': 1, 'text': '', 'visible': True, 'child_count': 1}

            # ...
            # ]
            # 
        }

        self.state_history.append(state)
        return state
    
    def get_state_history(self) -> list[dict[Any, str]]:
        self.logger.info("getting the agent env state_history...")
        return self.state_history
    
    def post_action(self, action: str) -> bool: 
        # action example
        # action_type: type, touch_point: [-1.0, -1.0], lift_point: [-1.0, -1.0], typed_text: ”best rated coffee maker”
        """Takes a step in the environment."""
        operator_state = 0
        if not action.startswith('am') and not action.startswith('Oracle'):
            action_dict = parse_action_string(action)
            action_type, action_para = parse_action(action_dict)
            self.current_action = self._trans_action_format(action_type, action_para)
            # operator_state = self._execute_action(action_type, action_para)
        elif action.startswith('Oracle'):
            self.current_action = action
            action_type = "Oracle"
        else:
            self.current_action = action
            action_type = "INTENT"
            # operator_state = self.device.adb_shell(action)
        if not ( self.current_action.startswith("am force-stop") and self.current_steps == 0 ):   
            # save the action
            tag = self.current_steps
            action_dir_path = self._setup_directories(self.task_output_path, ['action'])[0]
            action_path = os.path.join(action_dir_path, f"{tag}.action")
            with open(action_path, "w") as action_file:
                action_file.write(self.current_action)# n.action
            
            self.logger.info("execute action: " + self.current_action)
            self.current_steps += 1
            self.logger.info(f"current steps: {self.current_steps},action type: {action_type}")

        if self.current_steps >= self.max_steps or action_type == "STATUS_TASK_COMPLETE" or action_type == "STATUS_TASK_IMPOSSIBLE":
            self.episode_end = True
            self.logger.info("episode end")
            # record installed packages after each episode
            self.ep_installed_apps = self.device.get_installed_apps()
            ep_installed_dir = self._setup_directories(self.task_output_path, ['installed_apps'])[0]
            self.ep_installed_fp = os.path.join(ep_installed_dir, "installed_apps.txt")

            if self.ep_installed_apps:
                with open(self.ep_installed_fp, 'w') as file:
                    for item in self.ep_installed_apps:
                        file.write(f"{item}\n") # installed_apps.txt
            else:
                with open(self.ep_installed_fp, 'w') as file:
                    file.write("")

        # time.sleep(1) # original 5, i guess used to wait executing; now disable executing, so no need to wait
        self.logger.info("action executed successfully")
        return operator_state
    
    def save_chat(self, conversation: str):
            tag = self.current_steps
            action_dir_path = self._setup_directories(self.task_output_path, ['chat'])[0]
            action_path = os.path.join(action_dir_path, f"{tag}.chat")
            with open(action_path, "w") as action_file:
                action_file.write(conversation)# n.chat

    def save_intructions(self, similar_ins: str, instructions: dict):
        sim_path = os.path.join(self.task_output_path, "instructions_sim.txt")
        ins_path = os.path.join(self.task_output_path, "instructions.json")        
         # Ensure the directory exists
        os.makedirs(os.path.dirname(ins_path), exist_ok=True)
        with open(sim_path,"w") as sim_file:
            sim_file.write(similar_ins)
        with open(ins_path,"w") as instruction_file:
            json.dump(instructions, instruction_file, indent=4)

    
    def get_device_size(self) -> tuple[int, int]:
        # return width, height
        width, height = self.device.get_screen_size()
        self.logger.info(f"getting device size {width}, {height}")
        return width, height

    def get_instruction(self) -> str:
        try:
            instruction, gr_path, app_short, episode, path = next(self.instruction_generator)

            self.task_output_path = path.replace("googleapps", "google_apps").replace("webshopping", "web_shopping")
            return instruction, gr_path, app_short, episode
        except StopIteration:
            self.logger.warning("All instructions have been fetched.")  
            return None
  
    def reset_env(self):
        
        self.logger.info("resetting agent env...")
        self.current_action = "None|None|None"
        self.state_history = []
        self.episode_end = False
        self.current_steps = 0
        self.device.disconnect()
        time.sleep(5)
        self.emulator_controller.reload_snapshot()
        time.sleep(30)
        self.device.connect()
        time.sleep(5)
        self.logger.info("agent env reset successfully!")

    def episode_done(self) -> bool:
        return self.episode_end
    
    def tear_down(self) -> None:
        self.device.disconnect()
        time.sleep(5)
        self.emulator_controller.exit_emulator()
        self.logger.info(f"tear down the agent env...")
    
    def setup_task(self, instruction: str) -> None:
        self.logger.info(f"setting up the task: {instruction}")

        TaskSetUp(self.device.u2d, instruction)
        



class AndroidController(AgentEnv): # AndroidController is a subclass of AgentEnv, and I think they should be integreted as one
    def __init__(self, avd_name, emulator_controller_args, local_output_path, max_steps=30,instruction_fp="../dataset/llamatouch_task_metadata.tsv"):
        super().__init__(
            avd_name=avd_name,
            emulator_controller_args=emulator_controller_args,
            local_output_path=local_output_path,
            max_steps=max_steps,
            instruction_fp=os.path.abspath(instruction_fp),
        )
        self.width, self.height = None, None


    def tap(self, tl, br):
        x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        w, h = self.get_device_size()
        x /= w
        y /= h
        action = f"action_type: dual_point, touch_point: [{x}, {y}], lift_point: [{x}, {y}], typed_text: ''"
        # AgentEnv interface post_action
        ret = self.post_action(action)
        return ret

    def text(self, input_str):
        # input_str = input_str.replace(" ", "%s") # Original AgentEnv
        # input_str = input_str.replace("'", "") # Original AgentEnv
        action = f"action_type: type, touch_point: [-1.0, -1.0], lift_point: [-1.0, -1.0], typed_text: '{input_str}'"
        # AgentEnv interface post_action       
        ret = self.post_action(action)
        return ret

    def long_press(self, tl, br, duration=1000):
        x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        w, h = self.get_device_size()
        x /= w
        y /= h
        action = f"action_type: dual_point, touch_point: [{x}, {y}], lift_point: [{x}, {y}], typed_text: ''"
        # AgentEnv interface post_action        
        ret = self.post_action(action)
        return ret

    def swipe(self, tl, br, direction, dist="short", quick=False):
        # AgentEnv interface get the device_size
        self.width, self.height = self.get_device_size()
        unit_dist = int(self.width / 10)
        if dist == "long":
            unit_dist *= 3
        elif dist == "medium":
            unit_dist *= 2
        x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        if direction == "up":
            offset = 0, -2 * unit_dist
        elif direction == "down":
            offset = 0, 2 * unit_dist
        elif direction == "left":
            offset = -1 * unit_dist, 0
        elif direction == "right":
            offset = unit_dist, 0
        else:
            return "ERROR"
        duration = 100 if quick else 400

        w, h = self.get_device_size()
        xbegin = x / w
        ybegin = y / w
        xend = (x + offset[0]) / w
        yend = (y + offset[1]) / h
        action = f"action_type: dual_point, touch_point: [{xbegin}, {ybegin}], lift_point: [{xend}, {yend}], typed_text: ''"
        ret = self.post_action(action)
        return ret

    def intent(self, intent_str:str):
        ret = self.post_action(intent_str)
        return ret