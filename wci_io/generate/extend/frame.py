import os
import re
import json
import time
import datetime
import shutil
import subprocess

from .ex_config import ExConfig
from ..wci_resources import WciResourceManager,Key

from ..utils import normalizied_keyboard
from ...constants import WCI_PATTERN_NAME


def add_frame(ex_config:ExConfig,mod_manager:WciResourceManager):
    #配置文件帧变量
    frames=set({})
    if len(mod_manager.frames)<=0:
        print("skip motion frame!")
        return mod_manager
    #配置文件帧按键
    if "keyboard" in ex_config.wci_frames and len(ex_config.wci_frames["keyboard"])>0:
        nk=normalizied_keyboard(ex_config.wci_frames["keyboard"])
    if nk not in mod_manager.keys:
        key=Key(
            condition="$active == 1",
            defaultvalue=0,
        )
        key.set_keyboard(nk)
        key=mod_manager.add_key(key,[0,1])
    else:
        key=mod_manager.keys[nk]
    key_var=key.get_var()
    #给每一个drawPack新增帧切换按键
    update_start_draws=[]
    for frame_item_name in mod_manager.frames:
        #需要计算最小帧和最大帧
        frame=int(frame_item_name.split("frame=")[1])
        #没有帧动画时的模型
        start_obj_name=frame_item_name.split("_frame=")[0]
        if start_obj_name not in update_start_draws:
            index,start_drawPack = mod_manager.get_drawpack_by_obj_name(start_obj_name)
            if start_drawPack.toggle:
                start_drawPack.toggle = f"({start_drawPack.toggle}) && {key_var} == 0"
            else:
                start_drawPack.toggle = f"{key_var} == 0"
            update_start_draws.append(start_obj_name)

        frames.add(frame)
        index,drawPack = mod_manager.get_drawpack_by_obj_name(frame_item_name)
        if drawPack.toggle:
            drawPack.toggle= f"({drawPack.toggle}) && {key_var} == 1 && $frame == {frame}"
        else:
            drawPack.toggle= f"{key_var} == 1 && $frame == {frame}"

    frames=list(frames)
    frames.sort()
    # 获取最大帧和最小帧
    min_frame=frames[0]
    max_frame=frames[-1]
    #帧率默认30帧
    fps=30
    varList=[
        {
            "var":"frame",
            "defaultvalue":"0",
        },
        {
            "var":"fps",
            "defaultvalue":30,
        },
        {
            "var":"speed",
            "defaultvalue":1.0,
        },
        {
            "var":"min_frame",
            "defaultvalue":min_frame,
        },
        {
            "var":"max_frame",
            "defaultvalue":max_frame,
        }
    ]
    for val in varList:
        mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_KEY,val)

    mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_FRAME_INIT,{})
    return mod_manager
