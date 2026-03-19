import os
import re


from ...constants import Game,FILE_TYPE,FOLDER_NAME
from ..wci_resources import WciResourceManager,DrawPack,Key,TexResource
from ...constants import WCI_PATTERN_NAME
from .ex_config import ExConfig


def add_cutting(ex_config:ExConfig,mod_manager:WciResourceManager):
    #检测裁剪贴图
    for file in ex_config.wci_cuttings:
        prePack=None
        sufPack=None
        #cutting_info=ex_config.wci_glows[file]
        file_path=os.path.join(mod_manager.buf_path,FOLDER_NAME.TEXTURE,file)
        if os.path.isfile(file_path) and mod_manager.game in [Game.ZZZ]:
            tex_file=file.replace("_cut.dds",".dds")
            #寻找去掉_glow这样文件名称的drawPack
            for ib_hash,ib_alias in mod_manager.drawPacks:
                for drawPack in mod_manager.drawPacks[(ib_hash,ib_alias)]:
                    for tex_res in drawPack.texs:
                        if tex_res.file==tex_file:
                            #判断hash是否存在，存在的话直接用Resource
                            cutting_tex=mod_manager.add_tex(file_path,tex_res.slot,tex_res.hash,tex_res.texname)
                            if prePack==None and sufPack==None:
                                prePack=DrawPack()
                                prePack.lv=drawPack.lv
                                prePack.draws.append("ps-t18 = "+cutting_tex.resource)
                                prePack.draws.append("Resource\\RabbitFX\\FXMap = ref"+cutting_tex.resource)
                                prePack.draws.append("run = CommandList\\RabbitFX\\Run")
                                sufPack=DrawPack()
                                sufPack.lv=drawPack.lv
                                sufPack.draws.append("ps-t18 = null")
                                sufPack.draws.append("Resource\\RabbitFX\\FXMap = null")
                                sufPack.draws.append("run = CommandList\\RabbitFX\\Run")
                            drawPack.subPacks.append(prePack)
                            drawPack.prePacks.append(sufPack)
            
    return mod_manager


def glow_init(ex_config:ExConfig,mod_manager:WciResourceManager):
    #发光替换的插件
    varList=[
        {
            "var":"speed",
            "defaultvalue":"4",
        },
        {
            "var":"glow_frame",
            "defaultvalue":"0",
        },
        {
            "var":"glow_fps",
            "defaultvalue":120,#默认60帧
        }
    ]
    for val in varList:
        mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_KEY,val)
    mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_GLOW_INIT,{})
    return mod_manager


def create_rabbitfx_drawPacks(toggle,h,s,v,brightness,glow_resource):
    prePack=DrawPack()
    sufPack=DrawPack()
    prePack.toggle=toggle
    prePack.draws.append(r"$\RabbitFX\H = "+str(h))
    prePack.draws.append(r"$\RabbitFX\S = "+str(s))
    prePack.draws.append(r"$\RabbitFX\V = "+str(v))
    prePack.draws.append(r"ps-u4 = ResourceEngineRGB")
    prePack.draws.append(r"$\RabbitFX\brightness = "+str(brightness))
    prePack.draws.append(r"ps-t17 = "+glow_resource)
    prePack.draws.append(r"Resource\RabbitFx\GlowMap = ref "+glow_resource)
    prePack.draws.append(r"run = CommandList\RabbitFX\Run")
    sufPack.toggle=toggle
    sufPack.draws.append(r"ps-t17 = null")
    sufPack.draws.append(r"Resource\RabbitFx\GlowMap = null")
    sufPack.draws.append(r"run = CommandList\RabbitFX\Run")
    return prePack,sufPack



def add_glow(ex_config:ExConfig,mod_manager:WciResourceManager):
    #检测发光贴图是否存在
    glow_flag=False
    for file in ex_config.wci_glows:
        prePack=None
        sufPack=None
        glow_info=ex_config.wci_glows[file]
        file_path=os.path.join(mod_manager.buf_path,FOLDER_NAME.TEXTURE,file)
        if os.path.isfile(file_path) and mod_manager.game in [Game.ZZZ]:
            time=glow_info["time"]
            H=glow_info["H"]
            S=glow_info["S"]
            V=glow_info["V"]
            B=glow_info["brightness"]
            keyboard=glow_info["keyboard"]
            key=Key(
                condition="$active == 1",
                defaultvalue=1,
                keyboard=keyboard,
            )
            key=mod_manager.merge_to_keys(key,[0,1])
            if time<1:
                #静态发光
                #初始化静态参数
                h,s,v,b=H[0],S[0],V[0],B[0]
            else:
                #动态发光
                #初始化动态参数
                #基础总共4秒，glow_frame -> 0-> 60-> 0
                if len(H)>1 and H[1]>H[0]:
                    val=format((H[1]-H[0])/60, ".2f")
                    h=f"{H[0]} + $glow_frame * {val}"
                else:
                    h=H[0]
                if len(S)>1 and S[1]>S[0]:
                    val=format((S[1]-S[0])/60, ".2f")
                    s=f"{S[0]} + $glow_frame * {val}"
                else:
                    s=S[0]
                if len(V)>1 and V[1]>V[0]:
                    val=format((V[1]-V[0])/60, ".2f")
                    v=f"{V[0]} + $glow_frame * {val}"
                else:
                    v=V[0]
                if len(B)>1 and B[1]>B[0]:
                    val=format((B[1]-B[0])/60, ".2f")
                    b=f"{B[0]} + $glow_frame * {val}"
                else:
                    b=B[0]
            var=key.get_var()
            #只要切换，不要名称
            item_name,toggle=mod_manager.parse_toggle("12345678-1.vb.glow",[(var,[1],key.is_or)])
            tex_file=file.replace("_glow.dds",".dds")
            #寻找去掉_glow这样文件名称的drawPack
            for ib_hash,ib_alias in mod_manager.drawPacks:
                for drawPack in mod_manager.drawPacks[(ib_hash,ib_alias)]:
                    for tex_res in drawPack.texs:
                        if tex_res.file==tex_file:
                            glow_flag=True
                            glow_tex=mod_manager.add_tex(file_path,tex_res.slot,tex_res.hash,tex_res.texname)
                            if prePack==None and sufPack==None:
                                prePack,sufPack=create_rabbitfx_drawPacks(toggle,h,s,v,b,glow_tex.resource)
                            drawPack.prePacks.append(prePack)
                            drawPack.sufPacks.append(sufPack)
    if glow_flag:
        return glow_init(ex_config,mod_manager)
    else:
        return mod_manager