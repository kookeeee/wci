#骨骼变换矩阵快照重定向,来自
#https://www.caimogu.cc/post/2323055.html
#Bone Matrix Snapshot Redirect
#通过每一帧的骨骼变换矩阵快照，达到任意模型渲染到任意位置的效果，最终实现跨材质渲染
import os
import re
import json
import time
import datetime
import shutil
import subprocess

from typing import List,Tuple,Dict
from collections import defaultdict
from dataclasses import dataclass
from copy import deepcopy

from .ex_config import ExConfig
from ..wci_resources import WciResourceManager,DrawPack
from ...constants import FOLDER_NAME
from ...utils import parse_obj_name
from ...constants import Game,SectionType,CROSS_TYPE,WCI_PATTERN_NAME


bone_snapshot_redirect_ini=f"""
;骨骼变换矩阵快照重定向
;技术来自https://www.caimogu.cc/post/2323055.html
[Constants]
global $redirect_id = -1


[Resource_Snapshot_CB1.RW]
type = RWStructuredBuffer
stride = 16
array = 4096

[Resource_Snapshot_CB1]
type = Buffer
stride = 16
array = 4096

[Resource_Redirected_Snapshot_CB1.RW]
type = RWStructuredBuffer
stride = 16
array = 4096

[Resource_Redirected_Snapshot_CB1]
type = Buffer
stride = 16
format = R32G32B32A32_UINT
array = 4096


[Resource_Redirected_Snapshot_T0.RW]
type = RWStructuredBuffer
stride = 16
array = 120000



[Resource_Redirected_Snapshot_T0]
type = StructuredBuffer
stride = 16
array = 120000


[CustomShader_Snapshot_CB1]
vs = {FOLDER_NAME.BUFFER}/snapshot_cb1_vs.hlsl
ps = {FOLDER_NAME.BUFFER}/snapshot_cb1_ps.hlsl
ps-u7 = Resource_Snapshot_CB1.RW
depth_enable = false
blend = ADD SRC_ALPHA INV_SRC_ALPHA
cull = none
topology = point_list
draw = 4096, 0
ps-u7 = null
Resource_Snapshot_CB1 = copy Resource_Snapshot_CB1.RW

[CustomShader_Redirect_Snapshot_T0]
cs = {FOLDER_NAME.BUFFER}/redirect_t0_cs.hlsl
x86 = $redirect_id
cs-t0 = vs-t0
cs-t1 = Resource_Snapshot_CB1
;可读写骨骼变换矩阵快照
cs-u1 = Resource_Redirected_Snapshot_T0.RW
dispatch = 12, 1, 1
cs-u1 = null
cs-t0 = null
cs-t1 = null
x86 = 0
Resource_Redirected_Snapshot_T0 = copy Resource_Redirected_Snapshot_T0.RW

[CustomShader_Redirect_Snapshot_CB1]
cs = {FOLDER_NAME.BUFFER}/redirect_cb1_cs.hlsl
cs-t0 = Resource_Snapshot_CB1
x86 = $redirect_id

;真正会重定向的数据
cs-u0 = Resource_Redirected_Snapshot_CB1.RW
dispatch = 4, 1, 1
;转换为只读CB1重定向快照
Resource_Redirected_Snapshot_CB1 = copy cs-u0
cs-u0 = null
cs-t0 = null


[CommandList_Snapshot_Bone_Matrix]
if $redirect_id > -1
    run = CustomShader_Snapshot_CB1
    run = CustomShader_Redirect_Snapshot_T0
    run = CustomShader_Redirect_Snapshot_CB1
    vs-t0 = Resource_Redirected_Snapshot_T0
    vs-cb1 = Resource_Redirected_Snapshot_CB1   
endif

[CommandList_Redirect_Bone_Matrix]
if $redirect_id > -1
    run = CustomShader_Redirect_Snapshot_CB1
    vs-t0 = Resource_Redirected_Snapshot_T0
    vs-cb1 = Resource_Redirected_Snapshot_CB1
endif
"""


def get_redirected_draw_raw_data(ib_alias,name,var,draw):
    #获取重定向draw
    return f"[CommandList_{ib_alias}_BMSR_Redirected_Draw{name}]",\
    f"""if ${var} == 0
    $redirect_id = $_{ib_alias}_id
    run = CommandList_Redirect_Bone_Matrix
    {draw}
    post vs-cb1 = null
    post vs-t0 = null
endif
    """

def get_snapshoted_draw_raw_data(ib_alias,name,var,draw):
    #获取快照draw
    return f"[CommandList_{ib_alias}_BMSR_Snapshoted_Draw{name}]",\
    f"""if ${var} == 1
    $redirect_id = $_{ib_alias}_id
    run = CommandList_Snapshot_Bone_Matrix
    {draw}
    ${var} = 0
    post vs-cb1 = null
    post vs-t0 = null
endif
    """

@dataclass
class CrossDrawInfo:
    drawPack:DrawPack = None
    src_ib_hash:str = None
    src_ib_alias:str = None
    src_sub_alias:str = None
    src_item_name:str = None
    des_ib_hash:str = None
    des_ib_alias:str = None
    des_sub_alias:str = "1"
    des_item_name:str = None

def add_bone_redirect(ex_config:ExConfig,mod_manager:WciResourceManager):
    # 有没有需要跨ib的数据
    bmsr_draw_dict:defaultdict[str,CrossDrawInfo]=defaultdict()
    ini_path=os.path.join(mod_manager.mod_path,"snapshot_redirect.ini")
    for cross_info in ex_config.wci_cross_ibs:   
        if (cross_info["type"]!=CROSS_TYPE.BMSR  and cross_info["type"]!=CROSS_TYPE.BMSR_ALL) or \
            cross_info["skip"] == True:
            continue
        print(cross_info)
        src_obj_name=cross_info["src"]
        des_obj_name=cross_info["des"]
        src_ib_hash,src_sub_alias,src_item_name = parse_obj_name(src_obj_name)
        index,drawPack=mod_manager.get_drawpack_by_obj_name(src_obj_name)
        if src_ib_hash in mod_manager.ib_alias_dict:
            src_ib_alias=mod_manager.ib_alias_dict[src_ib_hash]
        else:
            # 没有生成该数据，不用跨跳过
            continue
        des_ib_hash,des_sub_alias,des_item_name = parse_obj_name(des_obj_name)
        if des_ib_hash in mod_manager.ib_alias_dict:
            des_ib_alias = mod_manager.ib_alias_dict[des_ib_hash]
        else:
            # 没有生成该数据，不用跨跳过
            continue
            des_ib_alias = des_ib_hash
        if drawPack:
            bmsr_draw_dict[drawPack.name]=CrossDrawInfo(
                drawPack=drawPack,
                src_ib_hash = src_ib_hash,
                src_ib_alias=src_ib_alias,
                src_sub_alias= src_sub_alias,
                src_item_name = src_item_name,
                des_ib_hash=des_ib_hash,
                des_ib_alias=des_ib_alias,
                des_sub_alias=des_sub_alias,
                des_item_name=des_item_name,
            )
    if len(bmsr_draw_dict)>0:
        #给每一个ib分配id
        for ib_hash in mod_manager.ib_alias_dict:
            ib_alias = mod_manager.ib_alias_dict[ib_hash]
            id=mod_manager.get_number_id(ib_hash,type_key="bmsr_id")
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_KEY,{
                "var":f"_{ib_alias}_id",
                "defaultvalue":id,
            })
        bmsr_res=os.path.join(ex_config.resources,"bmsr")
        for file in os.listdir(bmsr_res):
            des_path=os.path.join(mod_manager.mod_path,FOLDER_NAME.BUFFER,file)
            if not os.path.isfile(des_path):
                shutil.copyfile(os.path.join(bmsr_res,file),des_path)
        mod_manager.namespace=ex_config.wci_namespace_uuid
        with open(ini_path,"w",encoding="utf-8") as f:
            f.write("namespace = "+mod_manager.namespace+"\n")
            f.write(bone_snapshot_redirect_ini)
        for name in bmsr_draw_dict:
            #生成CommandList
            cross_draw_info=bmsr_draw_dict[name]
            drawPack=cross_draw_info.drawPack
            ib_hash=cross_draw_info.src_ib_hash
            ib_alias=cross_draw_info.src_ib_alias
            #写vs 的filter
            index_vs=mod_manager.ib_vs_dict[ib_hash]
            indices=sorted(list(index_vs.keys()),key = lambda x:int(x))
            vs=index_vs[indices[0]]
            #加一个变量过滤条件
            var = f"shadow_vs_{vs}"
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_KEY,{
                "var":var,
                "defaultvalue":0,
            })
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_PRESENT_POST,{
                "var":var,
                "pre_value":0,
            })
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_VAR_FILTER,{
                "section_type":SectionType.ShaderOverride,
                "hash":vs,
                "var":var,
                "value":1,                
            })
            if cross_info["type"]==CROSS_TYPE.BMSR_ALL:
                mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_BMSR_FILTER,{
                    "ib_alias":ib_alias,
                    "sub_alias":src_sub_alias,
                    "var":var,

                })
            draw=""
            for line in cross_draw_info.drawPack.draws:
                draw+=line+"\n"
            if len(draw)>0:
                draw=draw[0:-1]
            name=mod_manager.get_number_id(drawPack.name,type_key="bmsr")
            r_section,r_raw_data=get_redirected_draw_raw_data(ib_alias,name,var,draw)
            n_section,n_raw_data=get_snapshoted_draw_raw_data(ib_alias,name,var,draw)
            #写入第一次绘制，存储重定向的骨骼变换矩阵快照
            drawPack.draws=["run = "+n_section[1:-1]]
            if cross_info["type"]==CROSS_TYPE.BMSR_ALL:
                drawPack.lv+=1
            mod_manager.update_drawPack(drawPack)
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_RAW,{
                "section":n_section,
                "raw_data":n_raw_data,
            })
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_RAW,{
                "section":r_section,
                "raw_data":r_raw_data,
            })
            #使用已经存储的骨骼变换矩阵快照跨ib绘制
            cross_drawPack = deepcopy(drawPack)
            if cross_info["type"]==CROSS_TYPE.BMSR_ALL:
                cross_drawPack.lv -= 1
            cross_drawPack.draws= ["run = "+r_section[1:-1]]
            prePack=DrawPack()
            prePack.lv=cross_drawPack.lv
            sufPack=DrawPack()
            sufPack.lv=cross_drawPack.lv
            if mod_manager.game in [Game.AE]:
                prePack.draws=[f"ib = Resource_{src_ib_alias}_Component{src_sub_alias}",
                       f"vb0 = Resource_{src_ib_alias}_Position",
                       f"vb1 = Resource_{src_ib_alias}_Texcoord",
                       f"vb2 = Resource_{src_ib_alias}_Blend",
                       f"vb3 = Resource_{src_ib_alias}_Position",
                       ]
                #恢复
                sufPack.draws=[f"ib = Resource_{des_ib_alias}_Component{des_sub_alias}",
                        f"vb0 = Resource_{des_ib_alias}_Position",
                        f"vb1 = Resource_{des_ib_alias}_Texcoord",
                        f"vb2 = Resource_{des_ib_alias}_Blend",
                        f"vb3 = Resource_{des_ib_alias}_Position",
                        ]
            elif mod_manager.game in [Game.ZZZ]:
                prePack.draws=[f"ib = Resource_{src_ib_alias}_Component{src_sub_alias}",
                       f"vb1 = Resource_{src_ib_alias}_Texcoord",
                       ]
                #恢复
                sufPack.draws=[f"ib = Resource_{des_ib_alias}_Component{des_sub_alias}",
                        f"vb1 = Resource_{des_ib_alias}_Texcoord",
                        ]                
            cross_drawPack.prePacks.append(prePack)
            cross_drawPack.sufPacks.append(sufPack)
            mod_manager.add_drawPacks(cross_draw_info.des_ib_hash,cross_draw_info.des_sub_alias,[cross_drawPack])
    return mod_manager