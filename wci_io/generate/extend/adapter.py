import datetime
import os
import re
from typing import Dict,List,Tuple


from .help import add_help
from .frame import add_frame
from .glow import add_glow,add_cutting
from .lods import add_lods
from .tex_toggle import add_tex_toggle
from .transparency import add_transpancy
from .shapekey import add_shapekey
from .bone_redirect import add_bone_redirect
from .ex_config import ExConfig
from ..wci_resources import WciResourceManager,DrawPack,IniUtil
from ...constants import Game,CROSS_TYPE,FOLDER_NAME,WCI_PATTERN_NAME
from ...utils import parse_obj_name



#TODO 帧动画
#TODO 插槽检测
# 跨IB
def add_cross_ib(ex_config:ExConfig,mod_manager:WciResourceManager):
    for cross_info in ex_config.wci_cross_ibs:
        if "type" not in cross_info or cross_info["type"]!=CROSS_TYPE.CONST:
            continue
        if "skip" in cross_info and cross_info["skip"] == True:
            continue
        src_obj_name=cross_info["src"]
        des_obj_name=cross_info["des"]
        cbs=cross_info["cb"]
        cross_type=cross_info["type"]

        src_ib_hash,src_sub_alias,src_item_name = parse_obj_name(src_obj_name)
        if src_ib_hash not in mod_manager.ib_alias_dict:
            continue
        src_ib_alias=mod_manager.ib_alias_dict[src_ib_hash]
        des_ib_hash,des_sub_alias,item_name = parse_obj_name(des_obj_name)
        des_ib_alias=mod_manager.ib_alias_dict[des_ib_hash]
        index,drawPack=mod_manager.get_drawpack_by_obj_name(src_obj_name)
        if drawPack:
            if mod_manager.game in [Game.ZZZ]:
                prePack=DrawPack()
                prePack.lv=drawPack.lv
                sufPack=DrawPack()
                sufPack.lv=drawPack.lv
                #复制VB0
                mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CROSS_IB,
                                              {"ib_hash":src_ib_hash,
                                               "ib_alias":src_ib_alias,
                                               "sub_alias":src_sub_alias}
                                               )
                mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CROSS_IB,
                                              {"ib_hash":des_ib_hash,
                                               "ib_alias":des_ib_alias,
                                               "sub_alias":des_sub_alias}
                                               )

                #写ib,vb0,vb1,vb2的替换
                pre_draws=[f"ib = Resource_{src_ib_alias}_Component{src_sub_alias}",
                       f"vb0 = Resource_{src_ib_alias}_VB0",
                       f"vb1 = Resource_{src_ib_alias}_Texcoord",
                       ]
                #恢复
                suf_draws=[f"ib = Resource_{des_ib_alias}_Component{des_sub_alias}",
                        f"vb0 = Resource_{des_ib_alias}_VB0",
                        f"vb1 = Resource_{des_ib_alias}_Texcoord",
                        ]
                #写常量
                for cb in cbs:
                    mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CROSS_CONST,{"src_ib_alias":src_ib_alias,"des_ib_alias":des_ib_alias,"name":cb})
                    pre_draws.append(f"Resource_{des_ib_alias}_{cb} = ref vs-{cb} unless_null")
                    pre_draws.append(f"vs-{cb} = Resource_{src_ib_alias}_{cb}")
                    suf_draws.append(f"vs-{cb} = Resource_{des_ib_alias}_{cb}")

                prePack.draws=pre_draws
                sufPack.draws=suf_draws
                drawPack.prePacks.append(prePack)
                drawPack.sufPacks.append(sufPack)
                #将drawPack移动到目标ib
                mod_manager.append_drawPack(des_ib_hash,des_sub_alias,drawPack)
                mod_manager.remove_drawPack(drawPack)
    return mod_manager



# 自定义正则匹配替换
def add_custom_replace(ex_config:ExConfig,mod_manager:WciResourceManager):
    #校验格式,替换
    mod_manager.sectiongs=IniUtil.re_replace(mod_manager.sections,ex_config.wci_custom_replace,{})
    return mod_manager


# shader_fix
def add_shader_fix(ex_config:ExConfig,mod_manager:WciResourceManager):
    shader_fixes_path=os.path.join(mod_manager.buf_path,FOLDER_NAME.SHADER_FIXES)
    files=os.listdir(shader_fixes_path)
    if ex_config.wci_shader_fixes_draw==True:
        draw_type=""
    else:
        draw_type=";"
    varList=[
        {
            "var":"shadervar",
            "defaultvalue":"0",
            "pre_value":"0",
        }
    ]
    if len(files)>0:
        mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_PRESENT_POST,varList[0])
        mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_KEY,varList[0])
        for file in files:
            file_path=os.path.join(shader_fixes_path,file)
            re_datas=re.findall("^([a-z0-9]{16})-([vp]s)_replace.txt$",file)
            if len(re_datas)>0:
                dataDict={
                    "hash":re_datas[0][0],
                    "shader_type":re_datas[0][1],
                    "draw_type":draw_type,
                    "filename":file,
                }
                mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_SHADER_FIX,dataDict)
                with open(os.path.join(mod_manager.mod_path,FOLDER_NAME.RES,file),"w",encoding="utf-8") as fw:
                    with open(file_path,"r",encoding="utf-8") as fr:
                        fw.write(fr.read())
    return mod_manager


def ex_adapter(mod_manager:WciResourceManager):

    #初始化
    ex_config=ExConfig(mod_manager.game,mod_manager.buf_path,mod_manager.mod_path)
    mod_manager.comment=ex_config.comment
    mod_manager.config_name=ex_config.wci_config_name
    mod_manager.links = ex_config.wci_mod_links

    #添加基本配置
    mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_PRESENT_INIT,{})
    
    mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_INIT,{})

    # 帧切换
    mod_manager = add_frame(ex_config,mod_manager)

    # 半透明
    mod_manager = add_transpancy(ex_config,mod_manager)

    # 发光
    mod_manager=add_glow(ex_config,mod_manager)
    
    # 不透明剔除
    mod_manager = add_cutting(ex_config,mod_manager)

    # 贴图切换
    mod_manager = add_tex_toggle(ex_config,mod_manager)

    # 跨ib在贴图切换之后
    mod_manager = add_cross_ib(ex_config,mod_manager)
    

    # 骨骼变换矩阵重定向
    mod_manager = add_bone_redirect(ex_config,mod_manager)

    # 形态键
    mod_manager = add_shapekey(ex_config,mod_manager)

    # 写入着色器修复文件
    mod_manager = add_shader_fix(ex_config,mod_manager)
    
    # 写help.txt
    mod_manager = add_help(ex_config,mod_manager)

    # 自定义正则替换    
    mod_manager = add_custom_replace(ex_config,mod_manager)

    # lods
    mod_manager = add_lods(ex_config,mod_manager)
    
    return mod_manager
    