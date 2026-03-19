import os
import shutil
import math

from collections import defaultdict

from ...constants import Game,FILE_TYPE,WCI_BASE_CONST,ReplaceType,FOLDER_NAME
from ..wci_resources import WciResourceManager,DrawPack,Key,TexResource,IniUtil,Section
from ...constants import WCI_PATTERN_NAME
from ...utils import parse_obj_name
from .ex_config import ExConfig


shapekey_ui=f"""
[Constants]
global persist $mx = 0.207812503
global persist $my = 0.120833427
global $menu = 0
global $hold
global $holdShape
global $drag
global $hovering
global $currentSlider
global $ww 
global $wh
global $cpx
global $cpy
global $dt
global $ts

global $slider_base_x = 0.0
global $slider_base_y = 0.0


[KeyMenu]
condition = $active == 1
key = NO_MODIFIERS /
type = cycle
$menu = 0,1

[KeyMenu.ResetPosition]
condition = $menu == 1
key = CTRL SHIFT /
run = CommandListResetMenuPos

[KeyHold]
condition = $menu == 1 && $hovering == 0
key = NO_CTRL NO_SHIFT VK_LBUTTON
key = NO_CTRL NO_SHIFT VK_RBUTTON
type = hold
$hold = 1

[KeyHoldShape]
condition = $menu == 1 && $hovering >= 1
key = NO_CTRL NO_SHIFT VK_LBUTTON
key = NO_CTRL NO_SHIFT VK_RBUTTON
type = hold
run = CommandListHoldShape

[CommandListHoldShape]
$holdShape = $hovering
post $holdShape = 0


[Present]
if $costume_mods
    $dt = time - $ts
    $ts = time
    
    run = CommandListComputeShapekeys
    if $menu
        run = CommandListOutfitMenu
    endif
endif


[CommandListComputeShapekeys]
; 计算顶点位置

[CommandListDimensions]
if window_width != 0
  $ww = window_width
  $wh = window_height
elif $ww != 0
  $ww = rt_width
  $wh = rt_height
else
  $ww = res_width
  $wh = res_height
endif

if cursor_x != 0 && cursor_y != 0
  $cpx = cursor_x
  $cpy = cursor_y
elif cursor_window_x != 0 && cursor_window_y != 0
  $cpx = cursor_window_x / $ww
  $cpy = cursor_window_y / $wh
else
  $cpx = cursor_screen_x / $ww
  $cpy = cursor_screen_y / $wh
endif

[CommandListResetMenuPos]
$mx = 50 / $ww
$my = 0.5 - 360 / $wh



[CommandListOutfitMenu]
run = CommandListDimensions
run = CommandListBackground

[CommandListBackground]
local $cox
local $coy
ps-t100 = ResourceMenuBG
y87 = 560 / $wh
x87 = 360 / $ww
if $hovering == 0
    if $drag == 0
        if $cpx > $mx + 0.0125 && $cpx < ($mx+x87-0.0035) && $cpy > $my && $cpy < ($my+y87-0.0035)
            if $hold
                $cox = $cpx - $mx
                $coy = $cpy - $my
                $drag = 1
            endif
        endif
    else
        if $hold
            $mx = $cpx - $cox
            $my = $cpy - $coy
        else
            $drag = 0
        endif
    endif
endif
z87 = $mx
w87 = $my
run = CustomShaderElement
run = CommandListDrawAllSliders

[CommandListDrawAllSliders]
local $z0 = z87 + 23 / $ww
local $wo = 84 / $wh
$hovering = 0


[CustomShaderElement]
vs = {FOLDER_NAME.RES}/draw_2d.hlsl
ps = {FOLDER_NAME.RES}/draw_2d.hlsl
run = BuiltInCommandListUnbindAllRenderTargets
blend = ADD SRC_ALPHA INV_SRC_ALPHA
cull = none
topology = triangle_strip
o0 = set_viewport bb
Draw = 4,0

[ResourceMenuBG]
filename = {FOLDER_NAME.RES}/Menu.dds
[ResourceSlider]
filename = {FOLDER_NAME.RES}/Slider.dds
[ResourceSliderPink]
filename = {FOLDER_NAME.RES}/Slider_pink.dds
[ResourceButton]
filename = {FOLDER_NAME.RES}/Button.dds
[ResourceButtonHover]
filename = {FOLDER_NAME.RES}/Button_Hover.dds
[ResourceItemBlock]
filename = {FOLDER_NAME.RES}/item_block.dds
"""

format_to_type = {
"R32G32B32_FLOAT": "float3",
"R32G32B32A32_FLOAT": "float4",
"R32G32_FLOAT": "float2",
"R32_FLOAT": "float",
"R32_UINT": "uint",
}

def get_shapekey_ini(namespace,number_id,slider_val,slider_target):
    return f"""
; 形态键UI基础格式来自 LastRite
; 由ergry改造为分离形式并应用与WCI
; The basic format of the shapekey UI was originally from LastRite
; modified by ergry into a separate form.
namespace = {namespace}
[Constants]
global persist ${slider_val} = 0
global persist ${slider_target} = 0

; 重置滑块的值
[CommandListResetSlider{number_id}]
${slider_val} = 0
${slider_target} = 0

[CommandListDrawFullSlider{number_id}]
$currentSlider = {number_id}

; 绘制图标（使用主文件传入的 $slider_base_x, $slider_base_y）
x87 = 52 / $ww
y87 = 52 / $wh
z87 = $slider_base_x
w87 = $slider_base_y
ps-t100 = Resource_shapekey_icon{number_id}
run = CustomShaderElement

; 设置滑块条位置并调用滑块条绘制
z87 = $slider_base_x + 80 / $ww
w87 = $slider_base_y + 25 / $wh
run = CommandListDrawSlider{number_id}

; 滑块1的滑块条绘制（背景、填充、光标）
[CommandListDrawSlider{number_id}]
local $val = ${slider_val}

; 绘制滑块条背景
ps-t100 = ResourceSlider
x87 = 230 / $ww
y87 = 4 / $wh
run = CustomShaderElement

; 绘制滑块填充
ps-t100 = ResourceSliderPink
x87 = $val * 230 / $ww
run = CustomShaderElement

; 处理鼠标交互和按钮绘制
x87 = 230 / $ww
run = CommandListCursorSlider{number_id}

; 滑块的光标处理
[CommandListCursorSlider{number_id}]
local $x = z87
local $y = w87
local $xo = z87 + x87
local $yo = w87 + y87
local $newTarget

; 检测鼠标悬停
if $cpx > $x && $cpx < $xo && $holdShape == 0
    if $cpy > $y - 15 / $wh && $cpy < $yo + 15 / $wh
        $hovering = {number_id}
    endif
endif

; 如果正在拖动，更新目标值
if $holdShape == {number_id}
    $newTarget = (($cpx-$x)/($xo-$x))
    if $newTarget < 0
        $newTarget = 0
    elif $newTarget > 1
        $newTarget = 1
    endif
    ${slider_target} = $newTarget
endif

; 计算按钮位置
z87 = (z87 + x87 * (${slider_val}) - 14 / $ww)

; 绘制按钮（高亮如果悬停、选中或拖动）
if $hovering == {number_id} || $holdShape == {number_id}
    ps-t100 = ResourceButtonHover
else
    ps-t100 = ResourceButton
endif
x87 = 32 / $ww
y87 = 32 / $wh
w87 = w87 - 13 / $wh
run = CustomShaderElement

; 滑块1的插值命令
[CommandListInterpolateSlider{number_id}]
local $td = 0.033
local $ds = (${slider_target} - ${slider_val}) / $td
${slider_val} = ${slider_val} + $ds * $dt


[Resource_shapekey_icon{number_id}]
filename = {FOLDER_NAME.RES}/shapekey_icon{number_id}.dds
"""
def get_element_dict(elements):
    element_dict={}
    for elem in elements:
        semantic = elem.get("AliasSemanticName", "").lower()
        fmt = elem.get("Format", "")
        typ = format_to_type.get(fmt, "unknown")
        element_dict[semantic]=typ
    return element_dict

def get_position_element_dicts(buf_dicts):
    r=defaultdict()
    r_suf=""
    r_buf=""
    for ib in buf_dicts:
        buf_dict=buf_dicts[ib]
        for buf in buf_dict:
            if "fmts" in buf_dict[buf]:
                for fmt in buf_dict[buf]["fmts"]:
                    if "file" in fmt and "POSITION" in fmt["metadata"]["semantics"]:
                        r[ib]=get_element_dict(fmt["metadata"]["elements"])
                        r_suf=fmt["suf"]
                        r_buf=buf
                        break
    return r,r_suf,r_buf
        
#形态键追加
def add_shapekey(ex_config:ExConfig,mod_manager:WciResourceManager):
    if len(mod_manager.shapekeys)==0:
        print("skip shapekey!")
    else:
        #写入命名空间，为了减少ini复杂度，形态键ui和gui都通过命名空间划分到不同的ini
        mod_manager.namespace=ex_config.wci_namespace_uuid
        #生成shapkey ui 不解析里面的key
        secions,keys=IniUtil.parse_ini(shapekey_ui,parse_key=False)
        for section in secions:
            mod_manager.add_section(secions[section])

        res_path=os.path.join(ex_config.resources,"shapekey","res")
        out_res_path=os.path.join(mod_manager.mod_path,FOLDER_NAME.RES)
        
        for file in os.listdir(res_path):
            custome_file=os.path.join(mod_manager.buf_path,FOLDER_NAME.RES,file)
            if os.path.isfile(custome_file):
                #复制自定义的资源文件
                shutil.copyfile(custome_file,os.path.join(out_res_path,file))
            else:
                shutil.copyfile(os.path.join(res_path,file),os.path.join(out_res_path,file))
        
        buf_dicts=ex_config.get_buf_dicts(mod_manager.buf_path,draw=True)
        position_elements_dict,suf,buf=get_position_element_dicts(buf_dicts)
        suf_name=suf.replace("-","").split(".")[0]
        for shapekey in mod_manager.shapekeys:
            obj_name,shapekey_name=shapekey.name.split("_shapekey=")
            ib_hash,sub_alias,item_name=parse_obj_name(obj_name)
            ib_alias = mod_manager.ib_alias_dict[ib_hash]
            shapekey_type="1"
            if mod_manager.game in [Game.BOY,Game.NARAKA]:
                shapekey_type=""
            elif "tangent" in position_elements_dict[ib_hash]:
                shapekey_type="3"
            else:
                if position_elements_dict[ib_hash]["normal"] in ["float3"]:
                    shapekey_type="2"
                elif position_elements_dict[ib_hash]["normal"] in ["float","uint"]:
                    shapekey_type="1"
            hlsl_path=os.path.join(mod_manager.mod_path,FOLDER_NAME.RES,f"Shapekey{shapekey_type}.hlsl")
            if not os.path.isfile(hlsl_path):
                shutil.copyfile(os.path.join(ex_config.resources,"shapekey",f"Shapekey{shapekey_type}.hlsl"),hlsl_path)
            if mod_manager.game in [Game.HSR]:
                #hsr，混合格式，导致必须添加ByteAddressBuffer的 shapekey.hlsl
                # TODO 优化HSR MOD格式
                cs_shapekey_hlsl=os.path.join(mod_manager.mod_path,FOLDER_NAME.RES,f"Shapekey.hlsl")
                if not os.path.isfile(cs_shapekey_hlsl):
                    shutil.copyfile(os.path.join(ex_config.resources,"shapekey",f"Shapekey.hlsl"),cs_shapekey_hlsl)
            shapekey_name=shapekey_name.replace(WCI_BASE_CONST.WCI_SHAPEKEY_PREFIX,"")
            thread_group_count = math.ceil(shapekey.vertex_count/64)
            number_id = mod_manager.get_number_id(shapekey_name,type_key="shapekey")
            key="shapekey"+number_id
            if number_id == "1":
                #与title隔开
                base_y = 60
            else:
                base_y = 25
            shapekey_ini_path = os.path.join(mod_manager.mod_path,key+".ini")
            if not os.path.isfile(shapekey_ini_path):
                icon_path=os.path.join(ex_config.resources,"shapekey","icon.dds")
                custome_icon_path= os.path.join(mod_manager.buf_path,FOLDER_NAME.RES,f"shapekey_icon{number_id}.dds")
                if os.path.isfile(custome_icon_path):
                    #替换为自定义图标
                    icon_path=custome_icon_path
                out_icon_path=os.path.join(out_res_path,f"shapekey_icon{number_id}.dds")
                shutil.copyfile(icon_path,out_icon_path)
                shapekey_ini = get_shapekey_ini(mod_manager.namespace,number_id,key+"_val",key+"_target")
                with open(shapekey_ini_path,"w",encoding="utf-8") as f:
                    for line in shapekey_ini.split("\n"):
                        if len(line)>0 and line.strip()[0] ==";":
                            # 去掉注释
                            continue
                        f.write(line+"\n")
                mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_SHAPEKEY_UI,{"number_id":number_id,"base_y":base_y,})
            base_vertex_index = shapekey.base_start_vertex
            vertex_count  = shapekey.vertex_count
            shapekey_vertex_index = shapekey.start_vertex
            out_slot = "cs-u5"
            resource_name=f"Resource_{ib_alias}_{suf_name}"
            section_names=list(mod_manager.sections.keys())
            for section_name in section_names:
                #资源复制
                if resource_name in section_name:
                    new_suf_name=suf_name+".mix"
                    new_resource_name = resource_name.replace(suf_name,new_suf_name)
                    new_suf=suf.replace(suf_name,new_suf_name)
                    old_section=section_name
                    new_section=section_name.replace(resource_name,new_resource_name)
                    shutil.copyfile(os.path.join(mod_manager.mod_path,FOLDER_NAME.BUFFER,ib_alias+suf),os.path.join(mod_manager.mod_path,FOLDER_NAME.BUFFER,ib_alias+new_suf))  
                    section_info=Section(new_section,dict(mod_manager.sections[old_section].to_dict()))
                    section_info.data=section_info.data.replace("ByteAddressBuffer","RWByteAddressBuffer").replace(suf,new_suf)
                    mod_manager.sections[new_section]=section_info
                    
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_CUSTOMSHADER_SHAPEKEY,
                                          {"ib_hash":ib_hash,
                                           "ib_alias":ib_alias,
                                           "suf_name":suf_name,
                                           "new_suf_name":new_suf_name,
                                           "item_name":item_name,
                                           "thread_group_count":thread_group_count,
                                           "shapekey_type":shapekey_type,
                                           "out_slot":out_slot
                                           })
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_COMMANDLIST_SHAPEKEY,
                                          {"ib_hash":ib_hash,
                                           "ib_alias":ib_alias,
                                           "suf_name":suf_name,
                                           "new_suf_name":new_suf_name,
                                           "sub_alias":sub_alias,
                                           "item_name":item_name,
                                           "shapekey_type":shapekey_type,
                                           "shapekey_name":shapekey_name,
                                           "thread_group_count":thread_group_count,
                                           "weight_var":"$"+key+"_val",
                                           "vertex_count":vertex_count,
                                           "base_vertex_index":base_vertex_index,
                                           "shapekey_vertex_index":shapekey_vertex_index,
                                           "out_slot":out_slot,
                                           })
    return mod_manager