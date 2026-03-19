import re
import os
import struct
from collections import defaultdict, OrderedDict
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any, Optional, Union

from ..utils import format_size
from ..constants import Game

from .data import FileCollector

def conv_tex(path: str, dds_file: str, conv_type: str = "jpg",
             dxgi_format: str = "BC7_UNORM_SRGB", mitmap: int = 1) -> None:
    """
    调用texconv.exe转换纹理格式。

    Args:
        path: 纹理所在目录路径。
        dds_file: 要转换的DDS文件名。
        conv_type: 目标格式，如"jpg"或"dds"。
        dxgi_format: 当conv_type="dds"时使用的DXGI格式。
        mitmap: 生成的mipmap级别数。
    """
    import subprocess
    try:
        file = os.path.join(path, dds_file)
        texconv_path = os.path.join(os.path.split(os.path.abspath(__file__))[0], "texconv.exe")
        command = f'  -o "{path}" -y "{file}"'
        if conv_type == "dds":
            command = f" -m {mitmap} -f {dxgi_format} " + command
        else:
            command = f" -ft {conv_type}" + command
        subprocess.run(
            texconv_path + command,
            check=True,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _get_dds_size(f) -> Optional[Tuple[int, int]]:
    """
    从打开的DDS文件中读取图像尺寸。

    Args:
        f: 以二进制模式打开的文件对象。

    Returns:
        (width, height) 元组，如果读取失败则返回None。
    """
    if f.read(4) != b'DDS ':
        return None
    # 跳过头部固定字段，读取高度和宽度
    f.seek(12)  # 跳过: 4字节魔数 + 4字节dwSize + 4字节dwFlags
    height, width = struct.unpack('<II', f.read(8))
    return width, height


def _get_jpg_size(f) -> Optional[Tuple[int, int]]:
    """
    从打开的JPEG文件中读取图像尺寸。

    Args:
        f: 以二进制模式打开的文件对象。

    Returns:
        (width, height) 元组，如果读取失败则返回None。
    """
    # JPEG以0xFFD8开始
    if f.read(2) != b'\xff\xd8':
        return None

    while True:
        marker = f.read(2)
        if len(marker) < 2:
            return None
        if marker[0] != 0xFF:
            return None
        marker_type = marker[1]

        # 跳过填充字节
        while marker_type == 0xFF:
            marker_type = f.read(1)[0]

        # SOF0, SOF1, SOF2 包含图像尺寸
        if 0xC0 <= marker_type <= 0xC3 or 0xC5 <= marker_type <= 0xC7 or 0xC9 <= marker_type <= 0xCB or 0xCD <= marker_type <= 0xCF:
            length = struct.unpack('>H', f.read(2))[0]
            f.read(1)  # 跳过精度
            height, width = struct.unpack('>HH', f.read(4))
            return width, height
        elif marker_type == 0xD9 or marker_type == 0xDA:  # EOI或SOS
            return None
        else:
            length = struct.unpack('>H', f.read(2))[0]
            f.read(length - 2)  # 跳过其他段

def get_image_size(file_path: str) -> Tuple[int, int]:
    """
    获取图片文件的分辨率（支持DDS和JPG）。

    Args:
        file_path: 图片文件路径。

    Returns:
        (width, height) 元组，如果无法读取则返回 (0, 0)。
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            f.seek(0)
            if header.startswith(b'DDS '):
                size = _get_dds_size(f)
                if size:
                    return size
            elif header.startswith(b'\xff\xd8'):
                size = _get_jpg_size(f)
                if size:
                    return size
            else:
                print(f"不支持的格式: {file_path}")
                return 0, 0
    except Exception as e:
        print(f"读取失败 {file_path}: {e}")
        return 0, 0
    
def write_ib_binary(metadata: dict, output_file: str) -> int:
    """
    将索引数据写入二进制文件。

    Args:
        metadata: 包含索引列表和格式信息的字典。
        output_file: 输出二进制文件路径。

    Returns:
        实际写入的文件大小（字节数）。
    """
    format_str = metadata["format"].upper()
    indices = metadata["indices"]

    pack_format, index_size, val_size = format_size(format_str)

    with open(output_file, 'wb') as f:
        for index in indices:
            if format_str == "DXGI_FORMAT_R16_UINT" and index > 65535:
                print(f"索引值 {index} 超出16位范围，将被截断")
                index = index & 0xFFFF
            packed = struct.pack(pack_format, index)
            f.write(packed)

    actual_size = os.path.getsize(output_file)
    return actual_size

def get_search_buf(extract_path: str, buf_dict: dict) -> list:
    """
    确定哪些缓冲区还需要进一步搜索。

    Args:
        extract_path: 提取目录。
        buf_dict: 缓冲区配置。

    Returns:
        需要搜索的缓冲区名称列表。
    """
    search_buf = []
    for buf in buf_dict:
        if buf == "ib":
            continue
        search = False
        if len(buf_dict[buf]["fmts"]) > 0:
            for fmt in buf_dict[buf]["fmts"]:
                if "file" in fmt:
                    if not os.path.isfile(os.path.join(extract_path, fmt["file"])):
                        search = True
                else:
                    search = True
        else:
            search = True
        if search:
            search_buf.append(buf)
    search_buf.sort()
    return search_buf


def parse_ib_txt_file(filename: str, read: bool = True) -> dict:
    """
    解析3DMigoto索引缓冲区文本文件。

    Args:
        filename: 要解析的文本文件路径。
        read: 是否读取索引数据（若为False，只解析头部）。

    Returns:
        包含头部元数据和索引列表的字典。
    """
    metadata = {
        "byte_offset": 0,
        "first_index": 0,
        "index_count": -1,
        "topology": "",
        "format": "",
        "indices": [],
    }

    patterns = {
        "byte_offset": r"byte offset: (\d+)",
        "first_index": r"first index: (\d+)",
        "index_count": r"index count: (\d+)",
        "topology": r"topology: (\w+)",
        "format": r"format: (\w+)",
    }
    line_pattern = re.compile(r"^\d+ \d+ \d+$")
    line_pattern1 = re.compile(r"^\d+$")
    read_count = 0
    read_meta = False
    with open(filename, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not read_meta:
            for key, pattern in patterns.items():
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    if key in ["byte_offset", "first_index", "index_count"]:
                        value = int(value)
                    metadata[key] = value
                    break

        if read_meta and read_count >= metadata["index_count"]:
            break

        # 检查是否到达索引数据部分
        if read:
            if line_pattern.match(line):
                read_meta = True
                val1, val2, val3 = line.split(" ")
                metadata["indices"].append(int(val1))
                metadata["indices"].append(int(val2))
                metadata["indices"].append(int(val3))
                read_count += 3
            elif line_pattern1.match(line):
                read_meta = True
                val1 = line.strip()
                read_count += 1
                metadata["indices"].append(int(val1))

    return metadata


def parse_buf_txt_file(filename: str, buf: str, read: bool = True) -> dict:
    """
    解析3DMigoto顶点缓冲区文本文件。

    Args:
        filename: 要解析的文本文件路径。
        buf: 缓冲区名称（如"vb0"）。
        read: 是否读取顶点数据（若为False，只解析头部并读取第一个顶点）。

    Returns:
        包含步长、顶点数、元素定义和顶点数据的字典。
    """
    metadata = {
        "stride": 0,
        "byte offset":0,
        "first_vertex": 0,
        "vertex_count": 0,
        "topology": "",
        "valid_alias_semantics": [],
        "elements": [],
        "vertex_data": defaultdict(dict),
    }
    offset_alias_name_dict = OrderedDict()
    current_section = None
    buf_slot = re.compile(r"[a-zA-Z\-]*(\d+)").match(buf).group(1)
    element_pattern = re.compile(r"element\[(\d+)\]:")
    offset_pattern = re.compile(buf + r"\[(\d+)\]\+(\d+)([A-Z0-9 ]*):")
    valid_alias_semantic_names = set()

    with open(filename, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line == "vertex-data:":
            current_section = "vertex-data"
            continue

        # 解析元数据
        if line.startswith("stride:"):
            metadata["stride"] = int(line.split(":")[1].strip())
        elif line.startswith("first vertex:"):
            metadata["first_vertex"] = int(line.split(":")[1].strip())
        elif line.startswith("vertex count:"):
            metadata["vertex_count"] = int(line.split(":")[1].split()[0].strip())
        elif line.startswith("topology:"):
            metadata["topology"] = line.split(":")[1].strip()
        elif line.startswith("byte offset:"):
            metadata["byte offset"] = int(line.split(":")[1].strip())

        # 解析元素定义
        elif element_pattern.match(line):
            current_section = "element"
            match = element_pattern.match(line)
            element_idx = int(match.group(1))
            element = {"index": element_idx}
            metadata["elements"].append(element)

        if current_section == "element" and "SemanticName:" in line:
            name = line.split(":")[1].strip()
            metadata["elements"][-1]["SemanticName"] = name
        elif current_section == "element" and "InputSlot" in line and "InputSlotClass" not in line:
            metadata["elements"][-1]["InputSlot"] = line.split(":")[1].strip()
        elif current_section == "element" and "SemanticIndex:" in line:
            metadata["elements"][-1]["SemanticIndex"] = int(line.split(":")[1].strip())
        elif current_section == "element" and "Format:" in line:
            metadata["elements"][-1]["Format"] = line.split(":")[1].strip()
        elif current_section == "element" and "AlignedByteOffset:" in line:
            metadata["elements"][-1]["AlignedByteOffset"] = int(line.split(":")[1].strip())

        # 解析顶点数据
        elif current_section == "vertex-data" and f"{buf}[" in line:
            match = offset_pattern.search(line)
            if match:
                vertex_idx = int(match.group(1))
                offset = int(match.group(2))
                alias_semantic_name = match.group(3).strip()
                if offset in metadata["vertex_data"][vertex_idx]:
                    continue
                else:
                    offset_alias_name_dict[offset] = alias_semantic_name
                    valid_alias_semantic_names.add(alias_semantic_name)

                # 非读取模式下只解析第一个顶点
                if not read and vertex_idx > 0:
                    break

                parts = line.split(":", 1)
                if len(parts) > 1:
                    data_type = parts[0].split()[-1].strip()
                    values_str = parts[1].strip()
                    values = [val.strip() for val in values_str.split(",")]
                    metadata["vertex_data"][vertex_idx][offset] = {
                        "type": data_type,
                        "values": values,
                    }

    # 清理元素列表，只保留存在的语义
    elements = list(metadata["elements"])
    new_elements = []
    for element in elements:
        for offset in offset_alias_name_dict:
            alias_semantic_name = offset_alias_name_dict[offset]
            if (element["AlignedByteOffset"] == int(offset) and
                    element["SemanticName"] in alias_semantic_name and
                    element["InputSlot"] == buf_slot):
                element["AliasSemanticName"] = alias_semantic_name
                new_elements.append(element)
    metadata["elements"] = new_elements
    metadata["valid_alias_semantics"] = list(valid_alias_semantic_names)
    return metadata

def rename_elements(game,extract_path,buf_dict: dict) -> dict:
    """
    重命名元素中的语义别名，确保同一语义多次出现时添加数字后缀。
    重命名WuWa语义，确保能正确导入导出
    Args:
        buf_dict: 缓冲区配置字典。

    Returns:
        更新后的buf_dict。
    """
    elements_dict = {}
    bufs = list(buf_dict.keys())
    bufs.sort()
    for buf in bufs:
        if "fmts" in buf_dict[buf]:
            #先清理没有file的fmt
            fmts=buf_dict[buf]["fmts"]
            new_fmts=[]
            for i in range(0,len(fmts)):
                if "file" in fmts[i] and os.path.join(extract_path,fmts[i]["file"]):
                    if game in [Game.WUWA]:
                        wuwa_attributes={
                            "ATTRIBUTE":"POSITION",
                            "ATTRIBUTE1":"NORMAL",
                            "ATTRIBUTE2":"TANGENT",
                            "ATTRIBUTE5":"TEXCOORD",
                            "ATTRIBUTE6":"TEXCOORD3",
                            #TODO 暂时还是存储到UV，鸣潮的color1是R16G16格式，无法用通用的解析
                            #"ATTRIBUTE6":"COLOR1",
                            "ATTRIBUTE7":"TEXCOORD1",
                            "ATTRIBUTE8":"TEXCOORD2",
                            "ATTRIBUTE3":"BLENDINDICES",
                            "ATTRIBUTE14":"BLENDINDICES1",
                            "ATTRIBUTE4":"BLENDWEIGHTS",
                            "ATTRIBUTE15":"BLENDWEIGHTS1",
                            "ATTRIBUTE9":"SHAPEKEY",
                            "ATTRIBUTE10":"SHAPEKEY1",
                            "ATTRIBUTE11":"SNORMAL",
                            "ATTRIBUTE13":"COLOR",
                        }
                        #语义重命名
                        suf=buf_dict[buf]["suf"]
                        for element in fmts[i]["metadata"]["elements"]:
                            attribue_name= element["AliasSemanticName"]
                            if attribue_name in wuwa_attributes:
                                element["SemanticName"]=wuwa_attributes[attribue_name]
                                element["AliasSemanticName"]=wuwa_attributes[attribue_name]
                    new_fmts.append(fmts[i])
            buf_dict[buf]["fmts"]=new_fmts
            for item in buf_dict[buf]["fmts"]:
                fmt = item["metadata"]
                if "valid_alias_semantics" in fmt:
                    del fmt["valid_alias_semantics"]
                fmt["semantics"] = []
                new_element = []
                for element in fmt["elements"]:
                    sem_name = element["SemanticName"]
                    alias = element["AliasSemanticName"]
                    if sem_name in elements_dict:
                        elements_dict[sem_name].append(alias)
                        elements_dict[sem_name].sort()
                        index = elements_dict[sem_name].index(alias)
                        if index == 0:
                            continue
                        else:
                            element["AliasSemanticName"] = sem_name + str(index)
                            fmt["semantics"].append(element["AliasSemanticName"])
                            new_element.append(element)
                    else:
                        elements_dict[sem_name] = [alias]
                        element["AliasSemanticName"] = sem_name
                        fmt["semantics"].append(element["AliasSemanticName"])
                        new_element.append(element)
                fmt["elements"] = list(new_element)
                if len(new_element) == 0:
                    keys = list(item.keys())
                    for key in keys:
                        del item[key]
    return buf_dict


def analysis_frame(fc: FileCollector) -> List[Tuple[str, str]]:
    """
    分析整个帧转储，找出所有完整的IB及其关联的缓冲区。

    Args:
        fc: 文件收集器实例。

    Returns:
        包含 (ib哈希, ib别名) 的元组列表。
    """
    ib_vs_dict = defaultdict(set)
    match_slots = fc.slots

    # 根据不同游戏移除不需要检查的槽位
    if fc.game in [Game.ZZZ, Game.GI, Game.HSR, Game.HI3]:
        if "vb2" in match_slots:
            match_slots.remove("vb2")
    if fc.game in [Game.BOY, Game.NARAKA,Game.HSR]:
        for slot in list(fc.slots):
            if 'cs-t' in slot:
                match_slots.remove(slot)
    for ib in fc.IndexBufferIndices:
        bufs = set()
        vs = set()
        indices = fc.IndexBufferIndices[ib]
        for index in indices:
            for file in fc.caches[index]:
                buf = file[7:].split("=")[0]
                if buf in fc.slots:
                    bufs.add(buf)
                if buf == "ib":
                    vs_hash = file.split("vs=")[1][:16]
                    vs.add(vs_hash)
        if len(bufs) == len(match_slots):
            ib_vs_dict[ib] = vs

    return [(key, key) for key in ib_vs_dict.keys()]

def update_buf_fmt_info(buf_dict: dict, buf: str, hash_val: str, buf_file: str,
                        buf_txt_file: str, extract_path: str) -> dict:
    """
    更新缓冲区格式信息，将解析出的顶点数据与现有格式匹配或追加。

    Args:
        buf_dict: 缓冲区配置字典。
        buf: 缓冲区名称。
        hash_val: 缓冲区的哈希值。
        buf_file: 对应的二进制缓冲区文件路径。
        buf_txt_file: 对应的文本描述文件路径。
        extract_path: 输出目录。

    Returns:
        更新后的buf_dict。
    """

    def extract_buf(buf_file: str, extract_buf_file: str, stride: int, vertex_count: int,byte_offset:int = 0):
        """从原始缓冲区文件中提取指定长度的数据并写入新文件。"""
        length = stride * vertex_count
        with open(buf_file, "rb") as f:
            bdata = f.read()
        bdata = bdata[byte_offset:byte_offset+length]
        with open(extract_buf_file, "wb") as f:
            f.write(bdata)

    match = False #通过语义和hash匹配没有结果的，直接默认为新的格式
    buf_metadata = parse_buf_txt_file(buf_txt_file, buf, read=True)
    if "vertex_data" not in buf_metadata\
        or buf_metadata["vertex_count"] != buf_dict["ib"]["vertex_count"] \
        or buf_metadata["vertex_count"] != len(buf_metadata["vertex_data"]) \
        or len(buf_metadata["elements"]) <= 0:
        #没有顶点数据，或者顶点数不一致，或者没有语义数据，不用更新
        return buf_dict
    for i in range(0, len(buf_dict[buf]["fmts"])):
        fmt = buf_dict[buf]["fmts"][i]
        if fmt["hash"] == hash_val:
            # hash一致
            match = True
            if len(buf_metadata["valid_alias_semantics"]) > len(fmt["metadata"]["valid_alias_semantics"]):
                extract_buf_file = os.path.join(extract_path, fmt["file"])
                extract_buf(buf_file, extract_buf_file, buf_metadata["stride"], buf_metadata["vertex_count"],byte_offset=buf_metadata["byte offset"])
                new_fmt = {
                    "hash": hash_val,
                    "metadata": buf_metadata,
                    "file": fmt["file"],
                    "suf": fmt["suf"],
                }
                del new_fmt["metadata"]["vertex_data"]
                buf_dict[buf]["fmts"][i] = new_fmt

        else:
            # 哈希不同，比较语义集合
            same_semantics = set(buf_metadata["valid_alias_semantics"]) & set(fmt["metadata"]["valid_alias_semantics"])
            if len(set(buf_metadata["valid_alias_semantics"]) - set(fmt["metadata"]["valid_alias_semantics"])) == 0:
                #没有重合的语义，说明是新的格式
                match = True
                if buf_metadata["topology"] == "pointlist":
                    extract_buf_file = os.path.join(extract_path, fmt["file"])
                    extract_buf(buf_file, extract_buf_file, buf_metadata["stride"], buf_metadata["vertex_count"],byte_offset=buf_metadata["byte offset"])
                    new_fmt = {
                        "hash": hash_val,
                        "metadata": buf_metadata,
                        "file": fmt["file"],
                        "suf": fmt["suf"],
                    }
                    del new_fmt["metadata"]["vertex_data"]
                    buf_dict[buf]["fmts"][i] = new_fmt
            elif len(same_semantics) > 0:
                # 有重合的语义，说明是旧的格式，但是语义集合有新增
                if len(buf_metadata["valid_alias_semantics"]) > len(fmt["metadata"]["valid_alias_semantics"]):
                    match = True
                    extract_buf_file = os.path.join(extract_path, fmt["file"])
                    extract_buf(buf_file, extract_buf_file, buf_metadata["stride"], buf_metadata["vertex_count"],byte_offset=buf_metadata["byte offset"])
                    new_fmt = {
                        "hash": hash_val,
                        "metadata": buf_metadata,
                        "file": fmt["file"],
                        "suf": fmt["suf"],
                    }
                    if "vertex_data" in new_fmt["metadata"]:
                        del new_fmt["metadata"]["vertex_data"]
                    buf_dict[buf]["fmts"][i] = new_fmt
    if not match and len(buf_metadata["elements"]) > 0:
        fmt_number = len(buf_dict[buf]["fmts"])
        if fmt_number == 0:
            suf = buf_dict[buf]["suf"]
        else:
            #奇怪的命名
            suf = "-" + str(fmt_number) + buf_dict[buf]["suf"]

        extract_buf_file = os.path.join(extract_path, buf_dict["ib"]["hash"] + suf)
        extract_buf(buf_file, extract_buf_file, buf_metadata["stride"], buf_metadata["vertex_count"],byte_offset=buf_metadata["byte offset"])

        fmt = {
            "metadata": buf_metadata,
            "hash": hash_val,
            "file": os.path.split(extract_buf_file)[1],
            "suf": suf,
        }
        del fmt["metadata"]["vertex_data"]
        print("find file:", buf_txt_file)
        buf_dict[buf]["fmts"].append(fmt)

    return buf_dict