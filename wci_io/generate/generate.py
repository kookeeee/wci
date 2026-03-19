import os
import shutil
import json
import bpy
import time
import math

from pathlib import Path
from typing import Dict, Tuple, Any, List
from copy import deepcopy

from .utils import Patterns, normalizied_keyboard
from .wci_resources import IniUtil, Section, Key, ShapeKeyResource,TexResource, DrawPack, WciResourceManager, get_tex

from ..constants import *
from ..utils import parse_obj_name


class ModGenerater:
    """
    模组生成器主类，负责根据解析的缓冲区数据生成3DMigoto可用的Mod。
    主要功能包括：
    - 复制文件到Mod目录
    - 合并INI配置
    - 生成Draw调用和纹理切换
    - 处理按键绑定
    """

    def __init__(self, operator, game, buf_path, tex_style=TEX_STYLE.SLOT):
        """
        初始化模组生成器。

        Args:
            operator: Blender操作符实例，用于报告信息。
            game: 游戏标识（Game枚举）。
            buf_path: 缓冲区数据根目录。
            mod_path: 输出Mod的目标目录。
            tex_style: 纹理样式（TEX_STYLE枚举）。
        """
        self.operator = operator
        self.game = game
        self.buf_path = buf_path
        self.mod_path = os.path.join(buf_path, FOLDER_NAME.MOD)
        self.tex_style = tex_style
        self.mod_manager = WciResourceManager(game, buf_path, self.mod_path)

    def __copy_mod2migoto__(self):
        """
        将生成的Mod复制到3DMigoto的Mods目录下。
        目标路径：<migoto_path>/Mods/wci，若已存在则先删除。
        """
        migoto_path = bpy.path.abspath(bpy.context.scene.wci_props.migoto_path)
        if os.path.isdir(migoto_path):
            game_mod_path = os.path.join(migoto_path, "Mods", FOLDER_NAME.OUTPUT)
            if os.path.isdir(game_mod_path):
                shutil.rmtree(game_mod_path)
            shutil.copytree(self.mod_path, game_mod_path)
            path1:Path = Path(self.mod_path).resolve()
            path2:Path = Path(migoto_path).resolve()
            if str(path2) in str(path1):
                #给mod目录下的ini配置文件改名
                for file in os.listdir(self.mod_path):
                    if file.endswith(".ini"):
                        new_ini_path = os.path.join(self.mod_path, "DISABLED_" + file)
                        os.rename(os.path.join(self.mod_path, file), new_ini_path)
    def __generate_draw__(self, objs:bpy.types.Object, ib_hash, ib_alias,dds_info_dict):
        """
        根据导出的对象信息生成DrawPack并添加到mod_manager中。

        Args:
            ib_hash: IB的哈希值。
            ib_alias: IB的别名。
            sub_alias: 子IB别名。
            objs: 导出的对象
            slot_sort: 排序后的槽位列表。
            default_dds_info: 默认贴图信息（来自analysis.json中的slot）。
        """
        for obj in objs:
            ib_hash, sub_alias, item_name = parse_obj_name(obj.name)
            for export_item in obj.wci_exports.items:
                if export_item.export_type == EXPORT_TYPE.SHAPEKEY_MESH:
                    #形态键后续处理
                    shapekey=ShapeKeyResource(
                        name=export_item.name,
                        start_index = export_item.start_index,
                        start_vertex = export_item.start_vertex,
                        vertex_count= export_item.vertex_count,
                        base_start_vertex = export_item.base_start_vertex,
                    )
                    self.mod_manager.shapekeys.append(shapekey)
                    continue
                if export_item.export_type == EXPORT_TYPE.FRAME_MESH:
                    self.mod_manager.frames.append(export_item.name)
                    #帧切换后面的逻辑不变
                index, tmp_darw = self.mod_manager.get_drawpack_by_obj_name(export_item.name)
                if tmp_darw is None:
                    indexCount = export_item.index_count
                    startIndexLocation = export_item.start_index
                    swaps = []

                    if obj and hasattr(obj, "wci_key_bindings"):
                        # 处理按键绑定：将Blender中的按键信息转换为Key对象
                        for item in obj.wci_key_bindings.items:
                            swap = [int(i) for i in item.swap.replace("，", ",").rstrip(",").split(",")]
                            key = Key(
                                condition="$active == 1",
                                defaultvalue=item.defaultvalue,
                                keyboard=item.keyboard,
                                is_alt=item.is_alt,
                                is_ctrl=item.is_ctrl,
                                is_shift=item.is_shift,
                                is_or=item.is_or
                            )
                            key = self.mod_manager.add_key(key, swap)
                            var = key.get_var()
                            swaps.append((var, swap, item.is_or))
                    draw = DrawPack()
                    draw.lv = 0
                    keyvalue = self.mod_manager.parse_toggle(export_item.name, swaps)
                    draw.name = export_item.name
                    if len(keyvalue) > 0:
                        draw.toggle = keyvalue
                    t=time.time()
                    # 获取纹理信息
                    tex_info = get_tex(
                        self.buf_path, ib_hash, ib_alias, sub_alias,
                        item_name, dds_info_dict[sub_alias]
                    )
                    for res in tex_info:
                        #没有贴图就跳过
                        if not os.path.isfile(res.file_path):
                            continue
                        tex_res = self.mod_manager.add_tex(ib_hash,res.file_path, res.slot, res.hash, res.texname)
                        if self.tex_style == TEX_STYLE.HASH:
                            if tex_res.write:
                                self.mod_manager.merge_to_sections(
                                    WCI_PATTERN_NAME.ADD_TEXOVERRIDE_HASH,
                                    {"hash": tex_res.hash, "resource": tex_res.resource, "texname": tex_res.texname}
                                )
                        else:
                            tex_res.tex_style = self.tex_style
                            draw.texs.append(tex_res)
                    if self.game in [Game.AE]:
                        draw.draws = [f"drawindexedinstanced = {indexCount*3}, INSTANCE_COUNT, {startIndexLocation*3}, 0, FIRST_INSTANCE"]
                    else:
                        draw.draws = [f"drawindexed = {indexCount*3}, {startIndexLocation*3}, 0"]

                    # 按(ib_hash, sub_alias) 分组存储DrawPack
                    key = (ib_hash, sub_alias)
                    if key in self.mod_manager.drawPacks:
                        self.mod_manager.drawPacks[key].append(draw)
                    else:
                        self.mod_manager.drawPacks[key] = [draw]
    def __generate_mod__(self, ib_hash:str, objs:bpy.types.Object):
        """
        根据单个IB的分析数据生成对应的INI片段和文件复制。

        Args:
            ib: IB标识符。
            data: 整个analysis_export.json的数据字典。
        """
        with open(os.path.join(self.buf_path,ib_hash,"analysis_export.json"),"r",encoding="utf-8") as f:
            data=json.loads(f.read())
        if "real_ib" in data["ib"]:
            data["ib"]["hash"]=data["ib"]["real_ib"]
        data_dict = {
            "ib_hash":data["ib"]["hash"],
            "ib_alias":data["ib"]["alias"],
            "suf": data["ib"]["suf"],
            "vertex_count": data["ib"]["vertex_count"],
        }
        self.mod_manager.ib_alias_dict[ib_hash]=data["ib"]["alias"]
        #存储贴图信息
        dds_info_dict={}
        index_count = 0
        
        self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_IB_SKIP, data_dict)
        # 遍历每个子IB（match）
        for match in data["ib"]["info"]:
            indices = data["ib"]["info"][match]["indices"]
            for index in indices.keys():
                file = data["ib"]["info"][match]["indices"][index]
                if "vs=" in file:
                    vs=file.split("vs=")[1][0:16]
                    self.mod_manager.ib_vs_dict[ib_hash][index]=vs
            sub_meta = data["ib"]["info"][match]
            index_count += sub_meta["metadata"]["index_count"]
            data_dict["sub_alias"] = sub_meta["alias"]
            data_dict["match_first_index"] = sub_meta["metadata"]["first_index"]
            data_dict["match_index_count"] = sub_meta["metadata"]["index_count"]
            if "byte_offset" in sub_meta["metadata"]:
                data_dict["match_byte_offset"] = sub_meta["metadata"]["byte_offset"]
            else:
                data_dict["match_byte_offset"] = 0
            data_dict["format"] = sub_meta["metadata"]["format"]
            data_dict["file"] = sub_meta["file"].replace(ib_hash,self.mod_manager.ib_alias_dict[ib_hash])

            self.mod_manager.copy_file(
                ib_hash,
                os.path.join(self.buf_path, FOLDER_NAME.BUFFER, sub_meta["file"]),
                FILE_TYPE.BUF
            )

            # 处理槽位检查
            slot_info = sub_meta["slot"]
            slot_keys = list(slot_info.keys())
            slot_keys.sort()
            slot_keys.reverse()
            for slot in slot_keys:
                #逆序
                self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CHECK_TEX, {"slot": slot})
            #存储插槽信息
            dds_info_dict[sub_meta["alias"]]=slot_info
            # 写入基础IB配置
            self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_IB, data_dict)
        # 生成Drawindexed
        self.__generate_draw__(
            objs,
            data["ib"]["hash"],
            data["ib"]["alias"],
            dds_info_dict,
        )
        # 处理其他缓冲区（除ib外的所有键）
        bufs = list(data.keys())
        bufs.remove("ib")

        position_buf_info:Dict[str,str] = None

        blend_buf_info:Dict[str,str] = None
        
        texcoord_buf_info:Dict[str,str] = None
        for buf in bufs:
            for buf_info in data[buf]["fmts"]:
                if "file" not in buf_info:
                    continue
                suf = buf_info["suf"]
                buf_name = suf.replace("-", "").split(".")[0]
                data_dict["hash"] = buf_info["hash"]
                data_dict["buf"] = buf
                data_dict["buf_name"] = buf_name
                data_dict["stride"] = buf_info["metadata"]["stride"]
                data_dict["file"] = buf_info["file"].replace(ib_hash,self.mod_manager.ib_alias_dict[ib_hash])

                self.mod_manager.copy_file(
                    ib_hash,
                    os.path.join(self.buf_path, FOLDER_NAME.BUFFER, buf_info["file"]),
                    FILE_TYPE.BUF
                )
                self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_BUF, data_dict)

                if "draw" in data[buf]:
                    draw_hash = buf_info["draw"]
                    stride = buf_info["metadata"]["stride"]
                    vertex_count = data["ib"]["vertex_count"]
                    self.mod_manager.merge_to_sections(
                        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_DRAW,
                        {"hash": draw_hash, 
                         "stride": stride, 
                         "vertex_count": vertex_count,
                         "ib_hash":ib_hash,
                         "ib_alias":self.mod_manager.ib_alias_dict[ib_hash],}
                    )

                # 分类记录不同类型的缓冲区信息
                if "POSITION" in str(buf_info["metadata"]["semantics"]):
                    buf_info["buf_name"] = buf_name
                    buf_info["buf"] = buf
                    position_buf_info = buf_info
                elif "BLENDINDICE" in str(buf_info["metadata"]["semantics"]):
                    buf_info["buf_name"] = buf_name
                    buf_info["buf"] = buf
                    blend_buf_info = buf_info
                elif "TEXCOORD" in str(buf_info["metadata"]["semantics"]):
                    buf_info["buf_name"] = buf_name
                    buf_info["buf"] = buf
                    texcoord_buf_info = buf_info
        # 处理混合缓冲区（如果存在且与位置缓冲区分离）
        if blend_buf_info is None:
            pass
        elif blend_buf_info == position_buf_info:
            # 已合并，无需额外处理
            pass
        else:
            #以position hash为主hash
            data_dict["hash"] = position_buf_info["hash"]
            
            data_dict["position_hash"] = position_buf_info["hash"]
            data_dict["position_buf"] = position_buf_info["buf"]
            data_dict["position_buf_name"] = position_buf_info["buf_name"]
            data_dict["position_stride"] = position_buf_info["metadata"]["stride"]
            data_dict["position_file"] = position_buf_info["file"]
            
            data_dict["blend_hash"] = blend_buf_info["hash"]
            data_dict["blend_buf"] = blend_buf_info["buf"]
            data_dict["blend_buf_name"] = blend_buf_info["buf_name"]
            data_dict["blend_stride"] = blend_buf_info["metadata"]["stride"]
            data_dict["blend_file"] = blend_buf_info["file"]
            
            data_dict["dispatch"] = int(math.ceil(data["ib"]["vertex_count"] / 64)) + 1
            
            if texcoord_buf_info:
                data_dict["texcoord_hash"] = texcoord_buf_info["hash"]
                data_dict["texcoord_buf"] = texcoord_buf_info["buf"]
                data_dict["texcoord_buf_name"] = texcoord_buf_info["buf_name"]
                data_dict["texcoord_stride"] = texcoord_buf_info["metadata"]["stride"]
                data_dict["texcoord_file"] = texcoord_buf_info["file"]
            self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_BLEND, data_dict)
        # 针对特定游戏添加VS检查
        if self.game in [Game.BOY, Game.NARAKA]:
            vs_set=set()
            for ib_hash in self.mod_manager.ib_vs_dict:
                for index in self.mod_manager.ib_vs_dict[ib_hash]:
                   vs_set.add(self.mod_manager.ib_vs_dict[ib_hash][index]) 
            for vs in vs_set:
                self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_VS_CHECK, {"vs": vs})
        return index_count
    def __merge_draw__(self):
        """
        将所有已收集的DrawPack合并写入INI的draw部分。
        每个(ib_hash, sub_alias)对应一个draw组。
        """
        for key in self.mod_manager.drawPacks:
            ib_hash, sub_alias = key
            raw_data = ""
            for draw in self.mod_manager.drawPacks[key]:
                raw_data += draw.to_raw_data() + "\n"
            data_dict = {
                "raw_draw": raw_data
            }
            if draw.lod:
                data_dict["section"]=draw.lod
                self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_DRAWINDEXED_LOD, data_dict)
            else:
                data_dict["ib_alias"]=self.mod_manager.ib_alias_dict[ib_hash]
                data_dict["sub_alias"]=sub_alias
                self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_DRAWINDEXED, data_dict)

    def __merge_pre_keys__(self, keys: Dict[str, Key]):
        """
        预处理预定义的按键（来自wci.ini.pre），添加到mod_manager中。

        Args:
            keys: 键名为标准化键盘名称，键值为Key对象的字典。
        """
        for normalize_keyboard in keys:
            key = keys[normalize_keyboard]
            self.mod_manager.add_key(key, [])

    def __merge_pre_sections__(self, sections: Dict[str, Section]):
        """
        预处理预定义的INI节（来自wci.ini.pre），添加到mod_manager中。

        Args:
            sections: 节名称到Section对象的映射。
        """
        for section_name in sections:
            self.mod_manager.add_section(sections[section_name])

    def __merge_swapkey__(self):
        """
        将所有按键信息合并到INI的对应节中。
        """
        if len(self.mod_manager.keys.keys()) > 0:
            self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_PRESENT_INIT, {})
            self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_INIT, {})

        for keyboard in self.mod_manager.keys:
            key:Key = self.mod_manager.keys[keyboard]
            var = key.get_var()
            if var:
                data_dict = {
                    "var": var.replace("$", ""),
                    "defaultvalue": key.defaultvalue
                }
                self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_PERSIST_KEY, data_dict)

            if not key.section:
                key.section = "[Key" + var.replace("$", "") + "]"

            self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_RAW, 
                {
                    "raw_data": key.to_raw_data(),
                    "section": key.section,
                },                            
                )

    def create_mod(self, ib_objs:Dict[str,List[bpy.types.Object]]):
        """
        主入口方法：根据指定的IB列表（或所有IB）生成完整的Mod。

        Args:
            ib_objs: 所有导出的按ib存储的object对象
        """
        # 读取预配置文件 wci.ini.pre
        pre_config_path = os.path.join(self.buf_path, "wci.ini.pre")
        if os.path.isfile(pre_config_path):
            with open(pre_config_path, "r", encoding="utf-8") as f:
                config_data = f.read()
        else:
            config_data = ""

        sections, keys = IniUtil.parse_ini(config_data)
        self.__merge_pre_keys__(keys)
        self.mod_manager.active_info["active"] = []
        # 逐个生成每个IB的配置
        index_count = 0
        for ib in ib_objs:
            self.mod_manager.active_info["active"].append(ib)
            index_count += self.__generate_mod__(ib, ib_objs[ib])
        # 针对efmi做mod加载
        if self.game in [Game.AE]:
            self.mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_XXMI_MOD_LOAD,{"index_count":index_count})

        # 合并预定义的节
        self.__merge_pre_sections__(sections)
    
        # 设置激活标志
        for acitve_var in self.mod_manager.active_info:
            for ib_hash in self.mod_manager.active_info[acitve_var]:
                self.mod_manager.merge_to_sections(
                    WCI_PATTERN_NAME.ADD_ACTIVE_FLAG,
                    {"ib_hash": ib_hash, 
                     "ib_alias":self.mod_manager.ib_alias_dict[ib_hash],
                     "var": acitve_var}
                     )

        # 尝试加载扩展适配器（如果启用）
        if bpy.context.scene.wci_props.extension:
            try:
                from .extend.adapter import ex_adapter
                self.mod_manager = ex_adapter(self.mod_manager)
            except Exception:
                import traceback
                traceback.print_exc()
                print("WCI扩展插件生成失败！已跳过")
        # 合并Draw调用
        self.__merge_draw__()

        # 合并按键信息
        self.__merge_swapkey__()

        # 生成最终的INI文件
        sections, config_data = IniUtil.merge_ini(
            self.mod_manager.ib_alias_dict,
            self.mod_manager.sections,
            self.mod_manager.config_name,
            links=self.mod_manager.links)
        
        ini_path = os.path.join(self.mod_path, self.mod_manager.config_name + ".ini")
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(self.mod_manager.comment+"\n")
            if self.mod_manager.namespace:
                f.write("namespace = "+self.mod_manager.namespace+"\n")
            f.write(config_data)
        self.operator.report({"INFO"}, "create: " + ini_path.replace("\\", "/"))
        self.__copy_mod2migoto__()
