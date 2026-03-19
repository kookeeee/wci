import re
import os
import hashlib
import shutil
import threading
from typing import Dict, Tuple, List,Union
from collections import defaultdict
from dataclasses import dataclass
from copy import deepcopy

from ..utils import get_file_hash,parse_obj_name
from .utils import Patterns,normalizied_keyboard,TexNameDict
from ..constants import *


"""
    ini写入相关
"""  


class Section(dict):
    def __init__(self,section,section_info):
        #从拼接
        self.name:str=section
        self.sectionType:str=section_info["type"]
        self.subSectionType:str=section_info["subType"]
        self.data:str=section_info["data"]
        self.hash=None
        self.ib_hash=None
        self.file=None
        self.write=False
        #自己的hash,一些可能没有
        if "hash" in section_info:
            self.hash=section_info["hash"]
        if "ib" in section_info:
            self.ib_hash=section_info["ib"]
        if "file" in section_info:
            self.file=section_info["file"]
        if "write" in section_info:
            self.write=section_info["write"]
    
    @property
    def row_data(self):
        return self.name+"\n"+self.data+"\n"
    
    @property    
    def section(self):
        return self.name

    def to_dict(self):
        return {
            "hash":self.hash,
            "ib":self.ib_hash,
            "type":self.sectionType,
            "data":self.data,
            "subType":self.subSectionType,
            "write":self.write,
            "file":self.file
        }

    @staticmethod
    def parse_section_type(section:str,context:str)->Tuple[str,str]:
        typeInfo=SectionType.Undefined
        subTypeInfo=SectionSubType.SubUndefined
        if "Constants"==section[1:10]:
            typeInfo=SectionType.Constants
        elif "Present"==section[1:8]:
            typeInfo=SectionType.Present
        elif "Key"==section[1:4]:
            typeInfo=SectionType.Key
        elif "TextureOverride"==section[1:16]:
            typeInfo=SectionType.TextureOverride
            if "Blend" in section:
                subTypeInfo=SectionSubType.Blend
            elif "Position" in section:
                subTypeInfo=SectionSubType.Position
            elif "Texcoord" in section:
                subTypeInfo=SectionSubType.Texcoord
            elif "handling = skip" in context:
                subTypeInfo=SectionSubType.skip
            elif "VertexLimitRaise" in section:
                subTypeInfo=SectionSubType.VertexLimit
            elif "match_first_index" in context:
                subTypeInfo=SectionSubType.IB
            elif "this =" in context or "this=" in context:
                subTypeInfo=SectionSubType.Map

        elif "ShaderOverride"==section[1:15]:
            typeInfo=SectionType.ShaderOverride
        elif "ShaderRegex"==section[1:12]:
            typeInfo=SectionType.ShaderRegex
        elif "CommandList"==section[1:12]:
            typeInfo="CommandList"
        elif "CustomShader"==section[1:13]:
            typeInfo=SectionType.CustomShader
        elif "Resource"==section[1:9]:
            typeInfo=SectionType.Resource
            if "Buffer" in context:
                subTypeInfo=SectionSubType.Buffer
            else:
                subTypeInfo=SectionSubType.File
        elif "[Global_Head]"==section:
            typeInfo=SectionType.GlobalHead
        elif "[Global_Foot]"==section:
            typeInfo=SectionType.GlobalFoot
        else:
            print("未识别的数据结构",section)
        return typeInfo,subTypeInfo
    
    def __str__(self):
        return str(self.to_dict())



@dataclass
class DrawPack:
    
    def __init__(self):
        self.toggle:str=None
        self.lv:int=0
        self.lod:str=None
        self.prePacks:List[DrawPack]=[]
        self.sufPacks:List[DrawPack]=[]
        self.texs:List[TexResource]=[]
        self.subPacks:List[DrawPack]=[]
        self.draws:List[str]=[]
        self.name:str=None
    
    def __eq__(self, other):
        if not isinstance(other, DrawPack):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def to_raw_data(self):
        return raw_darw_pack(self.lv,self)
    


@dataclass
class Resource:
    name:str = None
    section:str = None
    format:str = None
    type:str = None
    stride:int = 0
    filename:str = None
    filepath:str = None

    def __hash__(self):
        return hash((self.name, self.section, self.type, self.format, self.stride, self.filename))

    def __eq__(self, other):
        if not isinstance(other, Resource):
            return False
        return (self.name == other.name and 
                self.section == other.section and 
                self.type == other.type and 
                self.format == other.format and 
                self.stride == other.stride and 
                self.filename == other.filename)
    @property
    def name(self)->str:
        return self.section[1:-1]
    
    @staticmethod
    def from_raw_data(section:str,raw_data:str):
        resource=Resource.__new__(Resource)
        resource.section=section
        resource.type = None
        resource.format = None
        resource.stride = 0
        resource.filename = None
        for line in raw_data.split("\n"):
            line=line.strip()
            if len(line)>0 and line[0]!=";" and "=" in line:
                key,value=line.split(";")[0].split("=")
                key=key.strip()
                value=value.strip()
                if key == "type":
                    resource.type=value
                elif key == "stride":
                    resource.stride=int(value)
                elif key == "filename":
                    resource.filename=value
                elif key == "format":
                    resource.format=value
        return resource


class TexResource:
    def __init__(self,file_path:str="",hash:str=None,slot:str=None,texname:str=None,resoure_name=None,type=None):
        self.file_path=file_path
        self.slot=slot
        self.hash=hash
        self.texname=texname
        self.resource=resoure_name
        self.write:bool=True
        self.tex_style:str = TEX_STYLE.SLOT
    @property
    def section(self):
        return f"[{self.resource}]"
    
    @property
    def file(self):
        if os.path.isfile(self.file_path):
            return os.path.split(self.file_path)[1]
        else:
            return None
    
    def to_raw_data(self):
        return f"[{self.resource}]\nfilename = {FOLDER_NAME.TEXTURE}/{self.file}\n"
    
class KeyType:
    TOGGLE="toggle"
    CYCLE="cycle"
    HOLD="hold"

class Key:
    """
    符合3dmigoto定义的key
    """
    condition_pattern=re.compile(r".*?condition=([a-z0-9A-Z\$_\==]+)")
    key_pattern = re.compile(r'^key\s*=\s*([A-Z_]+(?:\s+[A-Z_]+)*|\S+)$')
    type_pattern = re.compile(r"type=(toggle|cycle|hold)")
    var_pattern = re.compile(r"(\$[A-Za-z0-9_]+)=([0-9,]+)")
    command_pattern = re.compile(r"run=([A-Za-z0-9_]+)")

    def __init__(self,section:str=None,defaultvalue:int=0,condition:str=None,keyboard:str=None,is_ctrl=False,is_shift=False,is_alt=False,is_or=False,type:str=KeyType.CYCLE):
        """
            1.添加默认参数是为了初始化的时候方便，暂时先这样
        """
        self.section=section
        self.condition=condition
        #keyboard 不做校验直接输出,防止有奇奇怪怪的东西卡住
        self.keyboard=keyboard

        #用户界面显示
        self.notify=True
        #key的修饰键
        self.is_ctrl=is_ctrl
        self.is_shift=is_shift
        self.is_alt=is_alt
        self.defaultvalue=defaultvalue
        
        #按键切换信息,只有从ini中读取才可能多个值
        # wci设计只会保留一个值切换，减少判断逻辑
        self.swap={}
        self.type=type
        #blender中使用判断不同的按键切换的合并条件 逻辑或 or ||
        self.is_or=is_or
        #run= commandlist的条件
        self.commandList=[]

    @property
    def normalizied_keyboard(self):
        v=""
        if self.is_alt==False and self.is_ctrl==False and self.is_shift==False:
            v+="no_modifiers "
        else:
            if self.is_alt:
                v+="alt "
            else:
                v+="no_alt "
            if self.is_ctrl:
                v+="ctrl "
            else:
                v+="no_ctrl "
            if self.is_shift:
                v+="shift "
            else:
                v+="no_shift "
        return (v+self.keyboard).upper()
    
    def set_swap(self,var,swap:list):
        if var in self.swap:
            self.swap[var]=[int(i) for i in list(set(self.swap[var]+swap))]
        else:
            self.swap[var]=[int(i) for i in swap]
    
    def get_var(self):
        if len(self.swap.keys())>0:
            for key in self.swap:
                if key not in ["$creditinfo"]:
                    return key
        else:
            return None
        
    def get_swap(self,var):
        if var in self.swap:
            return self.swap[var]
        else:
            return []


    @staticmethod
    def get_toggle(var,swap):
        """
            #通过swap信息生成条件
        """
            #将swap解析成 key==1 || key==2 || key ==3的格式
        togglevalue=""
        for i in swap:
            togglevalue+=f"{var} == {i} ||"
        if togglevalue[-3:]==" ||":
            togglevalue=togglevalue[0:-3]
        return togglevalue


    def set_keyboard(self,keyboard:str):
        keyboard=keyboard.upper() \
            .replace("NO_CTRL","") \
            .replace("NO_SHIFT","") \
            .replace("NO_ALT","") \
            .replace("NO_MODIFIERS","") \
            .replace(" ","")
        if "CTRL" in keyboard:
            self.is_ctrl=True
            keyboard=keyboard.replace("CTRL","")
        if "SHIFT" in keyboard:
            self.is_shift=True
            keyboard=keyboard.replace("SHIFT","")
        if "ALT" in keyboard:
            self.is_alt=True
            keyboard=keyboard.replace("ALT","")
        self.keyboard=keyboard
    
    def from_raw_data(self,section,raw_data:str):
        self.section=section
        self.keyboard=""
        for line in raw_data.split("\n"):
            line=line.replace(" ","").split(";")[0].lower()
            condition_match = Key.condition_pattern.match(line)
            if condition_match:
                self.condition=condition_match.group(1)
                continue
            key_match=Key.key_pattern.match(line)
            if key_match:
                self.set_keyboard(key_match.group(1))
                continue
            type_match=Key.type_pattern.match(line)
            if type_match:
                self.type=type_match.group(1)
                continue
            var_match=Key.var_pattern.match(line)
            if var_match:
                var=var_match.group(1)
                swap=var_match.group(2).split(",")
                self.set_swap(var,[int(i) for i in swap])
            command_match=Key.command_pattern.match(line)
            if command_match:
                self.commandList.append(command_match.group(1))

    def to_raw_data(self):
        raw_data=""
        if self.condition:
            raw_data+="condition = "+self.condition+"\n"
        raw_data+="key = "+self.normalizied_keyboard+"\n"
        raw_data+="type = "+self.type+"\n"
        for var in self.swap:
            swap=self.swap[var]
            if 0 not in swap:
                swap.insert(0,0)
            swap=list(set(swap))
            swap.sort()
            swap_raw=str(swap).replace("[","").replace("]","").replace("\"","").replace("'","")
            raw_data+=f"{var} = {swap_raw}\n"
        for command in self.commandList:
            raw_data+=f"run = {command}\n"
        if self.notify:
            raw_data+="$creditinfo = 0"
        return raw_data
    
def raw_darw_pack(lv,drawPack:DrawPack):
    raw_data=""
    if drawPack.toggle:
        raw_data+=" "*(lv*4)+"if "+drawPack.toggle
        lv+=1
    if drawPack.name:
        raw_data+="\n"+" "*(lv*4)+"; "+drawPack.name.replace("_"," ")
    if drawPack.prePacks:
        for prePack in drawPack.prePacks:
            raw_data+="\n"+raw_darw_pack(lv,prePack)
    if drawPack.texs:
        append=None
        for tex in drawPack.texs:
            if tex.tex_style==TEX_STYLE.SLOT:
                raw_data+="\n"+" "*(lv*4)+tex.slot+" = "+tex.resource
            elif tex.tex_style==TEX_STYLE.ZZMI:
                slot=tex.slot
                if tex.texname in TexNameDict[TEX_STYLE.ZZMI]:
                    slot=TexNameDict[TEX_STYLE.ZZMI][tex.texname]
                raw_data+="\n"+" "*(lv*4)+slot+" = ref "+tex.resource
                append=r"run = CommandList\ZZMI\SetTextures"
            elif tex.tex_style==TEX_STYLE.RABBITFX:
                slot=tex.slot
                if tex.texname in TexNameDict[TEX_STYLE.RABBITFX]:
                    slot=TexNameDict[TEX_STYLE.RABBITFX][tex.texname]
                raw_data+="\n"+" "*(lv*4)+slot+" = ref "+tex.resource
                append=r"run = CommandList\RabbitFX\SetTextures"
        if append:
            raw_data+="\n"+" "*(lv*4)+append
    if drawPack.subPacks:
        for subPack in drawPack.subPacks:
            raw_data+="\n"+raw_darw_pack(lv,subPack)
    if drawPack.draws:
        for line in drawPack.draws:
            raw_data+="\n"+" "*(lv*4)+line
    if drawPack.sufPacks:
        for sufPack in drawPack.sufPacks:
            raw_data+="\n"+raw_darw_pack(lv,sufPack)
    if drawPack.toggle:
        lv-=1
        raw_data+="\n"+" "*(lv*4)+"endif"
    return raw_data

@dataclass
class ShapeKeyResource:
    name:str = WCI_BASE_CONST.WCI_SHAPEKEY_PREFIX+"default"
    index_count:int = 0
    vertex_count:int = 0
    start_index:int = 0
    start_vertex:int = 0
    base_start_vertex:int = 0

class IniUtil:
    
    @staticmethod
    def __re_replace_section__(data:str,reg:str,context:str,rep_type:str):
        re_datas=re.findall(reg,data,re.S)
        match=False
        if len(re_datas)>0:
            match=True
            if "multi" in rep_type:
                re_data_list=list(set(re_datas))
                for re_data in re_data_list:
                    if rep_type==ReplaceType.MULTI_REPLACE:
                        data=data.replace(re_data,context)
                    elif rep_type==ReplaceType.MULTI_APPEND_REPLACE:
                        data=data.replace(re_data,re_data+context)
                    elif rep_type==ReplaceType.MULTI_INSERT_REPLACE:
                        data=data.replace(re_data,context+re_data)
                    elif rep_type==ReplaceType.NONE:
                        #什么也不干
                        data=data
            elif  rep_type in [ReplaceType.LINE_APPEND,ReplaceType.LINE_INSERT] and len(re_datas)==1:
                if rep_type==ReplaceType.LINE_INSERT:
                    new_data=""
                    for line in re_datas[0].split("\n"):
                        if line=="":
                            continue
                        new_data+=context+line+"\n"
                    data=new_data
                elif rep_type==ReplaceType.LINE_APPEND:
                    new_data=""
                    for line in re_datas[0].split("\n"):
                        if line=="":
                            continue
                        new_data+=line+context+"\n"
                    data=new_data
            elif "multi" not in rep_type and len(re_datas)==1:
                match_info=re.search(reg,data,re.S)
                if rep_type==ReplaceType.REPLACE:
                    data=data[0:match_info.start(1)]+context+data[match_info.end(1):]
                elif rep_type==ReplaceType.APPEND_REPLACE:
                    data=data[0:match_info.end(1)]+context+data[match_info.end(1):]
                elif rep_type==ReplaceType.INSERT_REPLACE:
                    data=data[0:match_info.start(1)]+context+data[match_info.start(1):]
                elif rep_type==ReplaceType.NONE:
                    #什么也不干
                    data=data
            else:
                raise Exception("匹配类型异常，匹配到多个目标但是并未设置为multi!",reg)
        elif rep_type in [ReplaceType.NON_APPEND]:
            match=True
            data=data+context
        elif rep_type in [ReplaceType.NON_INSERT]:
            match=True
            data=context+data
        elif rep_type in [ReplaceType.MULTI_APPEND_REPLACE,\
                          ReplaceType.MULTI_INSERT_REPLACE,\
                          ReplaceType.MULTI_NON_APPEND,\
                          ReplaceType.MULTI_NON_INSERT,\
                          ReplaceType.MULTI_REPLACE,]:
            match=True
            data=data
        return data,match

    @staticmethod
    def re_replace(sections:Dict[str,Section],reg_group,data_dict)->Dict[str,Section]:
        """
        通过正则表达式替换3dmigoto文件配置数据,
        data_dict是键值对，里面是需要的替换内容
        """
        for regx in reg_group:
            section=regx["section"]
            reg=regx["re"]
            context=regx["context"]
            rep_type=regx["type"]
            for data_k in data_dict:
                _data_k="{"+data_k+"}"
                if _data_k in reg:
                    reg=reg.replace(_data_k,str(data_dict[data_k]))
                if _data_k in context:
                    context=context.replace(_data_k,str(data_dict[data_k]))
                if _data_k in section:
                    section=section.replace(_data_k,str(data_dict[data_k]))
            if "{" and "}" in context:
                print("内容不完全替换，请检查替换字典!",section,context,rep_type)
            if section[-1]=="]":
                if section not in sections or sections[section].data==None or sections[section].data=="":
                    #section不存在，创建section
                    #context的东西直接加上去，不论是替换还是添加,没有内容构建正则表达式无意义
                    typeInfo,subTypeInfo=Section.parse_section_type(section,context)
                    sections[section]=Section(section,{"data":context,"type":typeInfo,"subType":subTypeInfo})
                else:
                    #每个section唯一
                    data,match=IniUtil.__re_replace_section__(sections[section].data,reg,context,rep_type)
                    if match==False:
                        raise Exception("section匹配失败!",section,reg,context,sections[section].data)
                    sections[section].data=data
                    if 'ib_hash' in data_dict:
                        sections[section].ib=data_dict["ib_hash"]
                    if "hash" in data_dict:
                        sections[section].hash=data_dict["hash"]
            else:
                #section不闭合，需要遍历替换        
                find=False
                for key in sections:
                    if section in key:
                        data,find=IniUtil.__re_replace_section__(sections[key].data,reg,context,rep_type)
                        sections[key].data=data
                    if find==True and "multi" not in rep_type:
                        break
                if find==False:
                    raise Exception("section匹配失败:",section,context,rep_type)
        return sections

    @staticmethod
    def parse_section(section_name:str,context:str,parse_key=True)->Tuple[Section,Key]:
        section:Section=None
        key:Key=None
        typeInfo,subTypeInfo=Section.parse_section_type(section_name,context)
        if parse_key and typeInfo==SectionType.Key:
            #按键信息转换为Key
            key=Key()
            key.from_raw_data(section_name,context)
        else:
            section=Section(section_name,{"data":context,"type":typeInfo,"subType":subTypeInfo})
        if subTypeInfo==SectionSubType.File and typeInfo==SectionType.Resource:
            files=re.findall(".*?filename = (.*?\.(?:dds|ib|buf|txt|png|jpg|bmp|tga)).*?",context)
            if len(files)>0:
                section.file=files[0]
        return section,key
       
    @staticmethod
    def parse_ini(config_data:str,parse_key=True)->Tuple[Dict[str,Section],Dict[str,Key]]:
        # 将config_data按section解析
        sections:Dict[str,Section]={}
        keys:Dict[str,Key]={}
        config_data="[Global_Head]\n"+config_data+"\n[Global_Foot]"
        section=""
        context=""
        for line in config_data.split("\n"):
            if line.strip().startswith("["):
                if section!="":
                    section_obj,key_obj=IniUtil.parse_section(section,context,parse_key)
                    if section_obj!=None:
                        sections[section]=section_obj
                    if key_obj!=None:
                            keys[key_obj.normalizied_keyboard]=key_obj
                    section=line.strip()
                    context=""
                else:
                    section=line.strip()
                    context=""
            else:
                context+=line+"\n"
        return sections,keys

    @staticmethod
    def get_patterns_by_name(game,name):
        if name in Patterns.group[game]:
            return Patterns.group[game][name]
        else:
            raise Exception("正则替换列表不存在:"+name)
            
    @staticmethod
    def merge_ini(ib_alias_dict:Dict[str,str],sections:Dict[str,Section],config_name="mod",links:Dict[str,str]=None)->Union[Dict[str,Section],str]:
        """
           将解析的ini合并成字符串数据
        """
        config_data=""
        section_names=list(sections.keys())
        section_names.sort()

        ib_hashs=list(ib_alias_dict.keys())
        ib_hashs.sort()

        #开始写文本数据
        for category in ["Head"]:
            for template_item in Patterns.wci_ini_template[category]:
                if template_item["type"]==SectionType.GlobalHead:
                    config_data+=template_item["comment"].replace(r"{name}",config_name)+"\n\n"
                elif  template_item["comment"]!="":
                    config_data+=template_item["comment"]+"\n\n"
                for section_name in section_names:
                    #遍历ib，保证所有ib都被写入
                    section=sections[section_name]
                    if section.write:
                        #已经写入的不做判断
                        continue
                    if section.sectionType in [SectionType.GlobalHead,SectionType.GlobalFoot]:
                        section.write=True
                        continue
                    if template_item["type"]==section.sectionType:
                        if section.subSectionType!=SectionSubType.SubUndefined:
                            if template_item["subType"]==section.subSectionType:
                                config_data+=section.row_data
                                section.write=True
                        else:
                            config_data += section.row_data
                            section.write=True
        for hash in ib_hashs:
            ##遍历ib
            ib_alias =ib_alias_dict[hash]
            for template_item in Patterns.wci_ini_template["Body"]:
                if template_item["comment"]!="":
                    config_data+=template_item["comment"]+"\n\n"
                for section_name in section_names:
                    section=sections[section_name]
                    if section.write:
                        #已经写入的不做判断
                        continue
                    if (hash in section_name or ib_alias in section_name) and template_item["type"]==section.sectionType:
                        if section.subSectionType!=SectionSubType.SubUndefined:
                            if template_item["subType"]==section.subSectionType:
                                config_data+=section.row_data
                                section.write=True
                        else:
                            config_data += section.row_data
                            section.write=True
        for template_item in Patterns.wci_ini_template["Foot"]:
            #Foot包含有所有类型，保证所有数据都能被写入
            if template_item["comment"]!="":
                config_data+=template_item["comment"]+"\n\n"
            for section_name in section_names:
                #遍历section，保证所有section都被写入
                section=sections[section_name]
                if section.write:
                    #已经写入的不做判断
                    continue
                if template_item["type"]==section.sectionType:
                    if section.subSectionType!=SectionSubType.SubUndefined:
                        if template_item["subType"]==section.subSectionType:
                            config_data+=section.row_data
                            section.write=True
                    else:
                        config_data += section.row_data
                        section.write=True
        #写作者信息
        if links:
            for key in links:
                val=links[key]
                config_data+=f";{key}: {val}\n"
        return sections,config_data
    


class WciResourceManager:

    key_sign_pattern=re.compile(r".*?\$key_sign_([a-z0-9_]+).*?")
    
    def __init__(self,game,buf_path,mod_path):
        #生成id相关
        self._lock = threading.Lock()
        self._type_map = {}      # type -> {str: id}
        self._type_max_id = {}   # type -> max_id
        

        self.game:str=game
        self.buf_path:str=buf_path
        self.mod_path:str=mod_path

        self.config_name:str = "mod"
        self.comment:str=""           # 自定义内容来自comment.txt
        self.links:Dict[str,str] = {} # 作者信息来自ex_config加载
        self.namespace:str = None     # 命名空间
        
        #记录所有的active的激活信息
        #默认都是 active == 1
        self.active_info:Dict[str,List[str]]=defaultdict()
        
        #资源相关
        #每一个tex对应一个文件hash hash一致的用同一个tex, 用来对tex去重 hash:tex_resource_name
        self.tex_hash_dict:Dict[str,TexResource]={}

        #每个文件名都维护一个list,存储不同路径的重名文件，用来对重名文件编号
        self.file_name_dict:Dict[str,str]={}

        #文件路径到哈希的缓存，避免重复计算大文件的哈希
        self._file_hash_cache:Dict[str,str]={}

        #将drawindexed过程抽象为一个DrawPack后续中扩展方便修改
        self.drawPacks:Dict[str,List[DrawPack]]={}
        
        #存储所有的Section
        self.sections:Dict[str,Section] = {}
        #存储所有的Key
        self.keys:Dict[str:Key] = defaultdict()
        
        #形态键
        self.shapekeys:List[ShapeKeyResource]=[]

        self.frames:List[str]=[]
        #ib别名字典
        self.ib_alias_dict:Dict[str:str]={}
        
        #存储所有ib，绘制索引，关联的vs
        
        #在骨骼变换矩阵重定向中使用
        self.ib_vs_dict:defaultdict[str,defaultdict[str,str]]=defaultdict(defaultdict)
        
        self.__init_wci_folder__()

    def get_number_id(self,string,type_key="all")->str:
        """
        给字符串编号
        
        :param string: 字符串
        """
        with self._lock:
            if type_key not in self._type_map:
                self._type_map[type_key] = {}
                self._type_max_id[type_key] = 0

            if string in self._type_map[type_key]:
                return str(self._type_map[type_key][string])
            else:
                self._type_max_id[type_key] += 1
                new_id = self._type_max_id[type_key]
                self._type_map[type_key][string] = new_id
                return str(new_id)
    
    def __init_wci_folder__(self):
        #删除mod文件夹
        if os.path.isdir(self.mod_path) and self.mod_path!=self.buf_path:
            #防止删除buf_path
            shutil.rmtree(self.mod_path)
        os.makedirs(self.mod_path,exist_ok=True)
        
        #wci文件夹创建
        for folder in FOLDER_NAME.get_buf_folders():
            path = os.path.join(self.buf_path,folder)
            if not os.path.isdir(path):
                os.makedirs(path)
        
        #mod文件夹创建
        for folder in FOLDER_NAME.get_mod_folders():
            path = os.path.join(self.mod_path,folder)
            if not os.path.isdir(path):
                os.makedirs(path)


    def add_tex(self,ib_hash,file_path,slot,hash,texname)->TexResource:
        file_name,file_suf=os.path.splitext(os.path.split(file_path)[1])

        # 使用缓存避免重复计算文件哈希
        if file_path in self._file_hash_cache:
            file_hash = self._file_hash_cache[file_path]
        else:
            file_hash = get_file_hash(file_path)
            self._file_hash_cache[file_path] = file_hash

        if file_hash in self.tex_hash_dict:
            tex = deepcopy(self.tex_hash_dict[file_hash])
            tex.file_path=file_path
            return tex
        else:
            file_name_key=file_name+file_suf
            if file_name_key in self.file_name_dict:
                self.file_name_dict[file_name_key].append(file_path)
            else:
                self.file_name_dict[file_name_key]=[file_path]
            index=len(self.file_name_dict[file_name_key])
            if index>1:
                new_file=f"{file_name}{index}{file_suf}".replace(ib_hash,self.ib_alias_dict[ib_hash])
                resource_name="Resource_"+file_name+str(index)
            else:
                new_file=file_name.replace(ib_hash,self.ib_alias_dict[ib_hash])+file_suf
                resource_name="Resource_"+file_name.replace(ib_hash,self.ib_alias_dict[ib_hash])
            new_file_path=os.path.join(self.mod_path,FOLDER_NAME.TEXTURE,new_file)
            shutil.copyfile(file_path,new_file_path)
            self.merge_to_sections(WCI_PATTERN_NAME.ADD_TEX_RESOURCE,
                                                {"resource":resource_name,"file":new_file})
            tex=TexResource(slot=slot,hash=hash,texname=texname,file_path=new_file_path,resoure_name=resource_name)
            self.tex_hash_dict[file_hash]=tex
            return tex
        
    def add_section(self,section:Section):
        keyboards=self.key_sign_pattern.findall(section.data)
        if keyboards:
            for keyboard in keyboards:
                nk=normalizied_keyboard(keyboard.replace("_"," "))
                if nk in self.keys:
                    var=self.keys[nk].get_var()
                    if var:
                        section.data=section.data.replace("$key_sign_"+keyboard,var)
        if section.sectionType == SectionType.Resource:
            match=re.match(".*?filename *= *(.*?\.(?:dds|ib|buf|txt|png|jpg|bmp|tga)).*?",section.data,re.S)
            if match:
                file=match.group(1)
                file_path=os.path.join(self.buf_path,file)
                if os.path.isfile(file_path):
                    # 已存在对应名称则不复制
                    # 自定义配置文件内容的正确性应该由用户控制
                    mod_file_path=os.path.join(self.mod_path,file)
                    if os.path.isfile(mod_file_path):
                        print("buffer文件已存在",file)
                    else:
                        shutil.copyfile(file_path,mod_file_path)
            self.sections[section.section]=section                    
        elif section.section in self.sections:
            section_name=section.section
            lines=section.data.split("\n")
            for line in lines:
                if "endif" in line or line not in self.sections[section_name].data:
                    self.sections[section_name].data+=line+"\n"
        else:
            self.sections[section.section]=section

        return section


    def copy_file(self,ib_hash,file_path,file_type=FILE_TYPE.BUF):
        ib_alias=self.ib_alias_dict[ib_hash]
        if file_type==FILE_TYPE.BUF:
            bufer_path=os.path.join(self.mod_path,FOLDER_NAME.BUFFER)
            buffer_file=os.path.join(bufer_path,os.path.split(file_path)[1].replace(ib_hash,ib_alias))
            shutil.copyfile(file_path,buffer_file)
        elif file_type==FILE_TYPE.TEX:
            tex_path=os.path.join(self.mod_path,FOLDER_NAME.TEXTURE)
            tex_file=os.path.join(tex_path,os.path.split(file_path)[1].replace(ib_hash,ib_alias))
            shutil.copyfile(file_path,tex_file)
        else:
            raise Exception("未识别的文件类型",file_path)
    
    def parse_toggle(self,export_item,swaps)->Tuple[str,str]:
        """
            生成keyvalue和对应的Keys信息
            #key_bindings_Keys来自obj对象的按键切换

        """
        keyvalue=""
        for var,swap,is_or in swaps:
            subkeyvalue=Key.get_toggle(var,swap)
            if "||" in subkeyvalue and len(swaps)>1:
                subkeyvalue=f"( {subkeyvalue} )"
            if is_or:
                subkeyvalue="|| "+subkeyvalue
            else:
                subkeyvalue="&& "+subkeyvalue
            keyvalue+=subkeyvalue
        keyvalue=keyvalue.lstrip("&& ").lstrip("|| ")
        #print(export_item,"toggle -> if ",keyvalue)
        return keyvalue

    def get_patterns_by_name(self,name):
        return IniUtil.get_patterns_by_name(self.game,name)
        
    def merge_to_sections(self,pattern_name:str,data_dict):
        self.sections=IniUtil.re_replace(self.sections,self.get_patterns_by_name(pattern_name),data_dict)

    def add_key(self,key:Key,swap)->Key:
        #将一个key合并到keys
        new_key:Key=None
        if key.normalizied_keyboard in self.keys:
            #合并swap
            new_key=self.keys[key.normalizied_keyboard]
        else:
            new_key=key
        var = new_key.get_var()
        if not var:
            var="$swapkey"+self.get_number_id(key.normalizied_keyboard)
        if new_key.type==KeyType.CYCLE:
            new_key.set_swap(var,swap)
        self.keys[new_key.normalizied_keyboard]=new_key
        return new_key
    

    def get_drawpack_by_obj_name(self,obj_name)->Tuple[int,DrawPack]:
        ib_hash,ib_sub_alias,item_name = parse_obj_name(obj_name)
        key=(ib_hash,ib_sub_alias)
        if  key in self.drawPacks:
            for i in range(0,len(self.drawPacks[key])):
                drawPack=self.drawPacks[key][i]
                if drawPack.name==obj_name:
                    return i,drawPack
        return None,None
    
    def get_drawpacks_by_ib(self,ib_hash:str,ib_sub_alias)->List[DrawPack]:
        if (ib_hash,ib_sub_alias) in self.drawPacks:
            return self.drawPacks[(ib_hash,ib_sub_alias)]
        else:
            return []

    def add_drawPacks(self,ib_hash,ib_sub_alias,drawPacks:List[DrawPack]):
        if (ib_hash,ib_sub_alias) in self.drawPacks:
            for drawPack in drawPacks:
                if drawPack not in self.drawPacks[(ib_hash,ib_sub_alias)]:
                    self.drawPacks[(ib_hash,ib_sub_alias)].append(drawPack)
        else:
            self.drawPacks[(ib_hash,ib_sub_alias)]=drawPacks

    def update_drawPack(self,drawPack:DrawPack):
        ib_hash,ib_sub_alias,item_name = parse_obj_name(drawPack.name)
        key=(ib_hash,ib_sub_alias)
        if  key in self.drawPacks:
            for i in range(0,len(self.drawPacks[key])):
                i_drawPack=self.drawPacks[key][i]
                if i_drawPack.name==drawPack.name:
                    self.drawPacks[key][i]=drawPack    

    def remove_drawPack(self,drawPack:DrawPack):
        ib_hash,ib_sub_alias,item_name = parse_obj_name(drawPack.name)
        key=(ib_hash,ib_sub_alias)
        del_i=-1
        if  key in self.drawPacks:
            for i in range(0,len(self.drawPacks[key])):
                i_drawPack=self.drawPacks[key][i]
                if i_drawPack.name==drawPack.name:
                    del_i=i
                    break
            if del_i>-1:
                del self.drawPacks[key][del_i]

    def append_drawPack(self,ib_hash,ib_sub_alias,drawPack:DrawPack):
        key=(ib_hash,ib_sub_alias)
        if  key in self.drawPacks:
            self.drawPacks[key].append(drawPack)
        
        


def get_tex(buf_path,ib_hash,ib_alias,sub_alias,widgetname,default_slot_info)->List[TexResource]:

    def remove_rightmost_digits(s):
        # 从字符串的末尾开始向前遍历
        i = len(s) - 1
        while i >= 0 and s[i].isdigit():
            i -= 1
        # 返回不包含右边数字的新字符串
        return s[:i+1]
    tex_info=[]
    #先找名称，没有才去转换default_slot_info
    widgetname=re.sub(r'\.[0-9]+$', '', widgetname)
    for slot in default_slot_info:
        name=default_slot_info[slot]["name"]
        dds_file=""
        widget_name=remove_rightmost_digits(widgetname)
        #先找自己同名的没有才会去减序号找文件。
        file_info=("",widgetname)
        for suffix in [ib_alias+"-"+widgetname,widgetname,ib_alias+"-"+widget_name,widget_name]:
            dds_file = os.path.join(buf_path,FOLDER_NAME.TEXTURE,suffix+"-"+name+".dds")
            if os.path.isfile(dds_file):
                file_info=(dds_file,suffix)
                break
        if os.path.isfile(file_info[0]):
            tex=TexResource()
            tex.slot=slot
            tex.hash=default_slot_info[slot]["hash"]
            tex.texname=name
            tex.file_path=dds_file
            tex.resource=f"Resource_"+file_info[1].replace(" ","_")+"-"+name
            tex_info.append(tex)
        else:
            #没有则遍历default_slot_info
            for default_slot in default_slot_info:
                if slot==default_slot:
                    tex=TexResource()
                    tex.slot=default_slot
                    tex.hash=default_slot_info[slot]["hash"]
                    tex.texname=default_slot_info[slot]["name"]
                    file=default_slot_info[slot]["file"]
                    tex.file_path=os.path.join(buf_path,ib_hash,file)
                    tex.resource=f"Resource_"+file.replace("-","_").replace(".dds","").replace(".jpg","")
                    tex_info.append(tex)
    return tex_info



if __name__=="__main__":
    pass