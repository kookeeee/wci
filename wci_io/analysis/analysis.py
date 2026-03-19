import os
import shutil
import json
from collections import defaultdict, OrderedDict
from typing import Tuple, List, Dict, Any
from copy import deepcopy

from ..constants import Game
from ..utils import get_file_hash

from .data import FileCollector,game_buf_info
from .utils import write_ib_binary,update_buf_fmt_info,parse_ib_txt_file,rename_elements,analysis_frame,get_search_buf,parse_buf_txt_file
from .analysis_slot import analysis_slot

def analysis_ib(buf_dict: Dict[str,Any], fc: FileCollector, extract_path: str) -> Tuple[list, dict, int]:
    """
    分析索引缓冲区，提取索引数据并生成二进制IB文件。

    Args:
        buf_dict: 缓冲区配置字典。
        fc: 已初始化的FileCollector实例。
        extract_path: 提取文件的输出目录。

    Returns:
        (indices列表, match_info字典, 顶点总数)
    """
    #  存储所有索引
    indices = set()
    match_info = OrderedDict()
    file_hash_dict={}
    ib_hash = buf_dict["ib"]["hash"]
    vertex_indices = []

    for file in fc.IndexBufferFiles[ib_hash]:
        if file[-3:] == "txt":
            index = file[0:6]
            indices.add(index)
            ib_txt_file_path = os.path.join(fc.dumps_path, file)
            file_hash=get_file_hash(ib_txt_file_path)
            if file_hash  in file_hash_dict:
                metadata = file_hash_dict[file_hash]
            else:
                metadata = parse_ib_txt_file(ib_txt_file_path, read=True)
                metadata["vertex_count"] = len(set(metadata["indices"]))
                # 顶点总数
                file_hash_dict[file_hash] = metadata
            key = str(metadata['first_index']) + " " + str(metadata['index_count'])
            if key in match_info:
                match_info[key]["indices"][index] = file
                if match_info[key]["metadata"]["vertex_count"] < metadata["vertex_count"]:
                    match_info[key]["file"] = file
                    match_info[key]["metadata"] = metadata
                    vertex_indices += metadata["indices"]
            else:
                match_info[key] = {
                    "indices": {index: file},
                    "file": file,
                    "metadata": metadata,
                }
                vertex_indices += metadata["indices"]
    # 移除无效的key
    keys = list(match_info.keys())
    for key in keys:
        if key.split(" ")[1]=="-1" or key.split(" ")[1]=="0":
            del match_info[key]

    keys=sorted(keys,key=lambda x: int(x.split(" ")[0]))
    key_alias_name_dict = dict(zip(keys, [str(i) for i in range(1, len(keys) + 1)]))
    vertex_indices = list(set(vertex_indices))
    vertex_indices.sort()
    if len(vertex_indices) > 0:
        vertex_count = vertex_indices[-1] + 1
        for key in match_info:
            alias = key_alias_name_dict[key]
            ib_txt = os.path.join(fc.dumps_path, match_info[key]["file"])
            extract_ib_buf = os.path.join(extract_path, ib_hash + f"-{alias}" + buf_dict["ib"]["suf"])
            write_ib_binary(match_info[key]["metadata"], extract_ib_buf)
            match_info[key]["alias"] = alias
            match_info[key]["file"] = os.path.split(extract_ib_buf)[1]
            del match_info[key]["metadata"]["indices"]

            extract_ib_txt = os.path.join(extract_path, ib_hash + f"-{alias}" + ".txt")
            shutil.copyfile(ib_txt, extract_ib_txt)
        indices_list = list(indices)
        indices_list.sort(key=lambda x : int(x))
        return indices_list, match_info, vertex_count
    else:
        return list(indices), match_info, 0


def analysis_buf(buf_dict: dict, fc: FileCollector, extract_path: str) -> Tuple[dict, int]:
    """
    分析所有顶点缓冲区，匹配并提取与IB顶点数一致的文件。

    Args:
        buf_dict: 缓冲区配置字典。
        fc: 文件收集器实例。
        extract_path: 提取目录。

    Returns:
        (更新后的buf_dict, 成功找到的缓冲区数量)
    """
    search_buf = get_search_buf(extract_path, buf_dict)
    buf_count = 0
    search_finshed=False

    vertex_count = buf_dict["ib"]["vertex_count"]
    if vertex_count in fc.deduped_dict:
        layouts=list(fc.deduped_dict[vertex_count].keys())
        if "binary" in layouts: #移除特殊的layout
            layouts.remove("binary")
        topologys=list(set([fc.topologyCaches[layout]  for layout in layouts]))
        if len(topologys)==1:
            if len(layouts)>0:
                #多种布局的三角面拓扑
                find_buf_file_hash_dict:Dict[str,str]={}
                indices=sorted(buf_dict["ib"]["indices"],key=lambda x:int(x))
                indices.reverse()
                #逆序，索引越往后缓冲区文件越新，越符合新的格式
                search_buf = get_search_buf(extract_path, buf_dict)
                for index in indices:
                    for file in fc.caches[index]:
                        buf = file[7:].split("=")[0]
                        if buf in search_buf and file[-4:] == ".txt":
                            buf_txt_file = os.path.join(fc.dumps_path, file)
                            #缓冲区文件引用了同一个，没办法区分，以txt文件为准
                            file_hash = get_file_hash(buf_txt_file)
                            if file_hash in find_buf_file_hash_dict:
                                continue
                            hash_val = file.split(buf + "=")[1][0:8]
                            buf_file = os.path.join(fc.dumps_path, file[0:-4]+'.buf')
                            find_buf_file_hash_dict[file_hash]=buf_txt_file
                            buf_dict = update_buf_fmt_info(buf_dict, buf, hash_val, buf_file, buf_txt_file, extract_path)
            #判断是否结束查找 需要找到position数据才能结束 #为cs类型的渲染方式准备
            for buf in buf_dict:
                if buf!="ib" and len(buf_dict[buf]["fmts"])>0:
                    for fmt in buf_dict[buf]["fmts"]:
                        if "file" in fmt["metadata"]:
                            for element in fmt["metadata"]["elements"]:
                                if "POSITION" in element["SemanticName"]:
                                    search_finshed=True
                                    break
        elif len(topologys)>1:
            #多种拓扑，先找三角面拓扑，再找非三角面关联索引拓扑
            indices=buf_dict["ib"]["indices"]
            hashs=set() #ib 索引中包含的hash
            for index in indices:
                for file in fc.caches[index]:
                    buf = file[7:].split("=")[0]
                    if buf in search_buf and file[-4:] == ".txt":
                        hash_val = file.split(buf + "=")[1][0:8]
                        hashs.add(hash_val)
            #找非"trianglelist"的hash
            n_hashs=set()
            for layout in layouts:
                for n_dedupedfile in fc.deduped_dict[vertex_count][layout]:
                    if n_dedupedfile.topology != "trianglelist":
                        n_hashs.add(n_dedupedfile.hash)
            pointlist_hashs=hashs & n_hashs #与ib关联hash关联的非三角面拓扑缓冲区hash
            hash_indices = []
            for hash in pointlist_hashs:
                hash_indices+=fc.hashIndices[hash] #缓冲区索引，各种拓扑都会包含
            hash_indices=list(set(hash_indices))
            hash_indices.sort()
            if len(hash_indices)<=0 \
                and len(n_hashs)<=len(search_buf) \
                and len(hashs)<=len(search_buf) \
                and len(n_hashs)>0 and len(hashs)>0:
                # 各种拓扑的缓冲区文件都存在，
                for layout in layouts:
                    for dedupedfile in fc.deduped_dict[vertex_count][layout]:
                        buf=dedupedfile.buf
                        if buf in search_buf:
                            hash_val = dedupedfile.hash
                            filename = dedupedfile.file
                            buf_file = os.path.join(fc.dumps_path,"deduped", hash_val + ".buf")
                            buf_txt_file = os.path.join(fc.dumps_path,"deduped", filename)
                            buf_dict = update_buf_fmt_info(buf_dict, buf, hash_val, buf_file, buf_txt_file, extract_path)
            else:
                for index in hash_indices:
                    for file in fc.caches[index]:
                        search_buf = get_search_buf(extract_path, buf_dict)
                        buf = file[7:].split("=")[0]
                        if buf in search_buf and file[-4:] == ".txt":
                            hash_val = file.split(buf + "=")[1][0:8] 
                            buf_file = os.path.join(fc.dumps_path, file[0:-4]+'.buf')
                            buf_txt_file = os.path.join(fc.dumps_path, file)
                            buf_dict = update_buf_fmt_info(buf_dict, buf, hash_val, buf_file, buf_txt_file, extract_path)            

    # 更新待搜索列表
    search_buf = get_search_buf(extract_path, buf_dict)
    if len(search_buf) > 0 and not search_finshed:
        search_result = None
        # 优先找拓扑类型为pointlist的IB关联的缓冲区
        for index in fc.pointlistIndices:
            for file1 in fc.caches[index]:
                buf = file1[7:].split("=")[0]
                if buf in search_buf and file1[-4:] == ".txt":
                    buf_metadata = parse_buf_txt_file(os.path.join(fc.dumps_path, file1), buf, read=False)
                    if buf_metadata["vertex_count"] == buf_dict["ib"]["vertex_count"]:
                        search_result = index
                        break
            if search_result is not None:
                break
            
        # 找到匹配的索引后，处理该索引下的所有文件
        if search_result:
            print("match pointlist index", search_result)
            for file in fc.caches[search_result]:
                buf = file[7:].split("=")[0]
                if buf in search_buf:
                    hash_val = file.split(buf + "=")[1][0:8]
                    buf_file = os.path.join(fc.dumps_path, file[0:-3] + "buf")
                    buf_txt_file = os.path.join(fc.dumps_path, file[0:-3] + "txt")
                    if len(buf_dict[buf]["fmts"]) == 0 and file[-4:] == ".txt":
                        buf_metadata = parse_buf_txt_file(os.path.join(fc.dumps_path, file), buf)
                        if (buf_metadata["topology"] in ["pointlist", "3_control_point_patchlist"] and
                                buf_metadata["vertex_count"] == buf_dict["ib"]["vertex_count"] and
                                buf_metadata["vertex_count"] == len(buf_metadata["vertex_data"])):
                            buf_dict = update_buf_fmt_info(buf_dict, buf, hash_val, buf_file, buf_txt_file, extract_path)
                    elif len(buf_dict[buf]["fmts"]) > 0 and file[-4:] == ".buf":
                        for fmt in buf_dict[buf]["fmts"]:
                            stride = fmt["metadata"]["stride"]
                            file_size = os.path.getsize(os.path.join(fc.dumps_path, file))
                            buf_vertex_count = file_size / stride
                            if buf_vertex_count == buf_dict["ib"]["vertex_count"]:
                                hash_val = file.split(buf + "=")[1][0:8]
                                fmt["metadata"]["vertex_count"] = buf_vertex_count
                                fmt["hash"] = hash_val
                                # 复制文件
                                shutil.copyfile(
                                    os.path.join(fc.dumps_path, file),
                                    os.path.join(extract_path, fmt["file"])
                                )

    # 若仍未找到，进行全局查找
    search_buf = get_search_buf(extract_path, buf_dict)
    if len(search_buf) > 0 and not search_finshed:
        for buf in search_buf:
            for file in fc.caches[buf]:
                buf_file = os.path.join(fc.dumps_path, file[0:-3] + "buf")
                buf_txt_file = os.path.join(fc.dumps_path, file[0:-3] + "txt")
                if len(buf_dict[buf]["fmts"]) == 0 and file[-4:] == ".txt":
                    hash_val = file.split(buf + "=")[1][0:8]
                    buf_dict = update_buf_fmt_info(buf_dict, buf, hash_val, buf_file, buf_txt_file, extract_path)
                elif len(buf_dict[buf]["fmts"]) > 0 and file[-4:] == ".buf":
                    for fmt in buf_dict[buf]["fmts"]:
                        stride = fmt["metadata"]["stride"]
                        file_size = os.path.getsize(os.path.join(fc.dumps_path, file))
                        buf_vertex_count = file_size // stride
                        if buf_vertex_count == buf_dict["ib"]["vertex_count"]:
                            print("search bin:",file)
                            hash_val = file.split(buf + "=")[1][0:8]
                            buf_file_name = buf_dict["ib"]["hash"] + buf_dict[buf]["suf"]
                            fmt["metadata"]["vertex_count"] = buf_vertex_count
                            fmt["hash"] = hash_val
                            fmt["file"] = buf_file_name
                            shutil.copyfile(
                                os.path.join(fc.dumps_path, file),
                                os.path.join(extract_path, buf_file_name)
                            )
    # 统计已找到的缓冲区数量
    for buf in buf_dict:
        if buf == "ib":
            continue
        find = False
        if len(buf_dict[buf]["fmts"]) > 0:
            for fmt in buf_dict[buf]["fmts"]:
                if "file" in fmt and os.path.isfile(os.path.join(extract_path, fmt["file"])):
                    find = True
                    break
        if find:
            buf_count += 1

    return buf_dict, buf_count


def dumps_by_ib(buf_dict:Dict[str,Any],output_path: str, ib: str, ib_alias: str,
                         fc: FileCollector, min_image_size: int = 1024) -> Tuple[str, str]:
    """
    针对单个IB进行分析，提取相关数据并生成analysis.json。

    Args:
        output_path: 输出根目录。
        ib: IB哈希值。
        ib_alias: IB别名。
        fc: 文件收集器实例。
        min_image_size: 最小纹理尺寸。

    Returns:
        (生成的analysis.json文件路径, 状态消息)
    """
    ib_path = os.path.join(output_path, ib)
    if not os.path.isdir(ib_path):
        os.makedirs(ib_path)
    analysis_file = os.path.join(ib_path, "analysis.json")

    buf_dict["ib"]["hash"] = ib
    buf_dict["ib"]["alias"] = ib_alias
    indices, match_info, vertex_count = analysis_ib(buf_dict, fc, ib_path)
    if len(indices) > 0:
        buf_dict["ib"]["vertex_count"] = vertex_count
        buf_dict["ib"]["indices"] = indices
        buf_dict["ib"]["info"] = match_info
        buf_dict, buf_count = analysis_buf(buf_dict, fc, ib_path)
        if buf_count > 0:
            buf_dict = analysis_slot(buf_dict, fc, ib_path, min_image_size)
            buf_dict = rename_elements(fc.game,ib_path,buf_dict)
            del buf_dict["ib"]["slots"]
            with open(analysis_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(buf_dict, ensure_ascii=False, indent=4))

            return analysis_file, "提取成功:" + analysis_file
        else:
            if not os.path.isfile(analysis_file):
                shutil.rmtree(ib_path)
            return "", f"未匹配到该顶点总数的缓冲区数据: {vertex_count}"
    else:
        #可能有旧的数据，删除需要用户来判断
        if not os.path.isfile(analysis_file):
            shutil.rmtree(ib_path)
        return "", f"帧转储文件中不存在: {ib}"
    
def analysis_general_dumps(output_path: str, dumps: str, game: str,
                   ib_infos: list = [], min_image_size: int = 1024) -> Tuple[List[str], str]:
    analysis_files = []
    user_game_buf_file = os.path.join(output_path, ".wci")

    if os.path.isfile(user_game_buf_file):
        with open(user_game_buf_file, "r", encoding="utf-8") as f:
            buf_dict = json.loads(f.read())
    else:
        buf_dict = game_buf_info(game)
        with open(user_game_buf_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(buf_dict, ensure_ascii=False, indent=4))

    fc = FileCollector(game, deepcopy(buf_dict), dumps)

    if len(ib_infos) == 0:
        ib_infos = analysis_frame(fc)

    reason = ""
    for ib_info in ib_infos:
        ib_hash, ib_alias = ib_info
        try:
            print("start search ib:", ib_hash)
            analysis_file, reason = dumps_by_ib(deepcopy(buf_dict),output_path, ib_hash, ib_alias, fc, min_image_size)
            if os.path.isfile(analysis_file):
                analysis_files.append(analysis_file)
        except Exception as e:
            import traceback
            traceback.print_exc()
            reason = str(e)
    return analysis_files,reason


def analysis_dumps(output_path: str, dumps: str, game: str,
                   ib_infos: list = [], min_image_size: int = 1024) -> Tuple[List[str], str]:
    """
    主分析入口：扫描帧转储目录，提取所有符合条件的IB并生成mod数据。

    Args:
        output_path: 输出目录。
        dumps: 帧转储目录路径。
        game: 游戏标识。
        ib_infos: 指定要分析的IB列表，若为空则自动检测。
        min_image_size: 最小纹理尺寸。

    Returns:
        (生成的analysis.json文件路径列表, 状态消息)
    """
    analysis_files,reason = analysis_general_dumps(output_path,dumps,game,ib_infos=ib_infos,min_image_size=int(min_image_size))
    return analysis_files,reason
