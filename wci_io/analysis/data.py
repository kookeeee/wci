import re
import os
import json
from collections import defaultdict, OrderedDict
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any, Optional, Union,Set
from copy import deepcopy
from ..constants import Game
from ..game import game_dict

def game_buf_info(game: str) -> dict:
    """
    根据游戏名称返回对应的缓冲区配置信息。

    Args:
        game: 游戏标识符（Game枚举值）。

    Returns:
        包含索引缓冲区（ib）和顶点缓冲区（vb）配置的字典。

    Raises:
        Exception: 当游戏不支持提取时抛出。
    """
    if game not in game_dict.buffer_dict:
        raise Exception("暂不支持提取！")
    return deepcopy(game_dict.buffer_dict[game])

def xor_bytes(data: bytes, key: bytes) -> bytes:
    key_len = len(key)
    if key_len == 0:
        return data  # 无密钥时不处理
    # 循环使用密钥的每个字节进行异或
    return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))

def dict_to_xor_binary(d, key: bytes) -> bytes:
    """将字典转换为 XOR 混淆后的二进制数据"""
    json_str = json.dumps(d, ensure_ascii=False)  # 确保中文等字符正常处理
    utf8_bytes = json_str.encode('utf-8')
    encrypted = xor_bytes(utf8_bytes, key)
    return encrypted

def xor_binary_to_dict(encrypted: bytes, key: bytes):
    """从 XOR 混淆后的二进制数据恢复字典"""
    decrypted = xor_bytes(encrypted, key)
    json_str = decrypted.decode('utf-8')
    return json.loads(json_str)


@dataclass
class DedupedFile:
    MATCH_PATTERN = re.compile("([a-zA-Z0-9]{8})-([a-z-]+\d+).*?-topology=(\w+).*?-count=(\d+).*?txt")
    hash:str = None
    buf:str = None
    layout:str = None
    topology:str = None
    count:int = 0
    file:str = None

    @classmethod
    def from_file(cls, filename: str) -> Optional['DedupedFile']:
        """从文件名解析并返回 DedupedFile 实例，若不匹配则返回 None"""
        match = cls.MATCH_PATTERN.match(filename)
        if not match:
            return None
        obj = cls()
        obj.hash = match.group(1)
        obj.buf = match.group(2)
        obj.layout = match.group(3)
        obj.topology = match.group(3)
        obj.count = int(match.group(4))  # 转换为整数
        if "-layout=" in filename:
            obj.layout=filename.split("-layout=")[1][0:8]
        else:
            obj.layout = "binary"
        obj.file = filename
        return obj

class FileCollector:
    """
    文件收集器，用于扫描和索引帧转储目录中的所有文件。
    根据文件名中的前缀（6位索引）和缓冲区类型建立快速查找缓存。
    """

    def __init__(self, game: str, buf_dict: dict, dumps_path: str):
        """
        初始化文件收集器，开始扫描。

        Args:
            game: 游戏标识。
            buf_dict: 缓冲区配置字典。
            dumps_path: 帧转储目录路径。
        """
        self.game = game
        self.indices:Set[str] = set()  # 所有出现的6位索引
        self.IndexBufferIndices:defaultdict[str,Set[str]] = defaultdict(set)  # ib哈希 -> 索引集合
        self.IndexBufferFiles:defaultdict[str,List[str]] = defaultdict(list)    # ib哈希 -> 文件列表
        self.skip_tex_hashs:List[str]=[]                 #跳过的hashs
        self.topologyCaches:Dict[str,str] = defaultdict()      # 哈希 -> 拓扑类型
        self.pointlistIndices:Set[str]=set()                 #所有使用 pointlist的索引
        self.hashIndices:Dict[str,List[str]] = defaultdict(list) #hash对应的索引
        self.VertexShaders:Set[str] = set()                   # 顶点着色器哈希
        self.PixelShaders:Set[str] = set()                     # 像素着色器哈希
        self.customShaders:Set[str] = set()                    # 自定义着色器哈希
        self.caches:defaultdict[str,List[str]] = defaultdict(list)                 # 通用缓存：键（哈希/索引/缓冲区名）-> 文件列表
        self.slots:List[str] = []                                 # 缓冲区槽位名称列表（不含ib）
        self.buf_dict:Dict[str,Any] = buf_dict
        self.dumps_path:str = dumps_path
        #可以得到layout topology buf hash count
        self.deduped_dict: Dict[int, Dict[str, List[DedupedFile]]] = {} #layout和拓扑的deduped文件字典
        self.__collect__()

    def __collect__(self):
        """
        扫描转储目录，建立各类缓存。
        """
        deduped_path = os.path.join(self.dumps_path,"deduped")
        if os.path.isdir(deduped_path):
            topolgy_dict=defaultdict(set)
            for filename in os.listdir(deduped_path):
                deduped = DedupedFile.from_file(filename)
                if deduped is None:
                    continue  # 不匹配的文件忽略
                count = deduped.count
                layout = deduped.layout
                topolgy_dict[deduped.hash].add(deduped.topology)
                self.topologyCaches[deduped.layout]=deduped.topology
                # 确保外层字典存在
                if count not in self.deduped_dict:
                    self.deduped_dict[count] = {}
                # 确保内层字典的列表存在
                if layout not in self.deduped_dict[count]:
                   self.deduped_dict[count][layout] = []
                # 添加当前对象
                self.deduped_dict[count][layout].append(deduped)
            #添加hash
            for hash in topolgy_dict:
                if len(topolgy_dict[hash])==1:
                    self.topologyCaches[hash]=list(topolgy_dict[hash])[0]
        # 提取所有缓冲区槽位名称（ib除外）
        for buf in self.buf_dict.keys():
            if "ib" not in buf:
                self.slots.append(buf)
        ps_hash_dict:Dict[str,int]={}
        for file in os.listdir(self.dumps_path):
            index = file[0:6]
            self.indices.add(index)
            buf = file[7:].split("=")[0]
            if len(buf)>0:
                hash = file.split(buf+"=")[1][:8]
                if "ps-" in buf:
                    if buf+"=!S!" in file:
                        hash = file.split(buf+"=!S!=")[1][:8]
                    if hash in ps_hash_dict:
                        ps_hash_dict[hash] += 1
                    else:
                        ps_hash_dict[hash] = 1
                self.hashIndices[hash].append(index)
                if hash in self.topologyCaches and self.topologyCaches[hash] in ['pointlist','3_control_point_patchlist']:
                    self.pointlistIndices.add(index)
                if "vs=" in file:
                    vs_hash = file.split("vs=")[1][:16]
                    if vs_hash not in self.VertexShaders:
                        self.VertexShaders.add(vs_hash)
                    self.caches[vs_hash].append(file)

                if "ib=" in file:
                    self.IndexBufferIndices[hash].add(index)
                    self.IndexBufferFiles[hash].append(file)
                    self.caches[hash].append(file)

                if buf in self.slots:
                    self.caches[buf].append(file)

                # 按索引缓存
                self.caches[index].append(file)
        self.skip_tex_hashs = [hash for hash, count in ps_hash_dict.items() if count > 30]
        if self.game == Game.AE:
            #雨滴法线
            self.skip_tex_hashs.append("afde0fcd")