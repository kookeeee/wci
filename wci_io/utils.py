import os
import re
import bpy
import hashlib

from collections import defaultdict
from typing import Dict,List,Tuple,Any


from .constants import DEFAULT_ITEM_NAME
obj_name_pattern=re.compile(r"([a-zA-Z-0-9]{8})-(\d+)\.vb(.*)")


def parse_conditions(expr):
    expr=expr.strip()
    pattern = r'(\w+)==(\w+)(?:\s*(\|\||&&))?'
    matches = list(re.finditer(pattern, expr))
    result = []
    
    for i, match in enumerate(matches):
        var = match.group(1)
        value = match.group(2)
        operator = match.group(3)
        # 如果没有操作符，从中间文本推断
        if not operator and i < len(matches) - 1:
            between = expr[match.end():matches[i + 1].start()]
            op_match = re.search(r'\|\||&&', between)
            operator = op_match.group() if op_match else '&&'
        else:
            operator = operator or '&&'
        result.append((var, value, operator))
    return result

def get_keys_by_toggle(toggle:str)->Dict[str,Dict[str,Any]]:
    for string in ["elseif","elif","if"]:
        toggle = toggle.replace(string,"")
    conditions=parse_conditions(toggle)
    keys:Dict[str,Dict[str,Any]]=defaultdict(dict)
    for condition in conditions:
        var,value,operator=condition
        if "ctrl_" in var:
            is_ctrl=True
            var=var.replace("ctrl_","")
        else:
            is_ctrl=False
        if "alt_" in var:
            is_alt=True
            var=var.replace("alt_","")
        else:
            is_alt=False
        if "shift_" in var:
            is_shift=True
            var=var.replace("shift_","")
        else:
            is_shift=False
        var=var.upper()
        if var not in keys:
            keys[var]={
                "keyboard":var,
                "swap":set([value]),
                "is_alt":is_alt,
                "is_ctrl":is_ctrl,
                "is_shift":is_shift,
                "is_or":operator=="||",
            }
        else:
            keys[var]["swap"].add(value)
            keys[var]["is_or"]=keys[var]["is_or"] or operator=="||"
    return keys

def parse_obj_name(obj_name:str):
    match = obj_name_pattern.match(obj_name.strip())
    if match:
        ib_hash=match.group(1)
        sub_alias=match.group(2)
        item_name=match.group(3)
        if item_name == '':
            item_name=DEFAULT_ITEM_NAME
        else:
            item_name=item_name[1:]
        return ib_hash,sub_alias,item_name
    else:
        return None,None,None
    
def get_normalized_name(ib_hash:str,sub_alias:str,name:str):
    ib_suf=f"{ib_hash}-{sub_alias}"
    if len(name.strip())==0:
        return ib_suf+".vb"
    elif ib_suf in name:
        match = obj_name_pattern.match(name.strip())
        if match:
            return name
        else:
            return name.replace(ib_suf,ib_suf+".vb")
    else:
        return ib_suf+".vb."+name.strip()


# 从视图层LayerCollection集合得到真正的集合。
def get_objects_from_layer_collection(layer_collection:bpy.types.LayerCollection):#默认选中
    obj_name_list=[]
    if not layer_collection.exclude and "skip" not in layer_collection.name:
        for obj in layer_collection.collection.objects:
            if obj.type == "MESH":
                obj_name_list.append(str(obj.name))
        for child in layer_collection.children:
            obj_name_list+=get_objects_from_layer_collection(child)
    return obj_name_list

def collect_objects(buf_path:str,objs:List[bpy.types.Object],collection:bpy.types.LayerCollection=None)->Dict[str,List[bpy.types.Object]]:
    if collection:
        #从集合中收集
        obj_name_list= get_objects_from_layer_collection(collection)
    else:
        #直接用objs
        obj_name_list= [obj.name for obj in objs]
    # 按名称排序
    obj_name_list.sort()
    # 遍历选中的对象
    export_dict:defaultdict[str,List[bpy.types.Object]]=defaultdict(list)
    #生成导出对象字典
    for obj_name in obj_name_list:
        obj=bpy.data.objects[obj_name]
        # 判断对象是否为网格对象
        if hasattr(obj,'hide_get'):
            hide_state=obj.hide_get()
        else:
            hide_state=obj.hide
        ib,sub_alias,_=parse_obj_name(obj.name)
        if obj.type == 'MESH' and (hide_state==False and obj.hide_render==False) and ib:
            if os.path.isfile(os.path.join(buf_path,ib,"analysis.json")):
                export_dict[ib].append(obj)
    #合并到export_dict
    return export_dict
    

def get_file_hash(file_path, hash_algorithm='md5'):
    hash_obj = hashlib.new(hash_algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)

    return str(hash_obj.hexdigest())

SIZE_MAP = {
    # 浮点格式
    "R32G32B32A32_FLOAT": ('<4f', 16, 4),
    "R32G32B32_FLOAT": ('<3f', 12, 3),
    "R32G32_FLOAT": ('<2f', 8, 2),
    "R32_FLOAT": ('<f', 4, 1),

    "R16G16B16A16_FLOAT": ("<4e", 8, 4),
    "R16G16B16_FLOAT": ("<3e", 6, 3),
    "R16G16_FLOAT": ('<2e', 4, 2),
    "R16_FLOAT": ('<e', 2, 1),
    
    # 无符号整数格式
    "R32G32B32A32_UINT": ('<4I', 16, 4),
    "R32G32B32_UINT": ('<3I', 12, 3),
    "R32G32_UINT": ('<2I', 8, 2),
    "R32_UINT": ('<I', 4, 1),
    "R16G16B16A16_UINT": ('<4H', 8, 4),
    "R16G16B16_UINT": ('<3H', 6, 3),
    "R16G16_UINT": ('<2H', 4, 2),
    "R16_UINT": ('<H', 2, 1),
    "R8G8B8A8_UINT": ('<4B', 4, 4),
    "R8G8B8_UINT": ('<3B', 3, 3),
    "R8G8_UINT": ('<2B', 2, 2),
    "R8_UINT": ('<B', 1, 1),
    # 有符号整数格式
    "R32G32B32A32_SINT": ('<4i', 16, 4),
    "R32G32B32_SINT": ('<3i', 12, 3),
    "R32G32_SINT": ('<2i', 8, 2),
    "R32_SINT": ('<i', 4, 1),
    "R16G16B16A16_SINT": ('<4h', 8, 4),
    "R16G16B16_SINT": ('<3h', 6, 3),
    "R16G16_SINT": ('<2h', 4, 2),
    "R16_SINT": ('<h', 2, 1),
    "R8G8B8A8_SINT": ('<4b', 4, 4),
    "R8G8B8_SINT": ('<3b', 3, 3),
    "R8G8_SINT": ('<2b', 2, 2),
    "R8_SINT": ('<b', 1, 1),

    # UNORM 整数存储，浮点取值
    "R16G16B16A16_UNORM": ('<4H', 8, 4),
    "R16G16B16_UNORM": ('<3H', 6, 3),
    "R16G16_UNORM": ('<2H', 4, 2),
    "R16_UNORM": ('<H', 2, 1),

    "B8G8R8A8_UNORM" : ('<4B', 4, 4), #鸣潮顶点色
    "R8G8B8A8_UNORM": ('<4B', 4, 4),
    "R8G8B8_UNORM": ('<3B', 3, 3),
    "R8G8_UNORM": ('<2B', 2, 2),
    "R8_UNORM": ('<B', 1, 1),

    # SNORM 整数存储，浮点取值
    "R16G16B16A16_SNORM": ('<4h', 8, 4),
    "R16G16B16_SNORM": ('<3h', 6, 3),
    "R16G16_SNORM": ('<2h', 4, 2),
    "R16_SNORM": ('<h', 2, 1),

    "R8G8B8A8_SNORM": ('<4b', 4, 4),
    "R8G8B8_SNORM": ('<3b', 3, 3),
    "R8G8_SNORM": ('<2b', 2, 2),
    "R8_SNORM": ('<b', 1, 1),
    # ib 索引格式
    "DXGI_FORMAT_R16_UINT": ('<H', 2, 1),
    "DXGI_FORMAT_R32_UINT": ('<I', 4, 1),
    "R16_UINT": ('<H', 2, 1),
    "R32_UINT": ('<I', 4, 1),
}

def format_size(fmt: str) -> Tuple[str, int, int]:
    """
    返回编码打包格式、字节长度、打包所需值的个数
    
    :param fmt: DXGI的编码格式
    """
    return SIZE_MAP[fmt]


if __name__=="__main__":
    print(parse_obj_name("1234abcd-1.vb"))
    print(parse_obj_name(" 12345678-1.vb"))
    print(parse_obj_name(" 12345678-1.vb.   001"))
    print(parse_obj_name("12345678-1.vb.test1"))

