import re
import os
import shutil
import json
from collections import defaultdict
from typing import Tuple, List, Dict, Any, Union

from .utils import conv_tex,get_image_size
from .data import FileCollector
from ..constants import FOLDER_NAME


def get_draw_dict(buf_dict: dict) -> dict:
    """
    从缓冲区配置中提取绘制相关的插槽映射。

    Args:
        buf_dict: 缓冲区配置字典。

    Returns:
        字典，键为draw名称，值为对应的缓冲区名称。
    """
    draw_dict:defaultdict[str,List[str]] = defaultdict(list)
    for buf in buf_dict:
        if buf == "ib":
            continue
        elif "draw" in buf_dict[buf]:
            draw_dict[buf_dict[buf]["draw"]].append(buf)
    return draw_dict

def get_hit_slot_info(slots: List[Dict[str, str]], tex_info: Dict[str, Tuple[Any,]], min_image_size:int = 2) -> Union[Dict[str, str],int]:
    """
    从候选slot列表中找出最匹配的slot
    """
    if not slots or not tex_info:
        return {},0
    
    target_slots = set()
    for slot in tex_info:
        file,width,height,slot_hash = tex_info[slot]
        if file[-4:] == ".jpg" and (width < (min_image_size // 2) or height < (min_image_size // 2)):
            continue
        elif file[-4:] == ".dds" and (width < min_image_size or height < min_image_size):
            continue
        target_slots.add(slot)
    
    best_score = 0.0
    best_slot = {}

    # 插槽数量，匹配插槽数量=匹配贴图数量，贴图数量 总共4个只。
    # 插槽数量越多，匹配插槽数量越多就行，插槽数量和匹配插槽数量一致 权重是1
    # 匹配贴图数量越多，比如
    for slot_info in slots:
        slot_keys = set(slot_info.keys())
        matched = slot_keys & target_slots
        matched_count = len(matched)
        slot_count = len(slot_keys)

        if matched_count == 0:
            continue
        match_ratio = matched_count / len(slot_keys)
        coverage_ratio = matched_count / len(target_slots)
        extra_slots = len(slot_keys - target_slots)
        extra_penalty = extra_slots / len(slot_keys) if slot_keys else 0
        score = match_ratio * 0.4 + coverage_ratio * 0.5 - extra_penalty * 0.1
        if matched_count == len(target_slots) and len(slot_keys) == len(target_slots):
            score += 0.1
        
        

        if score > best_score:
            best_score = score
            best_slot = dict(slot_info)

    if best_score <= 0:
        return {},0
    return best_slot,best_score


def search_hit_slot_info_by_indices(indices:List[str],
                                     slots:List[Dict[str,str]],
                                     tex_info:Dict[str,Dict[str,Tuple[Any,]]],
                                     min_image_size:int)->Union[str,Dict[str,str]]:    
    hit_index:str = None
    hit_slot_info:Dict[str,str] = {}
    weights = 0
    for index in indices:
        slot_info = tex_info[index]
        #命中的槽位
        now_hit_slots,now_weights = get_hit_slot_info(slots,slot_info,min_image_size)
        #找插槽最多的数据
        if len(now_hit_slots.keys()) > len(hit_slot_info.keys()):
            hit_slot_info = now_hit_slots
            hit_index = index
            weights = now_weights
        elif len(now_hit_slots.keys()) == len(hit_slot_info.keys()):
            if now_weights > weights:
                hit_slot_info = now_hit_slots
                hit_index = index
                weights = now_weights               
    return hit_index,hit_slot_info

def update_slot_info(buf_dict:Dict[str,Any],slots:List[Dict[str,str]],slot_info:Dict[str,Tuple[Any,]],match_key:str,file_path:str,extract_path:str):
    sub_alias = buf_dict["ib"]["info"][match_key]["alias"]
    for slot in slot_info:
        file,width,height,slot_hash = slot_info[slot]
        slot_file = os.path.join(file_path, file)
        if slot in slots.keys():
            buf_type = file[-4:]
            new_file = buf_dict["ib"]["hash"] + f"-" + sub_alias + "-" + slots[slot]["name"] + buf_type
            extract_slot_file = os.path.join(extract_path, new_file)
            shutil.copyfile(slot_file, extract_slot_file)
            if slots[slot]["name"] == "DiffuseMap":
                conv_tex(extract_path, new_file, conv_type="jpg")
            if slots[slot]["name"] == "NormalMap":
                if buf_type == ".jpg":
                    conv_tex(extract_path, new_file, conv_type="dds", dxgi_format="BC7_UNORM")
                    os.remove(os.path.join(extract_path, new_file))
                    new_file = new_file[0:-4] + ".dds"
            buf_dict["ib"]["info"][match_key]["slot"][slot] = {"hash": slot_hash, "file": new_file,"name":slots[slot]["name"],}
    return buf_dict

def analysis_slot(buf_dict: dict, fc: FileCollector, extract_path: str,
                  min_image_size: int = 1024) -> dict:
    """
    分析纹理槽位，从帧转储中匹配最合适的纹理文件。

    Args:
        buf_dict: 缓冲区配置字典。
        fc: 文件收集器实例。
        extract_path: 提取目录。
        min_image_size: 最小纹理尺寸（用于过滤）。

    Returns:
        更新后的buf_dict，包含每个子IB对应的槽位信息。
    """
    
    tex_path = os.path.join(extract_path, "TrianglelistTextures")
    # 最终存储到indices.json
    tex_info:defaultdict[str,defaultdict[str,Tuple[Any,]]] = defaultdict(defaultdict)
    os.makedirs(tex_path, exist_ok=True)
    slots = buf_dict["ib"]["slots"]
    # hash一致的看做一张贴图
    slot_hash_dict:Dict[str,str] = {}
    #绘制信息
    draw_dict = get_draw_dict(buf_dict)
    for key in buf_dict["ib"]["info"].keys():
        indices = list(buf_dict["ib"]["info"][key]["indices"].keys())
        #初始化贴图插槽信息
        buf_dict["ib"]["info"][key]["slot"] = {}
        for index in indices:
            for file in fc.caches[index]:
                slot = file.split("=")[0][7:]
                slot_type = file[-4:]
                slot_hash = file.split(slot+"=")[1][0:8]
                if slot in draw_dict:
                    for real_slot in draw_dict[slot]:
                        for fmt in buf_dict[real_slot]["fmts"]:
                            fmt["draw"] = slot_hash
                if slot_type in [".dds", ".jpg"] and ("ps-t" in slot or "ds-t" in slot):
                    if "!S!=" in file or "!US!=" in file:
                        slot_hash = re.findall(r"^\d{6}-"+slot+"=!(?:S|US)!=([a-z0-9]{8})", file)[0]
                    else:       
                        slot_hash = re.findall(r"^\d{6}-"+slot+"=([a-z0-9]{8})", file)[0]
                    width, height = get_image_size(os.path.join(fc.dumps_path, file))
                    # 过滤不符合尺寸要求的纹理
                    if width % 2 != 0 or height % 2 != 0 or width % height != 0:
                        #不是2的幂次方的或者长宽为0
                        continue
                    if slot_hash in fc.skip_tex_hashs:
                        #跳过重复次数非常多的贴图
                        continue
                    #存储贴图到 TrianglelistTextures,并去重
                    slot_file = os.path.join(fc.dumps_path, file)
                    if slot_hash not in slot_hash_dict:
                        tex_file = os.path.join(tex_path, file)
                        tex_info[index][slot] = (file,width,height,slot_hash)
                        shutil.copyfile(slot_file, tex_file)
                        slot_hash_dict[slot_hash] = (file,width,height,slot_hash)
                    else:
                        # 引用同一个hash的贴图
                        tex_info[index][slot] = slot_hash_dict[slot_hash]
        hit_index,hit_slot_info = search_hit_slot_info_by_indices(indices,slots,tex_info,min_image_size)
        if hit_index:
            buf_dict = update_slot_info(buf_dict,hit_slot_info,tex_info[hit_index],key,fc.dumps_path,extract_path)
        else:
            #以最小的贴图尺寸匹配
            hit_index,hit_slot_info = search_hit_slot_info_by_indices(indices,slots,tex_info,2)
            buf_dict = update_slot_info(buf_dict,hit_slot_info,tex_info[hit_index],key,fc.dumps_path,extract_path)
    with open(os.path.join(tex_path,"indices.json"),"w",encoding="utf-8") as f:
        f.write(json.dumps(tex_info,ensure_ascii=False,indent=4))
    return buf_dict


# 更新指定对象贴图
def update_custom_tex(buf_path:str,ib_hash:str,sub_alias:str):

    # 检查游戏配置文件
    user_game_buf_file = os.path.join(buf_path, ".wci")
    if os.path.isfile(user_game_buf_file):
        with open(user_game_buf_file, "r", encoding="utf-8") as f:
            buf_dict = json.loads(f.read())
    else:
        # 自定义替换贴图 只读取.wci文件
        return None,None
    ib_path = os.path.join(buf_path,ib_hash)
    if os.path.isdir(ib_path):
        analysis_json_path = os.path.join(ib_path,"analysis.json")
    else:
        ib_path = os.path.join(buf_path,FOLDER_NAME.LODS,ib_hash)
        if os.path.isdir(ib_path):
            analysis_json_path = os.path.join(ib_path,"analysis.json")
        else:
            return None,None
    tex_path =  os.path.join(ib_path,"TrianglelistTextures")
    if not os.path.isfile(os.path.join(tex_path,"indices.json")):
        return None,None
    with open(os.path.join(tex_path,"indices.json"),"r",encoding="utf-8") as f:
        tex_info = json.loads(f.read())

    indices=list(tex_info.keys())
    if len(tex_info.keys()) <= 0:
        return None,None
    # 清除已经删除的贴图信息
    for index in indices:
        ss = list(tex_info[index].keys())
        for s in ss:
            file = tex_info[index][s][0]
            if not os.path.isfile(os.path.join(tex_path,file)):
                del tex_info[index][s]
        if len(tex_info[index]) <= 0:
            del tex_info[index]
    with open(analysis_json_path,"r",encoding="utf-8") as f:
        analysis_json=json.loads(f.read())
    for key in analysis_json["ib"]["info"]:
        slot_info = analysis_json["ib"]["info"][key]["slot"]
        if sub_alias == analysis_json["ib"]["info"][key]["alias"]:
            #单个还是全量？
            match_key_indices = list(analysis_json["ib"]["info"][key]["indices"])
            indices = set(tex_info.keys()) & set(match_key_indices)
            #从全局slots中移除当前正在使用的slots
            from copy import deepcopy
            slots = deepcopy(buf_dict["ib"]["slots"])
            for i, d in enumerate(slots):
                #移除当前正在使用的插槽
                check= True
                for slot in slot_info:
                    if slot in d and d[slot]["name"] == slot_info[slot]["name"]:
                        check=False
                        break
                if not check:
                    del slots[i]
            # 重新查找
            hit_index,hit_slot_info=search_hit_slot_info_by_indices(indices,slots,tex_info,2)
            if hit_index != None:
                #清理原本的贴图信息
                for slot in analysis_json["ib"]["info"][key]["slot"]:
                    file_path  = os.path.join(ib_path,analysis_json["ib"]["info"][key]["slot"][slot]["file"])
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    if os.path.isfile(file_path[0:-4]+".jpg"):
                        os.remove(file_path[0:-4]+".jpg")
                del analysis_json["ib"]["info"][key]["slot"][slot]
                analysis_json["ib"]["info"][key]["slot"]={}
                analysis_json = update_slot_info(analysis_json,hit_slot_info,tex_info[hit_index],key,tex_path,ib_path)
                with open(analysis_json_path,"w",encoding="utf-8") as f:
                    f.write(json.dumps(analysis_json,ensure_ascii=False,indent=4))
                return hit_slot_info,analysis_json["ib"]["info"][key]["slot"]
    return None,None