from os import name
from functools import partial
import bpy
import os
import numpy as np
import random

from typing import List,Dict,Tuple,Any
from collections import defaultdict

from .format import DXGIFormater
from ..utils import format_size

from typing import List,Dict,Tuple,Union

# ---------- 辅助函数 ----------
def read_binary_buffer(file_path):
    """读取整个二进制缓冲区"""
    if not os.path.exists(file_path):
        print(f"文件不存在 {file_path}")
        return None
    
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return None



class WciLayoutElement(dict):
    def __init__(self,d):
        self.Index:int= int(d['index'])
        self.SemanticName:str = d['SemanticName']
        self.AliasSemanticName:str = d['AliasSemanticName']
        self.SemanticIndex:int = int(d['SemanticIndex'])
        self.Format:str = d['Format']
        if 'InputSlot' in d:
            self.InputSlot:str = d['InputSlot']
        self.AlignedByteOffset:int = int(d['AlignedByteOffset'])
        if 'InputSlotClass' in d:
            self.InputSlotClass:str = d['InputSlotClass']
        if 'InstanceDataStepRate' in d:
            self.InstanceDataStepRate:str = d['InstanceDataStepRate']
        
        self.indexOffset:int=self.SemanticIndex * 4

        fmt_char,byte_size,var_size = format_size(self.Format)
        self.fmt_char:str = fmt_char
        self.byte_size:int = byte_size
        self.var_size:int = var_size
        self.type:str = None
        self.encode_formatter = self.__partial_encode_formater__()
        self.decode_formatter = self.__partial_decode_formater__()

    def parse_vertex_attribute(self, buffer, vertex_idx, stride):
        """解析单个顶点的单个属性"""
        # 计算属性在缓冲区中的位置
        start = vertex_idx * stride + self.AlignedByteOffset
        end = start + self.byte_size        
        # 获取字节码数据
        data = buffer[start:end]
        return data

    
    def __partial_encode_formater__(self):
        if self.SemanticName.startswith('POSITION'):
            self.type = "position"
            return partial(DXGIFormater.encode_position, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('NORMAL'):
            self.type = "normal"
            return partial(DXGIFormater.encode_normal, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)   
        elif self.SemanticName.startswith('TANGENT'):
            self.type = "tangent"
            return partial(DXGIFormater.encode_tangent, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('COLOR'):
            self.type = "color"
            return partial(DXGIFormater.encode_color, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('TEXCOORD'):
            self.type = "texcoord"
            return partial(DXGIFormater.encode_uv, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('BLENDINDICE'):    
            self.type = "blendindice"
            return partial(DXGIFormater.encode_blend_indices, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('BLENDWEIGHT'):
            self.type = "blendweight"
            return partial(DXGIFormater.encode_blend_weights, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)  

    def __partial_decode_formater__(self):
        if self.SemanticName.startswith('POSITION'):
            return  partial(DXGIFormater.decode_position, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('NORMAL'):
            return partial(DXGIFormater.decode_normal, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)   
        elif self.SemanticName.startswith('TANGENT'):
            return partial(DXGIFormater.decode_tangent, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('COLOR'):
            return partial(DXGIFormater.decode_color, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('TEXCOORD'):
            return partial(DXGIFormater.decode_uv, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)   
        elif self.SemanticName.startswith('BLENDINDICE'):       
            return partial(DXGIFormater.decode_blend_indices, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)
        elif self.SemanticName.startswith('BLENDWEIGHT'):
            return partial(DXGIFormater.decode_blend_weights, fmt=self.Format, fmt_char=self.fmt_char, byte_size = self.byte_size, var_size=self.var_size)   



    
    @property
    def name(self):
        return self.AliasSemanticName
    
    def pad(self, data, val):
        padding = format_size(self.Format)[2] - len(data)
        if padding>0:
            return tuple(list(data) + [val] * padding)
        else:
            return data

    def clip(self, data,length=-1):
        if length>0:
            return data[:length]
        else:
            return data[:format_size(self.Format)[2]]
    
    
class VertexWriteBuffer():
    def __init__(self,buffer_path,elements:list[WciLayoutElement],stride,vertex_count):
        self.elements={} #elementName : WciLayoutElement
        self.stride=stride
        self.element_dict:Dict[str,WciLayoutElement]=defaultdict()
        self.vertex_count=vertex_count
        self.buffer_path=buffer_path
        self.buffer = bytearray(self.vertex_count * self.stride)
        for elem in elements:
            self.element_dict[elem.name]=elem

    def save(self):
        with open(self.buffer_path,"wb") as f:
            f.write(self.buffer)
        
    def write_byte_data(self,element_name,v_idx,encode_data):
        #从elementName获取offset然后写入
        # 写入缓冲区
        offset=self.element_dict[element_name].AlignedByteOffset
        start = v_idx*self.stride + offset
        end = start + len(encode_data)
        self.buffer[start:end] = encode_data

def get_np_array(raw_vertices,sementicName,dtype=np.float32):
    if sementicName in raw_vertices[0]:
        return np.array([v[sementicName] for v in raw_vertices],dtype=dtype)
    else:
        return np.array([[0,0,0,0] for v in raw_vertices],dtype=dtype)
    

def compute_d2_histogram(raw_vertices,raw_faces, num_samples=2048, num_pairs=100000, bins=64):
    
    vertices = get_np_array(raw_vertices,'POSITION')
    
    # 计算三角形面积和累积分布
    tri_areas = []
    #raw_faces合并
    faces = []
    for sub in raw_faces:
        faces += [list(i) for i in raw_faces[sub]]
    for tri in faces:
        v0,v1,v2 = vertices[tri]
        area = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))
        tri_areas.append(area)
    total_area = sum(tri_areas)
    cum_areas = np.cumsum(tri_areas) / total_area
    
    # 采样点
    points = []
    for _ in range(num_samples):
        r = random.random()
        tri_idx = np.searchsorted(cum_areas, r)
        tri = faces[tri_idx]
        v0, v1, v2 = vertices[tri]
        u = random.random()
        v = random.random()
        if u + v > 1:
            u = 1 - u
            v = 1 - v
        w = 1 - u - v
        point = u * v0 + v * v1 + w * v2
        points.append(point)
    points = np.array(points)
    
    # 随机点对距离
    idx_pairs = np.random.choice(num_samples, size=(num_pairs, 2), replace=True)
    distances = np.linalg.norm(points[idx_pairs[:, 0]] - points[idx_pairs[:, 1]], axis=1)
    
    # 生成直方图
    hist, _ = np.histogram(distances, bins=bins, range=(0, np.max(distances)))
    hist = hist / np.sum(hist)  # 归一化
    return hist.tolist()  

def chi2_distance(histA, histB, eps=1e-10):
    """卡方距离"""
    histA = np.array(histA)
    histB = np.array(histB)
    return 0.5 * np.sum((histA - histB) ** 2 / (histA + histB + eps))


def remap_zero_rows(vg_ids: np.ndarray, vg_weights: np.ndarray) -> np.ndarray:
    """将0顶点组ID（有权重）替换为最大ID+1"""
    vg_ids = vg_ids.copy()
    virtual_id = int(vg_ids.max() + 1)
    # Create dummy weights array if not found (aka [[1, 0, 0, 0] * len(vg_ids)])
    if vg_weights is None:
        num_rows = vg_ids.shape[0]
        num_zeros = vg_ids.shape[1] - 1
        vg_weights = np.hstack([
            np.ones((num_rows, 1), dtype=np.int32),
            np.zeros((num_rows, num_zeros), dtype=np.int32)
        ])
    # Replace zeros where weight > 0
    mask = (vg_ids == 0) & (vg_weights > 0)
    vg_ids[mask] = virtual_id
    return vg_ids, virtual_id



def calculate_min_distances(points_a: np.ndarray, points_b: np.ndarray, chunk_size = 256):
    """Computes minimum distance for each vertex in points_a to any vertex in points_b in chunks to save memory."""
    cd_chunks = []
    for start in range(0, len(points_a), chunk_size):
        end = start + chunk_size
        diff_chunk = points_a[start:end, None, :] - points_b[None, :, :]
        dist_chunk = np.min(np.linalg.norm(diff_chunk, axis=2), axis=1)
        cd_chunks.append(dist_chunk)
    return np.concatenate(cd_chunks)

def calculate_linear_chamfer_distance(points_a: np.ndarray, points_b: np.ndarray) -> np.ndarray:
    """Calculates symmetric Chamfer distance using linear distances."""
    dist1 = calculate_min_distances(points_a, points_b)
    dist2 = calculate_min_distances(points_b, points_a)
    return np.mean(dist1) + np.mean(dist2)


def _precompute_vg_data(positions: np.ndarray, indices: np.ndarray) -> Tuple[Dict[int, np.ndarray], Dict[int, np.ndarray], np.ndarray, np.ndarray]:
    """预计算顶点组数据：每个VG的点云、质心、以及mask数组。"""
    unique_vgs = np.unique(indices[indices != 0])
    points_dict = {}
    centroids = []
    
    for vg in unique_vgs:
        mask = np.any(indices == vg, axis=1)
        points = positions[mask].astype(np.float32)
        points_dict[int(vg)] = points
        centroid = points.mean(axis=0) if len(points) > 0 else np.array([np.inf] * 3, dtype=np.float32)
        centroids.append(centroid)
    
    return points_dict, dict(zip(unique_vgs, centroids)), np.array(centroids, dtype=np.float32), unique_vgs

def _find_blend_semantics(raw_vertices: List[Dict[str, tuple]]) -> Tuple[str, str]:
    """查找 blend indices 和 blend weights 的语义名称。"""
    blendindices = ""
    blendweights = ""
    for semantic in raw_vertices[0]:
        if "INDICE" in semantic:
            blendindices = semantic
        elif "WEIGHT" in semantic:
            blendweights = semantic
    return blendindices, blendweights
    
def match_vertex_groups(raw_vertices_a:List[Dict[str,tuple]],raw_vertices_b:List[Dict[str,tuple]])->Dict[int, int]:
    """
        raw_vertices_a 需要查找lod的ib顶点数据
        raw_vertices_b lod ib顶点数据
    """
    blendindices, blendweights = _find_blend_semantics(raw_vertices_a)
    positions_a = get_np_array(raw_vertices_a,"POSITION",dtype=np.float32)
    indices_a = get_np_array(raw_vertices_a,blendindices,dtype=np.uint8)
    weights_a = get_np_array(raw_vertices_a,blendweights,dtype=np.float32)
    positions_b = get_np_array(raw_vertices_b,"POSITION",dtype=np.float32)
    indices_b = get_np_array(raw_vertices_b,blendindices,dtype=np.uint8)
    weights_b = get_np_array(raw_vertices_b,blendweights,dtype=np.float32)
    if indices_a is None:
        return {0: 0}
    
    # 将VG 0映射到虚拟ID
    # 这样可以统一用 != 0 判断有效VG，避免特殊处理VG 0
    indices_a, zero_id_a = remap_zero_rows(indices_a, weights_a)
    indices_b, zero_id_b = remap_zero_rows(indices_b, weights_b)
    
    points_dict_b, centroids_dict_b, centroids_b_arr, unique_indices_b = _precompute_vg_data(positions_b, indices_b)
    
    points_dict_a, centroids_dict_a, _, unique_indices_a = _precompute_vg_data(positions_a, indices_a)
    
    mapping = {}
    for vg_a in unique_indices_a:
        vg_a_int = int(vg_a)
        points_a = points_dict_a.get(vg_a_int)
        
        if points_a is None or len(points_a) == 0:
            mapping[vg_a_int if vg_a_int != zero_id_a else 0] = None
            continue
        
        full_centroid = centroids_dict_a[vg_a]
        
        # Pre-filter VG candidates from mesh B using centroid distance
        dists = np.linalg.norm(centroids_b_arr - full_centroid, axis=1)
        candidate_indices = np.argsort(dists)[:3]
        
        best_cd = np.inf
        best_vg_b = None
        
        for idx in candidate_indices:
            vg_b = unique_indices_b[idx]
            points_b = points_dict_b.get(int(vg_b))
            
            if points_b is None or len(points_b) == 0:
                continue
                
            cd = calculate_linear_chamfer_distance(points_a, points_b)
            if cd < best_cd:
                best_cd = cd
                best_vg_b = vg_b
        
        # 将虚拟ID映射回0
        vg_a_key = 0 if vg_a_int == zero_id_a else vg_a_int
        
        best_vg_b_val = int(best_vg_b) if best_vg_b is not None else None
        if best_vg_b_val == zero_id_b:
            best_vg_b_val = 0
        
        mapping[vg_a_key] = best_vg_b_val
    
    return dict(sorted(mapping.items()))


def init_vertices(self, mesh: bpy.types.Mesh):
    """顶点数据初始化"""
    vertices = mesh.vertices
    loops = mesh.loops
    vertex_count = len(vertices)
    loop_count = len(loops)

    # ---------- 1. 批量提取数据到 NumPy 数组 ----------
    # 顶点位置
    vert_co = np.zeros((vertex_count, 3), dtype=np.float32)
    vertices.foreach_get('co', vert_co.ravel())

    # loop 对应的顶点索引
    loop_vert_idx = np.zeros(loop_count, dtype=np.int32)
    loops.foreach_get('vertex_index', loop_vert_idx)

    # loop 法线
    loop_normals = np.zeros((loop_count, 3), dtype=np.float32)
    loops.foreach_get('normal', loop_normals.ravel())


    # loop 切线 (前三个分量)
    loop_tangents = np.zeros((loop_count, 3), dtype=np.float32)
    loops.foreach_get('tangent', loop_tangents.ravel())
    # loop 副法线符号
    loop_bitangent_sign = np.zeros(loop_count, dtype=np.float32)
    loops.foreach_get('bitangent_sign', loop_bitangent_sign)

    # ---------- 2. 按顶点位置分组 ----------
    unique_pos, inv_idx, group_counts = np.unique(vert_co, axis=0, return_inverse=True, return_counts=True)
    n_groups = len(unique_pos)

    # 每个 loop 所属的位置组索引
    loop_group_idx = inv_idx[loop_vert_idx]

    # 按组排序，以便使用 reduceat
    sort_idx = np.argsort(loop_group_idx)
    sorted_group_idx = loop_group_idx[sort_idx]
    sorted_normals = loop_normals[sort_idx]
    sorted_tangents = loop_tangents[sort_idx]
    sorted_bitangent_sign = loop_bitangent_sign[sort_idx]

    # 找到每组起始位置
    group_starts = np.flatnonzero(np.concatenate(([True], sorted_group_idx[:-1] != sorted_group_idx[1:])))
    # 每组包含的 loop 数量
    group_loop_counts = np.diff(np.append(group_starts, len(sorted_normals)))

    # ---------- 3. 计算每组平均法线 ----------
    sum_normals = np.add.reduceat(sorted_normals, group_starts, axis=0)
    avg_normals_group = np.zeros_like(sum_normals)
    non_zero = group_loop_counts > 0
    avg_normals_group[non_zero] = sum_normals[non_zero] / group_loop_counts[non_zero, np.newaxis]

    # 归一化
    norms = np.linalg.norm(avg_normals_group, axis=1, keepdims=True)
    norms[norms == 0] = 1
    avg_normals_group /= norms

    # ---------- 4. 计算每组平均切线 ----------
    # 先计算每个 loop 的副法线: B = sign * cross(N, T)
    loop_bitangents = sorted_bitangent_sign[:, np.newaxis] * np.cross(sorted_normals, sorted_tangents)

    # 累加切线和副法线
    sum_tangents = np.add.reduceat(sorted_tangents, group_starts, axis=0)
    sum_bitangents = np.add.reduceat(loop_bitangents, group_starts, axis=0)

    avg_tangents_group = np.zeros_like(sum_tangents)
    avg_bitangents_group = np.zeros_like(sum_bitangents)
    avg_tangents_group[non_zero] = sum_tangents[non_zero] / group_loop_counts[non_zero, np.newaxis]
    avg_bitangents_group[non_zero] = sum_bitangents[non_zero] / group_loop_counts[non_zero, np.newaxis]

    # 归一化
    t_norms = np.linalg.norm(avg_tangents_group, axis=1, keepdims=True)
    t_norms[t_norms == 0] = 1
    avg_tangents_group /= t_norms

    b_norms = np.linalg.norm(avg_bitangents_group, axis=1, keepdims=True)
    b_norms[b_norms == 0] = 1
    avg_bitangents_group /= b_norms

    # 正交化：使切线垂直于平均法线
    dot = np.sum(avg_tangents_group * avg_normals_group, axis=1, keepdims=True)
    t_orth = avg_tangents_group - dot * avg_normals_group
    t_orth_norms = np.linalg.norm(t_orth, axis=1, keepdims=True)
    t_orth_norms[t_orth_norms == 0] = 1
    t_orth /= t_orth_norms

    # 候选副法线 (与重建副法线一致)
    b_candidate = np.cross(avg_normals_group, t_orth)

    # 确定 w 符号
    dot_b = np.sum(b_candidate * avg_bitangents_group, axis=1)
    w = np.where(dot_b >= 0, 1.0, -1.0)

    # 最终切线四元组
    tangents_group = np.column_stack([t_orth, w])

    # ---------- 5. 将组结果映射回每个顶点 ----------
    avg_normals = avg_normals_group[inv_idx]          # (vertex_count, 3)
    avg_tangents = tangents_group[inv_idx]        # (vertex_count, 4)

    # 处理没有 loop 的顶点（孤立点）
    vert_has_loop = group_loop_counts[inv_idx] > 0
    if not np.all(vert_has_loop):
        default_normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        avg_normals[~vert_has_loop] = default_normal
        default_tangent = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        avg_tangents[~vert_has_loop] = default_tangent

    # ---------- 6. 构建位置到 loop 列表的映射（用于 UV/颜色） ----------
    from collections import defaultdict
    vertex_coords = [tuple(v) for v in vert_co]  # 列表，后续也用于位置编码
    vert_loop_indices = defaultdict(list)
    for i, loop in enumerate(loops):
        v = loop.vertex_index
        vert_loop_indices[vertex_coords[v]].append(i)

    # ---------- 7. 顶点组处理 ----------
    vertex_groups_data = []
    for v in vertices:
        groups = v.groups
        if groups:
            group_data = sorted(groups, key=lambda x: x.weight, reverse=True)
            if len(group_data) > 4:
                raise Exception("顶点组超出!")
            vertex_groups_data.append(group_data)
        else:
            vertex_groups_data.append([])

    # ---------- 8. UV 和颜色缓存 ----------
    uv_data_cache = {}
    if mesh.uv_layers:
        for uv_layer in mesh.uv_layers:
            uv_list = []
            for uv in uv_layer.data:
                uv_list.append((uv.uv.x, uv.uv.y))
            uv_data_cache[uv_layer.name] = uv_list

    color_data_cache = {}
    if mesh.vertex_colors:
        for color_layer in mesh.vertex_colors:
            color_list = []
            for color in color_layer.data:
                color_list.append(color)
            color_data_cache[color_layer.name] = color_list
 

    # ---------- 10. 逐顶点编码（保持不变，但法线/切线从 NumPy 数组取值） ----------
    indexed_vertices = [None] * vertex_count
    uv_data_cache_get = uv_data_cache.get

    for v_idx in range(vertex_count):
        vertex = {}
        position = vertex_coords[v_idx]
        # 取该位置第一个 loop 索引（与原逻辑一致）
        loop_indices = vert_loop_indices.get(position, [])
        loop_idx = loop_indices[0] if loop_indices else 0

        groups = vertex_groups_data[v_idx]

        for elem_name  in self.elements:
            element = self.elements[elem_name]
            elem_type = element.type
            formatter = element.encode_formatter
            if elem_type == 'position':
                value = element.pad(position, 1.0)
                vertex[elem_name] = formatter(value)

            elif elem_type == 'normal':
                from mathutils import Vector
                value = tuple(avg_normals[v_idx])
                vertex[elem_name] = formatter(Vector(value), Vector(avg_tangents[v_idx][0:3]),avg_tangents[v_idx][3])

            elif elem_type == 'tangent':
                value = tuple(avg_tangents[v_idx])
                vertex[elem_name] = formatter(value)

            elif elem_type == 'color':
                if elem_name in mesh.vertex_colors:
                    value = color_data_cache[elem_name][loop_idx]
                vertex[elem_name] = formatter(value)

            elif elem_type == 'blendindice':
                index_offset = getattr(element, 'indexOffset', 0)
                indices = [0, 0, 0, 0]
                for i in range(index_offset, index_offset + 4):
                    if i < len(groups):
                        indices[i] = groups[i].group
                vertex[elem_name] = formatter(tuple(indices))

            elif elem_type == 'blendweight':
                index_offset = getattr(element, 'indexOffset', 0)
                weights = [0.0, 0.0, 0.0, 0.0]
                total = 0.0
                for i in range(index_offset, index_offset + 4):
                    if i < len(groups):
                        weight = groups[i].weight
                        weights[i] = weight
                        total += weight
                if total > 0:
                    weights = [w / total for w in weights]
                vertex[elem_name] = formatter(tuple(weights))

            elif elem_type == 'texcoord':
                uv_xy_name = f'{elem_name}.xy'
                uv_zw_name = f'{elem_name}.zw'
                uvs = []
                uv_data = uv_data_cache_get(uv_xy_name)
                if uv_data and loop_idx < len(uv_data):
                    u, v = uv_data[loop_idx]
                    uvs.extend([u, v])
                uv_data = uv_data_cache_get(uv_zw_name)
                if uv_data and loop_idx < len(uv_data):
                    u, v = uv_data[loop_idx]
                    uvs.extend([u, v])
                while len(uvs) < 4:
                    uvs.append(0.0)
                vertex[elem_name] = formatter(uvs)

        indexed_vertices[v_idx] = vertex

    return indexed_vertices


def smooth_normals(vertices, loops):
    """
    平滑法线并生成切线，用于GI/原神游戏的2D化光影效果
    
    计算统一法线（按位置聚类平均），并将平滑后的法线存入切线
    切线W分量固定为-1
    
    Args:
        vertices: Blender MeshVertex 集合
        loops: Blender MeshLoop 集合  
    
    Returns:
        avg_normals: (vertex_count, 3) 每个顶点的平滑法线
        avg_tangents: (vertex_count, 4) 每个顶点的切线 (平滑法线XYZ, W=-1)
    """
    
    vertex_count = len(vertices)
    
    loop_vert_indices = np.array([loop.vertex_index for loop in loops], dtype=np.int32)
    loop_normals = np.array([loop.normal for loop in loops], dtype=np.float32)
    
    vertex_coords = np.array([v.co for v in vertices], dtype=np.float32)
    
    sort_indices = np.argsort(loop_vert_indices)
    sorted_vert_indices = loop_vert_indices[sort_indices]
    sorted_normals = loop_normals[sort_indices]
    
    vertex_normals = np.empty((vertex_count, 3), dtype=np.float32)
    
    for v_idx in range(vertex_count):
        start = np.searchsorted(sorted_vert_indices, v_idx, side='left')
        end = np.searchsorted(sorted_vert_indices, v_idx, side='right')
        
        if start >= end:
            vertex_normals[v_idx] = [0, 0, 1]
            continue
        
        v_normals = sorted_normals[start:end]
        
        avg_n = np.mean(v_normals, axis=0)
        avg_n = avg_n / (np.linalg.norm(avg_n) + 1e-8)
        
        vertex_normals[v_idx] = avg_n
    
    sort_idx = np.lexsort(vertex_coords.T)
    sorted_coords = vertex_coords[sort_idx]
    sorted_normals = vertex_normals[sort_idx]
    
    if len(sorted_coords) > 1:
        diff = np.any(sorted_coords[:-1] != sorted_coords[1:], axis=1)
        group_bounds = np.r_[0, np.flatnonzero(diff) + 1, len(sorted_coords)]
    else:
        group_bounds = np.array([0, len(sorted_coords)])
    
    for i in range(len(group_bounds) - 1):
        start, end = group_bounds[i], group_bounds[i + 1]
        
        if end - start <= 1:
            continue
        group_normals = sorted_normals[start:end]
        unified_n = np.mean(group_normals, axis=0)
        unified_n = unified_n / (np.linalg.norm(unified_n) + 1e-8)
        sorted_normals[start:end] = unified_n
    
    avg_normals = np.empty((vertex_count, 3), dtype=np.float32)
    avg_normals[sort_idx] = sorted_normals
    
    avg_tangents = np.empty((vertex_count, 4), dtype=np.float32)
    avg_tangents[:, :3] = avg_normals
    avg_tangents[:, 3] = -1.0
    
    return avg_normals, avg_tangents

def smooth_normals_by_angle(vertices, loops, angle_threshold=30.0):
    """
    平滑法线和切线，保留硬边的同时实现平滑过渡
    
    使用NumPy向量化操作，比原实现快10-100倍
    
    Args:
        vertices: Blender MeshVertex 集合
        loops: Blender MeshLoop 集合
        angle_threshold: 角度阈值（度），超过此角度的法线视为不同组，保留硬边
    
    Returns:
        avg_normals: (vertex_count, 3) 每个顶点的平滑法线
        avg_tangents: (vertex_count, 4) 每个顶点的平滑切线 (tx, ty, tz, sign)
    """
    
    vertex_count = len(vertices)
    threshold_dot = np.cos(np.radians(angle_threshold))
    
    # 提取所有loop数据到NumPy数组
    loop_vert_indices = np.array([loop.vertex_index for loop in loops], dtype=np.int32)
    loop_normals = np.array([loop.normal for loop in loops], dtype=np.float32)
    loop_tangents = np.array([loop.tangent for loop in loops], dtype=np.float32)
    loop_signs = np.array([loop.bitangent_sign for loop in loops], dtype=np.float32)
    
    # 获取顶点坐标
    vertex_coords = np.array([v.co for v in vertices], dtype=np.float32)
    
    # 按顶点索引排序，让同一顶点的loop相邻
    sort_indices = np.argsort(loop_vert_indices)
    sorted_vert_indices = loop_vert_indices[sort_indices]
    sorted_normals = loop_normals[sort_indices]
    sorted_tangents = loop_tangents[sort_indices]
    sorted_signs = loop_signs[sort_indices]
    
    # 步骤1: 为每个顶点按角度分组法线
    vertex_normals = np.empty((vertex_count, 3), dtype=np.float32)
    vertex_tangents = np.empty((vertex_count, 3), dtype=np.float32)
    vertex_signs = np.empty(vertex_count, dtype=np.float32)
    vertex_group_keys = []  # 每个顶点的主法线组键
    
    for v_idx in range(vertex_count):
        start = np.searchsorted(sorted_vert_indices, v_idx, side='left')
        end = np.searchsorted(sorted_vert_indices, v_idx, side='right')
        
        if start >= end:
            vertex_normals[v_idx] = [0, 0, 1]
            vertex_tangents[v_idx] = [1, 0, 0]
            vertex_signs[v_idx] = 1.0
            vertex_group_keys.append(None)
            continue
        
        v_normals = sorted_normals[start:end]
        v_tangents = sorted_tangents[start:end]
        v_signs = sorted_signs[start:end]
        
        # 按角度分组 - 使用向量化操作
        group_indices = _group_normals_by_angle_vectorized(v_normals, threshold_dot)
        
        # 找到最大的组
        best_group_idx = max(range(len(group_indices)), key=lambda i: len(group_indices[i]))
        best_indices = group_indices[best_group_idx]
        
        # 计算组内平均
        group_normals = v_normals[best_indices]
        group_tangents = v_tangents[best_indices]
        group_signs = v_signs[best_indices]
        
        avg_n = np.mean(group_normals, axis=0)
        avg_n = avg_n / (np.linalg.norm(avg_n) + 1e-8)
        
        avg_t = np.mean(group_tangents, axis=0)
        # 施密特正交化
        avg_t = avg_t - np.dot(avg_t, avg_n) * avg_n
        t_norm = np.linalg.norm(avg_t)
        if t_norm > 1e-8:
            avg_t = avg_t / t_norm
        else:
            avg_t = find_orthogonal_vector(avg_n)
        
        vertex_normals[v_idx] = avg_n
        vertex_tangents[v_idx] = avg_t
        vertex_signs[v_idx] = np.sign(np.mean(group_signs)) if len(group_signs) > 0 else 1.0
        
        # 生成组键用于跨顶点聚类
        normal_key = tuple(np.round(avg_n, 1))
        vertex_group_keys.append(normal_key)
    
    sort_idx = np.lexsort(vertex_coords.T)
    sorted_coords = vertex_coords[sort_idx]
    sorted_normals = vertex_normals[sort_idx]
    sorted_tangents = vertex_tangents[sort_idx]
    sorted_signs = vertex_signs[sort_idx]
    sorted_group_keys = [vertex_group_keys[i] for i in sort_idx]
    
    # 找出位置变化的分组边界
    if len(sorted_coords) > 1:
        diff = np.any(sorted_coords[:-1] != sorted_coords[1:], axis=1)
        group_bounds = np.r_[0, np.flatnonzero(diff) + 1, len(sorted_coords)]
    else:
        group_bounds = np.array([0, len(sorted_coords)])
    
    # 为每个位置组计算统一法线和切线
    for i in range(len(group_bounds) - 1):
        start, end = group_bounds[i], group_bounds[i + 1]
        
        if end - start <= 1:
            continue
        
        # 该组内所有顶点共享相同的平滑法线
        group_normals = sorted_normals[start:end]
        group_tangents = sorted_tangents[start:end]
        group_signs = sorted_signs[start:end]
        
        # 计算统一法线
        unified_n = np.mean(group_normals, axis=0)
        unified_n = unified_n / (np.linalg.norm(unified_n) + 1e-8)
        
        # 计算统一切线（正交化）
        unified_t = np.mean(group_tangents, axis=0)
        unified_t = unified_t - np.dot(unified_t, unified_n) * unified_n
        t_norm = np.linalg.norm(unified_t)
        if t_norm > 1e-8:
            unified_t = unified_t / t_norm
        else:
            unified_t = find_orthogonal_vector(unified_n)
        
        # 统一符号
        unified_sign = np.sign(np.mean(group_signs))
        
        # 写回组内所有顶点
        sorted_normals[start:end] = unified_n
        sorted_tangents[start:end] = unified_t
        sorted_signs[start:end] = unified_sign
    
    # 还原原始顺序
    avg_normals = np.empty((vertex_count, 3), dtype=np.float32)
    avg_tangents = np.empty((vertex_count, 4), dtype=np.float32)
    
    avg_normals[sort_idx] = sorted_normals
    avg_tangents[sort_idx, :3] = sorted_tangents
    avg_tangents[sort_idx, 3] = sorted_signs
    
    return avg_normals, avg_tangents


def _group_normals_by_angle_vectorized(normals, threshold_dot):
    """
    使用向量化操作将法线按角度分组
    
    Args:
        normals: (N, 3) 法线数组
        threshold_dot: 角度阈值的余弦值
    
    Returns:
        list of arrays: 每个组的索引列表
    """
    n = len(normals)
    if n == 0:
        return []
    if n == 1:
        return [np.array([0])]
    
    # 计算所有法线对之间的点积
    dots = np.dot(normals, normals.T)
    
    # 标记已使用的法线
    used = np.zeros(n, dtype=bool)
    groups = []
    
    for i in range(n):
        if used[i]:
            continue
        
        # 找到与当前法线相近的所有法线
        similar = (dots[i] > threshold_dot) & ~used
        group_indices = np.where(similar)[0]
        
        if len(group_indices) == 0:
            group_indices = np.array([i])
        
        used[group_indices] = True
        groups.append(group_indices)
    
    return groups


def quantize_normal_for_hash(normal, grid_size=8):
    """
    将法线量化到粗网格，用于空间哈希
    
    Args:
        normal: (3,) 法线向量
        grid_size: 网格大小，默认8x8x8
    
    Returns:
        量化后的哈希键（元组）
    """
    normal = normal / (np.linalg.norm(normal) + 1e-8)
    # 映射到 0-(grid_size-1) 的整数
    quantized = tuple(np.floor((normal + 1.0) * (grid_size - 1) / 2.0).astype(np.int32))
    return quantized


def group_normals_by_angle(normal_data, angle_threshold):
    """
    将法线按角度阈值分组 - 使用空间哈希优化，O(n)复杂度
    
    Args:
        normal_data: [(loop_idx, normal, tangent, sign), ...]
        angle_threshold: 角度阈值（度）
    
    Returns:
        [(normals_list, tangents_list, signs_list), ...]
    """
    if not normal_data:
        return []
    
    threshold_dot = np.cos(np.radians(angle_threshold))
    
    # 步骤1: 使用空间哈希将法线分到不同的桶
    # 只有同一桶内的法线才需要比较，大幅减少比较次数
    buckets = defaultdict(list)
    
    for i, (loop_idx, normal, tangent, sign) in enumerate(normal_data):
        # 量化法线方向作为哈希键
        quantized = quantize_normal_for_hash(normal, grid_size=8)
        buckets[quantized].append((i, loop_idx, normal, tangent, sign))
    
    # 步骤2: 在每个桶内进行分组
    groups = []
    used = set()
    
    for bucket in buckets.values():
        # 桶内数据量通常很小（几个到几十个）
        for i, loop_idx_i, normal_i, tangent_i, sign_i in bucket:
            if i in used:
                continue
            
            # 创建新组
            group_normals = [normal_i]
            group_tangents = [tangent_i]
            group_signs = [sign_i]
            used.add(i)
            
            # 只和同一桶内的其他法线比较
            for j, loop_idx_j, normal_j, tangent_j, sign_j in bucket:
                if j in used:
                    continue
                
                # 使用点积快速判断，避免arccos
                dot = np.dot(normal_i, normal_j)
                if dot > threshold_dot:
                    group_normals.append(normal_j)
                    group_tangents.append(tangent_j)
                    group_signs.append(sign_j)
                    used.add(j)
            
            groups.append((group_normals, group_tangents, group_signs))
    
    return groups


def quantize_normal_direction(normal, sectors=6):
    """
    将法线方向量化到几个主要扇区
    
    Args:
        normal: (3,) 法线向量
        sectors: 扇区数量（6=立方体6个面，8=八面体8个角）
    
    Returns:
        量化后的方向标识（元组）
    """
    import numpy as np
    
    normal = normal / (np.linalg.norm(normal) + 1e-8)
    
    if sectors == 6:
        # 6个主要方向（立方体面）
        directions = [
            np.array([1, 0, 0]), np.array([-1, 0, 0]),
            np.array([0, 1, 0]), np.array([0, -1, 0]),
            np.array([0, 0, 1]), np.array([0, 0, -1])
        ]
    elif sectors == 8:
        # 8个对角方向
        s = 1 / np.sqrt(3)
        directions = [
            np.array([s, s, s]), np.array([s, s, -s]),
            np.array([s, -s, s]), np.array([s, -s, -s]),
            np.array([-s, s, s]), np.array([-s, s, -s]),
            np.array([-s, -s, s]), np.array([-s, -s, -s])
        ]
    else:
        # 默认：保留1位小数
        return tuple(np.round(normal, 1))
    
    # 找最接近的方向
    best_idx = np.argmax([np.dot(normal, d) for d in directions])
    return tuple(directions[best_idx])


def find_orthogonal_vector(normal):
    """
    找到一个与给定法线垂直的向量
    """
    import numpy as np
    
    normal = normal / (np.linalg.norm(normal) + 1e-8)
    
    # 尝试与 X 轴叉乘
    if abs(normal[0]) < 0.9:
        tangent = np.cross(normal, np.array([1, 0, 0]))
    else:
        # 如果法线接近 X 轴，与 Y 轴叉乘
        tangent = np.cross(normal, np.array([0, 1, 0]))
    
    return tangent / (np.linalg.norm(tangent) + 1e-8)
