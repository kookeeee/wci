import os
import re
import json
import shutil
import struct
from copy import deepcopy
from typing import List,Tuple,Dict

from .ex_config import ExConfig
from ..wci_resources import WciResourceManager,Section,DrawPack

from ...constants import WCI_PATTERN_NAME
from ...constants import SectionType,Game,FOLDER_NAME
from ...utils import format_size


hash_pattern=re.compile(".*?hash = ([a-z0-9A-Z]+)\n.*?")
#lods配对 
# 默认lod和原IB的数据结构一致，不一致需要重新生成对应数据，有点麻烦
# 只考虑ib子网格的数量不一致情况


def update_blend_buf(match_vgs,blend_buf_file_path,fmt):
    #读取blend文件，检索匹配顶点组，修改二进制文件顶点组编号
    with open(blend_buf_file_path,"rb") as f:
        buffer = bytearray(f.read())

    stride=fmt["stride"]
    vertex_count = len(buffer)//stride
    blendindices_offset=0
    blendindces_fmt=""

    for element in fmt["elements"]:
        if element["SemanticName"] in ["BLENDINDICES","BLENDINDICE"]:
            blendindices_offset=element["AlignedByteOffset"]
            blendindces_fmt=element["Format"]
    fmt_char,elem_size,var_size=format_size(blendindces_fmt)
    for i in range(0,vertex_count):
        start = i * stride + blendindices_offset
        end = start + elem_size
        byte_values=buffer[start:end]
        value = struct.unpack(fmt_char, byte_values)
        new_value = tuple([match_vgs[str(v)] for v in value])
        if new_value!=value:
            new_byte_values=struct.pack(fmt_char, *new_value)
            buffer[start:end]=new_byte_values
    with open(blend_buf_file_path,"wb") as f:
        f.write(buffer)
            


def add_lods(ex_config:ExConfig,mod_manager:WciResourceManager):
    hash_dict={}
    ib_alias_dict={}
    blend_resource_names={}
    if len(ex_config.wci_lods.keys())>0:
        main_buf_dicts=ex_config.get_buf_dicts(mod_manager.buf_path,draw=False)
        lod_buf_dicts=ex_config.get_buf_dicts(os.path.join(mod_manager.buf_path,"LoDs"),draw=False)
        for ib_hash in ex_config.wci_lods.keys():
            lod_ib_hash=ex_config.wci_lods[ib_hash]["hash"]
            if ib_hash in main_buf_dicts and lod_ib_hash in lod_buf_dicts:
                hash_dict[ib_hash]=lod_ib_hash
                main_analysis_json=main_buf_dicts[ib_hash]
                lod_analysis_json=lod_buf_dicts[lod_ib_hash]
                #配对buf的hash
                bufs=list(main_analysis_json.keys())
                bufs.remove("ib")
                match_vgs=ex_config.wci_lods[ib_hash]["vg"]
                for buf in bufs:
                    if buf in lod_analysis_json:
                        main_fmt_infos = main_analysis_json[buf]["fmts"]
                        lod_fmt_infos = lod_analysis_json[buf]["fmts"]
                        # TODO 增加贴图hash
                        for i in range(0,len(main_fmt_infos)):
                            if "hash" in main_fmt_infos[i] and i<len(lod_fmt_infos) and "hash" in lod_fmt_infos[i]:
                                if "BLENDINDICES" in main_fmt_infos[i]["metadata"]["semantics"] or ["BLENDINDICE"] in main_fmt_infos[i]["metadata"]["semantics"]:
                                    blend_fmt=main_fmt_infos[i]
                                hash_dict[main_fmt_infos[i]["hash"]]=lod_fmt_infos[i]["hash"]
                                if "draw" in main_fmt_infos[i] and "draw" in lod_fmt_infos[i]:
                                    hash_dict[main_fmt_infos[i]["draw"]]=lod_fmt_infos[i]["draw"]
                #这里通过match_key匹配，后续通过match_key取值
                main_match_keys:List[str]=[]
                lod_match_keys:List[str]=[]
                match_keys_dict:Dict[str,str]={}
                for key in main_analysis_json["ib"]["info"]:
                    main_match_keys.append(key)
                main_match_keys = sorted(main_match_keys, key=lambda x: int(x.split(" ")[0]))
                for key in lod_analysis_json["ib"]["info"]:
                    lod_match_keys.append(key)
                lod_match_keys = sorted(lod_match_keys, key=lambda x: int(x.split(" ")[0]))
                for i in range(0,len(main_match_keys)):
                    if i>=len(lod_match_keys):
                        hash_dict[(ib_hash,main_match_keys[i])]=(lod_ib_hash,lod_match_keys[-1])
                        ib_alias_dict[(ib_hash,main_match_keys[i])]=main_analysis_json["ib"]["info"][main_match_keys[i]]["alias"]
                    else:
                        hash_dict[(ib_hash,main_match_keys[i])]=(lod_ib_hash,lod_match_keys[i])    
                        ib_alias_dict[(ib_hash,main_match_keys[i])]=main_analysis_json["ib"]["info"][main_match_keys[i]]["alias"]
                #配对ib的hash同时记录需要合并的数据
                main_ib_first_idxs= []
                lod_ib_first_idxs = []
                for key in main_analysis_json["ib"]["info"]:
                    main_ib_first_idxs.append((ib_hash,key.split(" ")[0]))
                    ib_alias_dict[(ib_hash,key)]=main_analysis_json["ib"]["info"][key]["alias"]
                main_ib_first_idxs = sorted(main_ib_first_idxs, key=lambda x: int(x[1]))
                for key in lod_analysis_json["ib"]["info"]:
                    lod_ib_first_idxs.append((lod_ib_hash,key.split(" ")[0]))
                    ib_alias_dict[(lod_ib_hash,key)]=lod_analysis_json["ib"]["info"][key]["alias"]
                lod_ib_first_idxs = sorted(lod_ib_first_idxs, key=lambda x: int(x[1]))
                for i in range(0,len(main_ib_first_idxs)):
                    # lod匹配不同的match_first_index,只有两种情况，
                    # 多对一，一对一
                    if i>=len(lod_ib_first_idxs):
                        hash_dict[tuple(main_ib_first_idxs[i])]=tuple(lod_ib_first_idxs[-1])
                    else:
                        hash_dict[tuple(main_ib_first_idxs[i])]=tuple(lod_ib_first_idxs[i])
                #创建新的blend文件
                if mod_manager.game in [Game.AE] and blend_fmt:
                    blend_file_path=os.path.join(mod_manager.mod_path,FOLDER_NAME.BUFFER,blend_fmt["file"])
                    basedir,file = os.path.split(blend_file_path)
                    file_name,suf=os.path.splitext(file)
                    lod_blend_file_path = os.path.join(basedir,file_name+".loD"+suf)
                    if os.path.isfile(blend_file_path):
                        shutil.copyfile(blend_file_path,lod_blend_file_path)
                        if len(match_vgs)>0:
                            update_blend_buf(match_vgs,lod_blend_file_path,blend_fmt["metadata"])
                        name=file_name.replace("-","_")
                        section_name=f"[Resource_{name}]" 
                        if f"Resource_{name}" not in blend_resource_names:
                            blend_resource_names[f"Resource_{name}"]=f"Resource_{name}"+".loD"
                        new_section_name=section_name[0:-1]+".loD]"
                        section=mod_manager.sections[section_name]
                        section_info=section.to_dict()
                        section_info["data"]=section_info["data"].replace(file,file_name+".loD"+suf)
                        mod_manager.sections[new_section_name]=Section(new_section_name,section_info)
            else:
                print("LoDs ib配对缺失:",ib_hash,lod_ib_hash)
    section_names=list(mod_manager.sections.keys())

    bmsr_commandLists:List[str]=[]
    bmsr_comandlist_lod_dict:Dict[str,str]={}
    for section_name in section_names:
        if "_BMSR_" in section_name:
            bmsr_commandLists.append(section_name)    
    for section_name in section_names:
        section=mod_manager.sections[section_name]
        if section.sectionType == SectionType.TextureOverride:
            hashs=re.findall(".*?hash = ([a-zA-Z0-9]{8})\n.*?",section.data,re.S)
            match_first_indexs = re.findall(".*?match_first_index = (\d+)\n.*?",section.data,re.S)
            match_index_counts = re.findall(".*?match_index_count = (\d+)\n.*?",section.data,re.S)
            match_first_index = None
            match_index_count = None
            if len(hashs)>0:
                hash=hashs[0]
            else:
                continue
            if len(match_first_indexs)>0:
                match_first_index = match_first_indexs[0]
            if len(match_index_counts)>0:
                match_index_count = match_index_counts[0]
            if match_first_index and match_index_count:
                match_key = match_first_index+" "+match_index_count
                if (hash,match_key) in hash_dict:
                    ib_alias=mod_manager.ib_alias_dict[hash]
                    sub_alias=ib_alias_dict[(hash,match_key)]
                    
                    lod_ib_hash,lod_match_key = hash_dict[(hash,match_key)]
                    lod_sub_alias=ib_alias_dict[(lod_ib_hash,lod_match_key)]
                    lod_match_first_index,lod_match_index_count = lod_match_key.split(" ")
                    new_section_name=section_name[0:-1]+".loD]"
                    section_info=section.to_dict()
                    section_info["data"]=section_info["data"].replace(f"hash = {hash}",f"hash = {lod_ib_hash}")
                    section_info["data"]=section_info["data"].replace(f"match_first_index = {match_first_index}",f"match_first_index = {lod_match_first_index}")
                    section_info["data"]=section_info["data"].replace(f"match_index_count = {match_index_count}",f"match_index_count = {lod_match_index_count}")
                    if mod_manager.game in [Game.AE]:
                        for resource_name in blend_resource_names:
                            if resource_name in section_info["data"]:
                                new_resource_name = blend_resource_names[resource_name]
                                section_info["data"]=section_info["data"].replace(resource_name,new_resource_name)
                        
                        #还需要对使用BMSR的跨ib数据进行修改
                        for bmsr_commandlist in bmsr_commandLists:
                            if "CommandList_"+ib_alias in bmsr_commandlist:
                                bmsr_commandlist_section=mod_manager.sections[bmsr_commandlist]
                                id=mod_manager.get_number_id(lod_ib_hash,"bmsr_id")
                                mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CONSTANTS_KEY,{"var":f"_{lod_ib_hash}_id","defaultvalue":id})
                                new_bmsr_commandlist=bmsr_commandlist[1:-1]+".loD"
                                bmsr_section_info=bmsr_commandlist_section.to_dict()
                                bmsr_section_info["data"]=bmsr_section_info["data"].replace(f"_{ib_alias}_id",f"_{lod_ib_hash}_id")
                                mod_manager.sections[f"[{new_bmsr_commandlist}]"]=Section(f"[{new_bmsr_commandlist}]",bmsr_section_info)
                                section_info["data"]=section_info["data"].replace(bmsr_commandlist,new_bmsr_commandlist)
                                bmsr_comandlist_lod_dict[bmsr_commandlist[1:-1]]=new_bmsr_commandlist
                                
                    mod_manager.sections[new_section_name]=Section(new_section_name,section_info)
                    # 复制drawPack
                    drawPacks=mod_manager.get_drawpacks_by_ib(hash,sub_alias)
                    pre_drawpack=DrawPack()
                    pre_drawpack.draws=[f"ib = Resource_{ib_alias}_Component{sub_alias}"]
                    for drawPack in drawPacks:
                        new_drawPack=deepcopy(drawPack)
                        new_drawPack.name=new_drawPack.name+".loD"
                        new_drawPack.lod=new_section_name
                        if mod_manager.game in [Game.AE]:
                            for i in range(0,len(new_drawPack.draws)):
                                for bmsr_commandlist in bmsr_comandlist_lod_dict:
                                    bmsr_commandlist_lod=bmsr_comandlist_lod_dict[bmsr_commandlist]
                                    if bmsr_commandlist in new_drawPack.draws[i] and ".loD" not in new_drawPack.draws[i]:
                                        new_drawPack.draws[i]=new_drawPack.draws[i].replace(bmsr_commandlist,bmsr_commandlist_lod)
                            for pack in new_drawPack.prePacks+new_drawPack.sufPacks:
                                for i in range(0,len(pack.draws)):
                                    for blend_resource_name in blend_resource_names:
                                        new_resource_name = blend_resource_names[blend_resource_name]
                                        if blend_resource_name in pack.draws[i] and ".loD" not in pack.draws[i]:
                                            pack.draws[i]=pack.draws[i].replace(blend_resource_name,new_resource_name)
                        if lod_sub_alias>sub_alias:
                            new_drawPack.prePacks.insert(0,pre_drawpack)
                        mod_manager.add_drawPacks(lod_ib_hash,lod_sub_alias,[new_drawPack])

            else:
                if hash in hash_dict:
                    lod_hash=hash_dict[hash]
                    new_section_name=section_name[0:-1]+".loD]"
                    section_info=section.to_dict()
                    section_info["data"]=section_info["data"].replace(f"hash = {hash}",f"hash = {lod_hash}")
                    mod_manager.sections[new_section_name]=Section(new_section_name,section_info)
    return mod_manager



if __name__=="__main__":
    pass