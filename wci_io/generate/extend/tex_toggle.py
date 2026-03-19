
import os
import re


from typing import List,Dict
from collections import defaultdict

from .ex_config import ExConfig

from ..wci_resources import WciResourceManager,DrawPack,Key,TexResource

from ...utils import get_file_hash
from ...constants import Game,FILE_TYPE,SectionSubType,WCI_PATTERN_NAME


toggle_texture_file_pattren=re.compile(r"Texture_(.+)")

def __add_tex_toggle_to_drawPack_(drawPack:DrawPack,texs:List[TexResource],toggle):
    subPack=DrawPack()
    subPack.lv=drawPack
    subPack.toggle=toggle
    for tex in texs:
        subPack.texs.append(tex)
    drawPack.subPacks.append(subPack)
    return drawPack

def add_tex_toggle(ex_config:ExConfig,mod_manager:WciResourceManager):
    #遍历drawPack,的所有tex_res,如果有一样文件名称的就增加切换
    #生成资源文件对应的drwaPack
    tex_drawpacks_dict:defaultdict[str,List[DrawPack]]=defaultdict(list)
    drawname_toggle_file_dict:defaultdict[str,List[List[str]]]=defaultdict(list)
    file_path_keyInfo_dict={}
    for ib_hash,ib_alias in mod_manager.drawPacks:
        for drawPack in mod_manager.drawPacks[(ib_hash,ib_alias)]:
            for tex_res in drawPack.texs:
                tex_drawpacks_dict[tex_res.file].append(drawPack)
    
    dirs= os.listdir(mod_manager.buf_path)
    dirs.sort()
    for dir in dirs:
        match=toggle_texture_file_pattren.match(dir)
        if match:
            toggle_str=match.group(1)
            toggle,keyInfos=ex_config.parse_keyboard_toggle_str(toggle_str)
            for file in os.listdir(os.path.join(mod_manager.buf_path,dir)):
                file_path = os.path.join(mod_manager.buf_path,dir,file)
                file_path_keyInfo_dict[file_path]=(toggle,keyInfos)
                if file in tex_drawpacks_dict:
                    # 同名文件存在
                    file_hash = get_file_hash(file_path)
                    if file_hash not in mod_manager.tex_hash_dict:
                        #没有加入资源
                        drawPacks=tex_drawpacks_dict[file]
                        for drawPack in drawPacks:
                            if drawPack.name in drawname_toggle_file_dict:
                                drawname_toggle_file_dict[drawPack.name].append([file_path,file])
                            else:
                                drawname_toggle_file_dict[drawPack.name]=[[file_path,file]]                       
                    else:
                        #已加入过资源需要判断resource是否一致
                        tex=mod_manager.tex_hash_dict[file_hash]
                        for drawPack in tex_drawpacks_dict[file]:
                            for d_tex in drawPack.texs:
                                if d_tex.file == file and d_tex.resource!=tex.resource:
                                    # 文件名称一致，但是resource不一致，加切换
                                    if drawPack.name in drawname_toggle_file_dict:
                                        drawname_toggle_file_dict[drawPack.name].append([file_path,file])
                                    else:
                                        drawname_toggle_file_dict[drawPack.name]=[[file_path,file]]
                                    break
    #遍历了所有的切换
    for drawname in drawname_toggle_file_dict.keys():
        index,drawPack = mod_manager.get_drawpack_by_obj_name(drawname)
        toggle_texs={}
        for file_path,file in drawname_toggle_file_dict[drawname]:
            ib_hash=file[0:8]
            toggle,keyInfos=file_path_keyInfo_dict[file_path]
            for nk,swap in keyInfos:
                key=Key()
                key.set_keyboard(nk)
                key.condition= "$active == 1"
                new_key=mod_manager.add_key(key,swap)
                var=new_key.get_var()
                #将按键替换为变量
                toggle=toggle.replace(nk,var)
            for tex_res in drawPack.texs:
                if tex_res.file == file:
                    toggle_tex=mod_manager.add_tex(ib_hash,file_path,tex_res.slot,tex_res.hash,tex_res.texname)
                    if toggle in toggle_texs:
                        toggle_texs[toggle].append(toggle_tex)
                    else:
                        toggle_texs[toggle]=[toggle_tex]
        for t in toggle_texs:
            texs=toggle_texs[t]
            drawPack=__add_tex_toggle_to_drawPack_(drawPack,texs,t)
        mod_manager.update_drawPack(drawPack)
    
    #hash的切换。
    # this = Resource_ 遍历section,然后添加切换
    section_names=list(mod_manager.sections.keys())
    for section_name in section_names:
        section=mod_manager.sections[section_name]
        if section.subSectionType == SectionSubType.Map:
            #切换对应的tex
            toggle_dict={}
            resource_name=re.findall(".*?this *= *(Resource.*?)\n.*?",section.data,re.S)[0].strip()
            resource_section=mod_manager.sections[f"[{resource_name}]"]
            filename = re.match(".*?filename *= *Texture/(.*?\.(?:dds|ib|buf|txt|png|jpg|bmp|tga)).*?",resource_section.data,re.S).group(1)
            for file_path in file_path_keyInfo_dict:
                file=os.path.split(file_path)[1]
                if filename==file:
                    toggle,keyInfos=file_path_keyInfo_dict[file_path]
                    for nk,swap in keyInfos:
                        key=Key()
                        key.set_keyboard(nk)
                        key.condition= "$active == 1"
                        new_key=mod_manager.add_key(key,swap)
                        var=new_key.get_var()
                        #将按键替换为变量
                        toggle=toggle.replace(nk,var)
                        toggle_dict[toggle]=mod_manager.add_tex(file_path,None,None,None)
            switch_str=""
            for toggle in toggle_dict:
                switch_str+="if "+toggle+"\n"
                switch_str+="    this = "+toggle_dict[toggle].resource+"\nendif\n"
            section.data+=switch_str
    return mod_manager


