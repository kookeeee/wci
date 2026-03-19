import re
import os
import hashlib
from typing import Dict,List,Any

from ..constants import SectionType,SectionSubType,TEX_STYLE
from ..game import game_dict




"""
    ini写入相关
"""


from typing import Dict
TexNameDict:Dict[str,Dict[str,str]]={
    TEX_STYLE.ZZMI:{
        "DiffuseMap":r"Resource\ZZMI\Diffuse",
        "NormalMap":r"Resource\ZZMI\NormalMap",
        "LightMap":r"Resource\ZZMI\LightMap",
        "MaterialMap":r"Resource\ZZMI\MaterialMap",
    },
    TEX_STYLE.RABBITFX:{
        "DiffuseMap":r"Resource\RabbitFX\Diffuse",
        "NormalMap":r"Resource\RabbitFX\NormalMap",
        "LightMap":r"Resource\RabbitFX\LightMap",
        "MaterialMap":r"Resource\RabbitFX\MaterialMap",
        "GlowMap":r"Resource\RabbitFX\GLowMap",
    }
}

class Patterns:
    
    """程序内定义，不做外部输出和转换，直接用dict定义"""
    wci_ini_template={
            "Head":[
                {
                    "type":SectionType.GlobalHead,
                    "subType":"",
                    "comment":"; {name}\n",
                },
                {
                    "type":SectionType.Constants,
                    "subType":"",
                    "comment":"; Constants -------------------------",
                    "merge":True,
                },
                {
                    "type":SectionType.Key,
                    "subType":"",
                    "comment":"; Key Swap --------------------------",
                },
                {
                    "type":SectionType.Present,
                    "subType":"",
                    "comment":"; Present ---------------------------",
                },
            ],
            "Body":[
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.skip,
                    "comment":"; Override -------------------------",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.IB,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.Position,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.Blend,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.Texcoord,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.VertexLimit,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.Map,
                    "comment":"",
                },
                {
                    "type":SectionType.Resource,
                    "subType":SectionSubType.Buffer,
                    "comment":"; Buffer ----------------------------",
                },
                {
                    "type":SectionType.Resource,
                    "subType":SectionSubType.File,
                    "comment":"; Resource ---------------------------",
                },
            ],
            "Foot":[
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.skip,
                    "comment":"; Override -------------------------",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.IB,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.Position,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.Blend,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.Texcoord,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.VertexLimit,
                    "comment":"",
                },
                {
                    "type":SectionType.TextureOverride,
                    "subType":SectionSubType.Map,
                    "comment":"",
                },
                {
                    "type":SectionType.Resource,
                    "subType":SectionSubType.Buffer,
                    "comment":"; Buffer ----------------------------",
                },
                {
                    "type":SectionType.Resource,
                    "subType":SectionSubType.File,
                    "comment":"; Resource ---------------------------",
                },
                {
                    "type":SectionType.CommandList,
                    "subType":"",
                    "comment":"; Command lists----------------------",
                },
                {
                    "type":SectionType.ShaderOverride,
                    "subType":"",
                    "comment":"; Shader override---------------------"
                },
                {
                    "type":SectionType.ShaderRegex,
                    "subType":"",
                    "comment":"; Shader Regex---------------------"
                },
                {
                    "type":SectionType.CustomShader,
                    "subType":"",
                    "comment":"; Custom shaders---------------------"
                },
                {
                    "type":SectionType.GlobalFoot,
                    "subType":"",
                    "comment":"""; .ini generated by wci.""",
                },      
            ], 
        }
    
    group:Dict[str,Any] = game_dict.pattern_dict


#规范化keyboard
def normalizied_keyboard(key):
    suf_val=""
    a=b=c=0
    key=key.lower().strip().replace("vk_","")
    if "no_alt " in key:
        key=key.replace("no_alt ","")
        a=0
    if "no_ctrl" in key:
        key=key.replace("no_ctrl ","")
        b=0
    if "no_shift" in key:
        key=key.replace("no_shift","")
        c=0
    if "alt" in key:
        key=key.replace("alt ","")
        a=1
    if "ctrl" in key:
        key=key.replace("ctrl ","")
        b=1
    if "shift" in key:
        key=key.replace("shift ","")
        c=1
    if a+b+c==0:
        suf_val+="NO_MODIFIERS "
    else:
        if a==0:
            suf_val+="NO_ALT "
        else:
            suf_val+="ALT "
        if b==0:
            suf_val+="NO_CTRL "
        else:
            suf_val+="CTRL "
        if c==0:
            suf_val+="NO_SHIFT "
        else:
            suf_val+="SHIFT "
    if "left" in key:
        key=key.replace("left","VK_LEFT")
    if "right" in key:
        key=key.replace("right","VK_RIGHT")
    if "up" in key:
        key=key.replace("up","VK_UP")
    if "down" in key:
        key=key.replace("down","VK_DOWN")
    key=suf_val+key.strip()
    return key
