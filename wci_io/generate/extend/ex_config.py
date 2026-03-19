import re
import os
import json
import shutil
import uuid
import hashlib
import inspect

from typing import Dict, List, Any
from dataclasses import dataclass

from ..utils import normalizied_keyboard


def __gen_hash__():
    return str(uuid.uuid4()).replace("-", "")


@dataclass
class Lod:
    
    hash:str = None
    
    vg:Dict[str,str] = None
    
    skip:bool = False

    cb:list[str] = None
    

class ExConfig:

    wci_config_name: str = "config"
    wci_config_name_comment: str = "mod配置文件名称"

    wci_helps: Dict[str, Any] = {
        "creditinfo": "wci example creditinfo",
        "keyboard": "=",
        "panel": {
            "rectangle": [0.3, -1, 1, 1],
            "forecolor": "#E6FFFFFF",    # 白
            "background": "#4D1A1A2E",   # 粉紫色调
            "border": [0.02, 0.02],
            "anchor": ["left", "center"],
            "text align": "left",
            "font scale": 1.0,
        },
    }
    wci_helps_comment: str = "creditinfo:切换时屏幕左下角显示作者信息,keyboard指定帮助按键"

    wci_mod_links: Dict[str, str] = {"author": "", "link": ""}
    wci_mod_links_comment: str = "readme.txt的作者链接，键值对类型"

    # 帧动画
    wci_frames: Dict[str, str] = {"keyboard": "ctrl /"}
    wci_frame_flag_comment: str = "帧动画写入"

    # active_slot,动态插槽切换判断
    wci_active_slot_flag: bool = False
    wci_active_slot_flag_comment: str = "动态插槽"

    wci_shader_fixes_draw: bool = True
    wci_shader_fixes_draw_comment: str = "是否调用shaderFixes文件的draw,默认调用"

    wci_namespace_uuid: str = ""  # 初始为空，__init__ 中会动态生成
    wci_namespace_uuid_comment: str = "命名空间uuid，合并不同的配置文件"

    wci_custom_replace: List[Dict[str, str]] = []
    wci_custom_replace_comment: str = "自定义正则匹配替换规则"

    wci_cross_ibs: List[Dict[str, Any]] = [
        {
            "src": "12345678-1.vb.body",
            "des": "87654321-1.vb.body2",
            "cb": ["cb1", "cb2"],
            "type": "const",
            "skip":True,
        }
    ]
    wci_cross_ibs_comment: str = "跨ib配置,类型有const(常量),和bmsr(骨骼变换矩阵重定向)两种"

    wci_glows: Dict[str, Any] = {
        "file": {"H": (100, 0), "S": (0, 0), "V": (0, 0), "brightness": (0, 100), "time": 0, "keyboard": "0"}
    }
    wci_glows_comment: str = "发光配置,参数来自RabbitFx,time是一次循环的时间，单位：秒 (s)"

    wci_cuttings: Dict[str, Any] = {"file": {}}
    wci_cuttings_comment: str = "裁剪配置，参数来自RabbitFx"

    wci_lods: Dict[str, Any] = {}
    wci_lods_comment: str = "ib对应的lods ib信息"

    # 需要设置为透明的部件
    wci_transparency: Dict[str, Dict[str, float]] = {"12345678-1.vb": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 0.1}}
    wci_transparency_comment: str = "透明配置"

    @staticmethod
    def parse_key_value(key, value):
        # 将key = 1,2,3 解析成 key==1 || key==2 || key ==3的格式
        swap = []
        keyValue = ""
        sub_str = ""
        for s in value + "#":
            if s in [",", "#"]:
                if str(sub_str).isdigit():
                    keyValue += f"{key} == {sub_str}"
                    swap.append(int(sub_str))
                if s in [","]:
                    keyValue += " || "
                sub_str = ""
            else:
                sub_str += s
        return swap, keyValue

    @staticmethod
    def parse_keyboard_toggle_str(toggle_str):
        # 分析a=1,2,3|b=1,2,3_body
        # 分析a_3_body
        toggle_str = toggle_str.strip()
        split_names = toggle_str.split("_")
        keyInfos = []
        if len(split_names) == 1:
            return "", []
        elif len(split_names) == 2:
            subvlaue = ""
            subkeyvalue = ""
            keyInfos = []
            for i in range(0, len(split_names[0])):
                ch = split_names[0][i]
                if i == len(split_names[0]) - 1:
                    subvlaue += ch
                    ch = ""
                if ch in ["&", "|", ""]:
                    keyboard, value = subvlaue.split("=")
                    keyboard = normalizied_keyboard(keyboard)
                    swap, v = ExConfig.parse_key_value(keyboard, value.strip())
                    keyInfos.append((keyboard, swap))
                    if "||" in v:
                        v = f"( {v} )"
                    if ch != "":
                        subkeyvalue += f" {v} "
                        subkeyvalue += f" {ch}{ch} "
                    else:
                        subkeyvalue += f" {v} "
                    subvlaue = ""
                else:
                    subvlaue += ch
            return subkeyvalue, keyInfos
        elif len(split_names) == 3:
            keyboard = normalizied_keyboard(split_names[0])
            swap, v = ExConfig.parse_key_value(keyboard, split_names[1])
            keyInfos.append((keyboard, swap))
            return v, keyInfos
        else:
            raise Exception("切换名称异常! " + toggle_str)

    @staticmethod
    def get_buf_dicts(buf_path, draw=True):
        __buf_dict = {}
        if os.path.isdir(buf_path):
            for dir in os.listdir(buf_path):
                if draw:
                    drawJson = os.path.join(buf_path, dir, "analysis_export.json")
                else:
                    drawJson = os.path.join(buf_path, dir, "analysis.json")
                if os.path.isfile(drawJson):
                    with open(drawJson, "r", encoding="utf-8") as f:
                        data= json.loads(f.read())
                        __buf_dict[data["ib"]["hash"]] = data
        return __buf_dict

    @staticmethod
    def get_static_attributes(cls):
        """
        获取类的所有静态属性（类变量），不包括从基类继承的属性或特殊方法。
        """
        static_attrs = {
            key: value
            for key, value in vars(cls).items()
            if not key.startswith("__") and not callable(value)
        }
        return static_attrs

    def __init__(self, game, buf_path, mod_path):
        # 程序路径
        script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
        script_dir = os.path.dirname(script_path)
        self.resources = os.path.join(script_dir, "resources")

        self.game = game
        self.buf_path = buf_path
        self.mod_path = mod_path
        self.comment = ""

        # 将类级别的 wci_ 默认值复制到实例
        for key, value in self.get_static_attributes(self.__class__).items():
            if key.startswith("wci_"):
                setattr(self, key, value)

        # 如果 wci_namespace_uuid 为空（刚复制默认值为空），则生成一个新值
        if not self.wci_namespace_uuid:
            self.wci_namespace_uuid = "wci_" + __gen_hash__()

        self.__init_wci_folder__()
        self.__init_wci_json__()
        self.__load_extend_config__()

    def __load_extend_config__(self):
        if os.path.isdir(self.buf_path):
            for file in os.listdir(self.buf_path):
                file_path = os.path.join(self.buf_path, file)
                if "comment.txt" == file:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.comment = f.read()

    def update_wci_json(self):
        """将当前实例的 wci_ 配置写入 wci.json"""
        config_path = os.path.join(self.buf_path, "wci.json")
        config = {}
        # 收集所有以 wci_ 开头的实例属性
        for name in dir(self):
            if name.startswith("wci_"):
                config[name] = getattr(self, name)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(config, indent=4, ensure_ascii=False))

    def __init_wci_json__(self):
        config_path = os.path.join(self.buf_path, "wci.json")
        if os.path.isfile(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                for key in config:
                    if key.startswith("wci_"):
                        setattr(self, key, config[key])
                        # 命名空间的uuid为空需要重新生成
                        if key == "wci_namespace_uuid" and config[key].strip() == "":
                            new_uuid = "wci_" + __gen_hash__()
                            setattr(self, key, new_uuid)
                            config[key] = new_uuid

            # 补全缺失的键（用类默认值，但这里直接保留现有值，避免覆盖已手动修改的实例）
            # 但为了保持配置文件完整，可以选择将实例中存在的所有 wci_ 写回去
            # 这里简单重新写一遍全部属性即可，也可以保持原有逻辑：确保所有类默认键都存在
            all_wci_keys = [k for k in dir(self) if k.startswith("wci_")]
            for key in all_wci_keys:
                if key not in config:
                    config[key] = getattr(self, key)

            # 排序后写回
            sorted_keys = sorted(config.keys())
            new_config = {k: config[k] for k in sorted_keys}
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(new_config, indent=4, ensure_ascii=False))
        else:
            # 生成 wci.json 文件，用实例的当前值（即类默认值）
            config = {}
            for name in dir(self):
                if name.startswith("wci_"):
                    config[name] = getattr(self, name)
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(config, indent=4, ensure_ascii=False))

    def __init_wci_folder__(self):
        # 模版文件写入
        template_dir = os.path.join(self.resources, "template")
        if os.path.isdir(template_dir):
            for file in os.listdir(template_dir):
                des_file_path = os.path.join(self.buf_path, file)
                if not os.path.isfile(des_file_path):
                    shutil.copyfile(os.path.join(template_dir, file), des_file_path)


if __name__ == "__main__":
    pass