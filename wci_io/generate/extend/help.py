import os
import math
import shutil

from .ex_config import ExConfig
from ..wci_resources import WciResourceManager,IniUtil

from ..utils import normalizied_keyboard
from ...constants import FOLDER_NAME



def get_help_ini(keyboard,creditinfo,panel_config_data,help_txt_name):
    help_ini=f"""
[KeyHelp]
condition = $active == 1
key = {keyboard}
type = toggle
run = CommandListHelp

[Present]
run = CommandListCreditInfo

[CommandListHelp]
pre Resource\\ShaderFixes\\help.ini\\Help = ref Resourcehelp
pre Resource\\ShaderFixes\\help.ini\\Params = ref ResourceParamsFull
pre run = CustomShader\\ShaderFixes\\help.ini\\FormatText

pre Resource\\ShaderFixes\\help.ini\\HelpShort = null
post Resource\\ShaderFixes\\help.ini\\Help = null



[Resourcehelp]
type = buffer
format = R8_UINT
filename = {FOLDER_NAME.RES}/{help_txt_name}.txt

[ResourceParamsFull]
type = StructuredBuffer
array = 1
data = {panel_config_data}


[CommandListCreditInfo]
if $creditinfo == 0 && $active == 1
	pre Resource\\ShaderFixes\\help.ini\\Notification = ResourceCreditInfo
	pre run = CustomShader\\ShaderFixes\\help.ini\\FormatText
	pre $\\ShaderFixes\\help.ini\\notification_timeout = time + 5.0
	$creditinfo = 1
endif

[ResourceCreditInfo]
type = Buffer
data = "{creditinfo}"


"""
    return help_ini

class HelpPanelConfig:
    def __init__(self,d):
        if "rectangle" in d:
            self.rectangle=d["rectangle"]
        if "forecolor" in d:
            self.forecolor=d["forecolor"]
        if "background" in d:
            self.background=d["background"]
        if "border" in d:
            self.border=d["border"]
        if "anchor" in d:
            self.anchor=d["anchor"]
        if "text align" in d:
            self.text_align=d["text align"]
        if "font scale" in d:
            self.font_scale=d["font scale"]

    @property
    def rectangle_str(self):
        string="0.3 -1 1 1"
        if hasattr(self,"rectangle"):
            if type(self.rectangle) is list and len(self.rectangle)==4:
                x1,y1,x2,y2=self.rectangle
                string=f"{x1} {y1} {x2} {y2}"
        return string

    @property
    def forecolor_str(self):
        string="1 1 1 1"
        if hasattr(self,"forecolor"):
            if type(self.forecolor) is list and len(self.forecolor)==4:
                r,g,b,a=self.forecolor
                string = f"{format(r,'.2f')} {format(g,'.2f')} {format(b,'.2f')} {format(a,'.2f')}"
            elif type(self.forecolor) is str and self.forecolor.startswith("#"):
                r,g,b,a=self.color_to_rgba(self.forecolor)
                string = f"{format(r,'.2f')} {format(g,'.2f')} {format(b,'.2f')} {format(a,'.2f')}"
        return string

    @property
    def background_str(self):
        string="0 0 0 0.5"
        if hasattr(self,"background"):
            if type(self.background) is list and len(self.background)==4:
                r,g,b,a=self.background
                string = f"{format(r,'.2f')} {format(g,'.2f')} {format(b,'.2f')} {format(a,'.2f')}"
            elif type(self.background) is str and self.background.startswith("#"):
                r,g,b,a=self.color_to_rgba(self.background)
                string = f"{format(r,'.2f')} {format(g,'.2f')} {format(b,'.2f')} {format(a,'.2f')}"
        return string

    @property
    def border_str(self):
        string="0.1 0.1"
        if hasattr(self,"border"):
            if type(self.border) is list and len(self.border)==2:
                x,y=self.border
                string = f"{x} {y}"
        return string

    @property
    def anchor_str(self):
        #h/v-anchor: 0=none 1=left/top 2=center 3=right/bottom
        string="1 2"
        if hasattr(self,"anchor"):
            if type(self.anchor) is list and len(self.anchor)==2:
                x,y=self.anchor
                x = {'left':1, 'center':2, 'right':3}.get(x, x)
                y = {'top':1, 'center':2, 'bottom':3}.get(y, y)
                string = f"{x} {y}"
        return string
    
    @property
    def text_align_str(self):
        #text alignment: 0=left 1=center 2=right
        string="0"
        if hasattr(self,"text_align"):
            if type(self.text_align) is str:
                if self.text_align=="left" or self.text_align=="0":
                    string = "0"
                elif self.text_align=="center" or self.text_align=="1":
                    string = "1"
                elif self.text_align=="right" or self.text_align=="2":
                    string = "2"
        return string

    @property
    def font_scale_str(self):
        string="1.0"
        if hasattr(self,"font_scale"):
            if type(self.font_scale) is float or type(self.font_scale) is int:
                string=str(self.font_scale)
        return string
    
    def color_to_rgba(self,hex_str):
        hex_str = hex_str.lstrip('#')
        # 处理 #FFF 简写
        if len(hex_str) == 3:
            hex_str = ''.join(c*2 for c in hex_str)
            hex_str+="FF"
        if len(hex_str) == 6:
            hex_str+="FF"
        if len(hex_str) == 8:
            r = int(hex_str[0:2], 16) / 255.0
            g = int(hex_str[2:4], 16) / 255.0
            b = int(hex_str[4:6], 16) / 255.0
            a = int(hex_str[6:8], 16) / 255.0
            return r,g,b,a
        else:
            return 1,1,1,1

    def panel_config_data(self):
        return f"R32_FLOAT  \
            {self.rectangle_str}  \
            {self.forecolor_str}  \
            {self.background_str}  \
            {self.border_str}  \
            {self.anchor_str}  \
            {self.text_align_str}  \
            {self.font_scale_str}"
        



def get_hlep_txt(help_info,keyboard,link_info):
    help_txt=f"""



                ### WCI TOGGLE###


{help_info}

         Press {keyboard} to turn on/off this sheet
find me: 
		{link_info}

"""
    return help_txt


key_rep="""
    [{key}] {name} ({swapList})
"""



def add_help(ex_config:ExConfig,mod_manager:WciResourceManager):
    help_info=""
    link_info=""
    if "keyboard" not in ex_config.wci_helps or len(ex_config.wci_helps["keyboard"])<1:
        return mod_manager
    help_keyboard=normalizied_keyboard(ex_config.wci_helps["keyboard"])
    if "panel" in ex_config.wci_helps:
        panelConfig=HelpPanelConfig(ex_config.wci_helps["panel"])
    else:
        panelConfig=HelpPanelConfig({})
    creditinfo=ex_config.wci_helps["creditinfo"]
    for link in ex_config.wci_mod_links:
        link_info+="\t\t"+link+":"+ex_config.wci_mod_links[link]+"\n"
    keyboards=list(mod_manager.keys.keys())
    keyboards=sorted(keyboards,key=lambda x:x.replace("NO_","").replace("ALT","").replace("CTRL","").replace("SHIFT","").lower())
    for keyboard in keyboards:
        key=mod_manager.keys[keyboard]
        var=key.get_var()
        swap=key.get_swap(var)
        swap_list=str(swap)[1:-1]
        kb=keyboard.replace("NO_MODIFIERS ","").replace("NO_CTRL","").replace("NO_SHIFT","").replace("NO_ALT","").replace("VK_","").lower()
        help_info+=f"[ {kb} ] ({swap_list})\n"
    #写入help ini
    help_ini=get_help_ini(help_keyboard,creditinfo,panelConfig.panel_config_data(),"help")
    sections,keys=IniUtil.parse_ini(help_ini)
    #合并sections,keys
    for section_name in sections:
        mod_manager.add_section(sections[section_name])

    for keyboard in keys:
        key=keys[keyboard]
        key.notify=False
        mod_manager.add_key(key,[])
    
    if ""==help_info:
        help_info="    No toggle"
    res_help_file_path=os.path.join(mod_manager.buf_path,FOLDER_NAME.RES,"help.txt")
    help_file_path=os.path.join(mod_manager.mod_path,FOLDER_NAME.RES,"help.txt")
    if os.path.isfile(res_help_file_path):
        shutil.copy(res_help_file_path,help_file_path)
    else:
        with open(help_file_path,"w",encoding="utf-8") as f:
            f.write(get_hlep_txt(help_info,help_keyboard,link_info))
    return mod_manager

        
