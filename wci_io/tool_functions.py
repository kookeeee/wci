import bpy
import math 
import time
import bmesh
import bpy



from typing import List, Tuple
from mathutils import Vector
from collections import defaultdict
from mathutils import Vector


from .constants import VERTEX_ATTRIBUTES



def __getCustomNormalKeeper(mesh):
    if hasattr(mesh, 'has_custom_normals') and mesh.use_auto_smooth:
        class _CustomNormalKeeper:
            def __init__(self, mesh):
                mesh.calc_normals_split()
                self.__normals = tuple(zip((l.normal.copy() for l in mesh.loops), (p.material_index for p in mesh.polygons for v in p.vertices)))
                mesh.free_normals_split()
                self.__material_map = {}
                materials = mesh.materials
                for i, m in enumerate(materials):
                    if m is None or m.name in self.__material_map:
                        materials[i] = bpy.data.materials.new('_mmd_tmp_')
                    self.__material_map[materials[i].name] = (i, getattr(m, 'name', ''))

            def restore_custom_normals(self, mesh):
                materials = mesh.materials
                for i, m in enumerate(materials):
                    mat_id, mat_name_orig = self.__material_map[m.name]
                    if m.name != mat_name_orig:
                        materials[i] = bpy.data.materials.get(mat_name_orig, None)
                        m.user_clear()
                        bpy.data.materials.remove(m)
                if len(materials) == 1:
                    mesh.normals_split_custom_set([n for n, x in self.__normals if x == mat_id])
                    mesh.update()
        return _CustomNormalKeeper(mesh) # This fixes the issue that "SeparateByMaterials" could break custom normals
    return None


def selectAObject(obj):
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=obj


def deselectObject(obj):
    if bpy.app.version >= (4, 0):
        obj.select_set(False)
    else:
        obj.select=False
    #bpy.ops.object.select_all(action='DESELECT')
    if obj == bpy.context.view_layer.objects.active:
        bpy.context.view_layer.objects.active=None


def enterEditMode(obj):
    selectAObject(obj)
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

def separateByMaterials(meshObj):
    if len(meshObj.data.materials) < 2:
        selectAObject(meshObj)
        return
    custom_normal_keeper = __getCustomNormalKeeper(meshObj.data)
    matrix_parent_inverse = meshObj.matrix_parent_inverse.copy()
    prev_parent = meshObj.parent
    dummy_parent = bpy.data.objects.new(name='tmp', object_data=None)
    meshObj.parent = dummy_parent
    meshObj.active_shape_key_index = 0
    try:
        enterEditMode(meshObj)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        for i in dummy_parent.children:
            if custom_normal_keeper:
                custom_normal_keeper.restore_custom_normals(i.data)
            materials = i.data.materials
            i.name = getattr(materials[0], 'name', 'None') if len(materials) else 'None'
            i.name=i.name.replace("Mat_","")
            i.parent = prev_parent
            i.matrix_parent_inverse = matrix_parent_inverse
        bpy.data.objects.remove(dummy_parent)


class SmoothNormal:
    '''
    SmoothNormal Algorithm.
    SupportedGame: GI,HI3,HSR,ZZZ,WuWa
    Designed For: ZZZ,WuWa

    # 代码版权与来源：
    # function 
    # https://www.bilibili.com/video/BV13G411u75s/?spm_id_from=333.999.0.0 
    # by 给你柠檬椰果养乐多你会跟我玩吗

    # 将法线XY分量存储到UV贴图的坐标(X:法线x, Y:法线y)
    # 灵感来自smoothtool from github 
    # by dashu04

    # 整合 by 失乡のKnight
    # 拆解信息链、重构为工具类 by NicoMico
    '''
    @classmethod
    def vector_cross_product(cls,v1,v2):
        '''
        叉乘 (Cross Product): 两个不平行的三维向量的叉乘会生成一个新的向量，这个新向量与原来的两个向量都垂直。
        因此，对于给定的三角形，使用其两边进行叉乘可以得到一个垂直于该三角形平面的向量，这就是所谓的法线向量。
        '''
        return Vector((v1.y*v2.z-v2.y*v1.z,v1.z*v2.x-v2.z*v1.x,v1.x*v2.y-v2.x*v1.y))
    
    @classmethod
    def vector_dot_product (cls,a,b):
        return a.x*b.x+a.y*b.y+a.z*b.z
    
    @classmethod
    def vector_calc_length(cls,v):
        return math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z)
    
    
    @classmethod
    def vector_normalize(cls,v):
        '''
        归一化 (Normalization): 
        之后对叉乘结果进行归一化（normalize），即调整法线向量的长度为1，这样可以确保法线向量只表示方向而不带有长度信息。
        这一步很重要，因为光照计算通常依赖于单位长度的法线向量来保证正确性。
        '''
        L = cls.vector_calc_length(v)
        if L != 0 :
            return v/L
        return 0
    
    @classmethod
    def vector_to_string(cls,v):
        '''
        把Vector变为string，方便放入dict
        '''
        return "x=" + str(v.x) + ",y=" + str(v.y) + ",z=" + str(v.z)
    
    @classmethod
    def calculate_angle_between_vectors(cls,v1,v2):
        ASIZE = cls.vector_calc_length(v1)
        BSIZE = cls.vector_calc_length(v2)
        D = ASIZE*BSIZE
        if D != 0:
            degree = math.acos(cls.vector_dot_product(v1,v2)/(ASIZE*BSIZE))
            #S = ASIZE*BSIZE*math.sin(degree)
            return degree
        return 0
    
    @classmethod
    def calculate_aggressive_normals(cls, mesh, config=None):
        """
        综合多种技术的突变法线计算

        config参数:
        - angle_threshold: 硬边角度阈值（度）
        - sharpness: 锐度参数（1.0-5.0）
        - distribution_power: 分布幂次（1.0-3.0）
        - use_edge_detection: 是否使用边缘检测
        """
        if config is None:
            config = {
                'angle_threshold': 80.0,
                'sharpness': 2.5,
                'distribution_power': 2.0,
                'use_edge_detection': True
            }

        # 第一步：构建顶点到面的映射
        vertex_to_faces = {}
        for poly in mesh.polygons:
            for vertex_index in poly.vertices:
                if vertex_index not in vertex_to_faces:
                    vertex_to_faces[vertex_index] = []
                vertex_to_faces[vertex_index].append(poly)

        # 第二步：计算每个面的原始法线
        face_normals = {}
        for poly in mesh.polygons:
            poly_verts = [mesh.vertices[i].co for i in poly.vertices]
            if len(poly_verts) >= 3:
                face_normal = cls.vector_cross_product(
                    poly_verts[1] - poly_verts[0],
                    poly_verts[2] - poly_verts[0]
                )
                face_normals[poly.index] = cls.vector_normalize(face_normal)

        # 第三步：根据配置计算最终顶点法线
        vertex_final_normals = {}

        for vertex_index, faces in vertex_to_faces.items():
            if not faces:
                continue

            # 收集相关面法线
            related_normals = []
            for poly in faces:
                if poly.index in face_normals:
                    related_normals.append(face_normals[poly.index])

            if not related_normals:
                continue
            
            # 方法1：简单平均
            avg_normal = sum(related_normals, Vector((0, 0, 0))) / len(related_normals)

            # 方法2：如果启用了边缘检测，检查角度差异
            if config['use_edge_detection'] and len(related_normals) > 1:
                angle_threshold_rad = math.radians(config['angle_threshold'])

                # 检查法线之间的最大角度差异
                max_angle_diff = 0
                for i in range(len(related_normals)):
                    for j in range(i+1, len(related_normals)):
                        angle = cls.calculate_angle_between_vectors(
                            related_normals[i], 
                            related_normals[j]
                        )
                        max_angle_diff = max(max_angle_diff, angle)

                # 如果角度差异大，使用加权平均，偏向角度大的面
                if max_angle_diff > angle_threshold_rad:
                    # 重新计算加权平均，权重为角度的幂次
                    weighted_sum = Vector((0, 0, 0))
                    total_weight = 0

                    for i, normal in enumerate(related_normals):
                        # 计算这个法线与其他法线的平均角度差
                        avg_angle_diff = 0
                        for j, other_normal in enumerate(related_normals):
                            if i != j:
                                angle = cls.calculate_angle_between_vectors(normal, other_normal)
                                avg_angle_diff += angle
                        avg_angle_diff /= (len(related_normals) - 1) if len(related_normals) > 1 else 1

                        # 权重为角度差的幂次，使差异大的法线权重更大
                        weight = (avg_angle_diff / angle_threshold_rad) ** config['sharpness']
                        weighted_sum += normal * weight
                        total_weight += weight

                    if total_weight > 0:
                        avg_normal = weighted_sum / total_weight

            # 对最终法线进行非线性变换
            def apply_nonlinear_transform(v, power=2.0):
                """应用非线性变换增强对比度"""
                # 分量符号
                sign_x = 1 if v.x >= 0 else -1
                sign_y = 1 if v.y >= 0 else -1
                sign_z = 1 if v.z >= 0 else -1

                # 绝对值幂次变换
                transformed = Vector((
                    (abs(v.x) ** power) * sign_x,
                    (abs(v.y) ** power) * sign_y,
                    (abs(v.z) ** power) * sign_z
                ))

                # 重新归一化
                length = cls.vector_calc_length(transformed)
                if length > 0:
                    return transformed / length
                return v

            # 应用非线性变换
            if config['distribution_power'] > 1.0:
                avg_normal = apply_nonlinear_transform(avg_normal, config['distribution_power'])

            vertex_final_normals[vertex_index] = cls.vector_normalize(avg_normal)

        return vertex_final_normals
    
    @classmethod
    def smooth_normal_save_to_uv(cls,obj,uvname):
        mesh = obj.data
        uvname = mesh.uv_layers.active.name

        mesh.calc_tangents(uvmap="TEXCOORD.xy")
        # 确保网格已经创建了所有必要的循环数据
        mesh.update(calc_edges=True)

        co_str_data_dict = {}

        # 开始
        for vertex in mesh.vertices:
                co = vertex.co
                co_str = cls.vector_to_string(co)
                co_str_data_dict[co_str] = []

        for poly in mesh.polygons:
            # 获取三角形的三个顶点
            loop_0 = mesh.loops[poly.loop_start]
            loop_1 = mesh.loops[poly.loop_start+1]
            loop_2 = mesh.loops[poly.loop_start + 2]

            # 获取顶点数据
            vertex_loop0 = mesh.vertices[loop_0.vertex_index]
            vertex_loop1 = mesh.vertices[loop_1.vertex_index]
            vertex_loop2 = mesh.vertices[loop_2.vertex_index]

            # 顶点数据转换为字符串格式
            co0_str = cls.vector_to_string(vertex_loop0.co)
            co1_str = cls.vector_to_string(vertex_loop1.co)
            co2_str = cls.vector_to_string(vertex_loop2.co)

            # 使用CorssProduct计算法线
            normal_vector = cls.vector_cross_product(vertex_loop1.co-vertex_loop0.co,vertex_loop2.co-vertex_loop0.co)
            # 法线归一化使其长度保持为1
            normal_vector = cls.vector_normalize(normal_vector)

            if co0_str in co_str_data_dict:
                w = cls.calculate_angle_between_vectors(vertex_loop2.co-vertex_loop0.co,vertex_loop1.co-vertex_loop0.co)
                co_str_data_dict[co0_str].append({"n":normal_vector,"w":w,"l":loop_0})
            if co1_str in co_str_data_dict:
                w = cls.calculate_angle_between_vectors(vertex_loop2.co-vertex_loop1.co,vertex_loop0.co-vertex_loop1.co)
                co_str_data_dict[co1_str].append({"n":normal_vector,"w":w,"l":loop_1})
            if co2_str in co_str_data_dict:
                w = cls.calculate_angle_between_vectors(vertex_loop1.co-vertex_loop2.co,vertex_loop0.co-vertex_loop2.co)
                co_str_data_dict[co2_str].append({"n":normal_vector,"w":w,"l":loop_2})

        # 存入UV
        uv_layer = mesh.uv_layers.get(uvname)
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start,poly.loop_start+poly.loop_total):
                vertex_index=mesh.loops[loop_index].vertex_index
                vertex = mesh.vertices[vertex_index]

                # 初始化平滑法线和平滑权重
                smoothnormal=Vector((0,0,0))
                weight = 0

                # 基于相邻面的法线加权平均计算平滑法线
                costr=cls.vector_to_string(vertex.co)

                if costr in co_str_data_dict:
                    a = co_str_data_dict[costr]
                    # 对于共享此顶点的所有面的数据，遍历它们
                    for d in a:
                        # 分别获取面的法线和权重
                        normal_vector=d['n']
                        w = d['w']
                        # 累加加权法线和权重
                        smoothnormal  += normal_vector*w
                        weight  += w
                if smoothnormal != Vector((0,0,0)):
                    smoothnormal /= weight
                    smoothnormal = cls.vector_normalize(smoothnormal)

                loop_normal = mesh.loops[loop_index].normal
                loop_tangent = mesh.loops[loop_index].tangent
                loop_bitangent = mesh.loops[loop_index].bitangent

                tx = cls.vector_dot_product(loop_tangent,smoothnormal)
                ty = cls.vector_dot_product(loop_bitangent,smoothnormal)
                tz = cls.vector_dot_product(loop_normal,smoothnormal)

                normalT=Vector((tx,ty,tz))
                # 游戏buf法线是翻转y后的，这里也处理一下
                uv = (normalT.x, 1 + normalT.y) 
                uv_layer.data[loop_index].uv = uv


    @staticmethod
    def normals_save_to_uv(obj:bpy.types.Object,uvname):
        """
            Saiku:
            增加普通法线写入uv,为了直观看到法线变化
        """
        mesh=obj.data
        # 确保网格已经创建了所有必要的循环数据
        mesh.update(calc_edges=True)
        uv_layer_xy = mesh.uv_layers.get(uvname)
        if uvname.replace(".xy",".zw") in mesh.uv_layers:
            uv_layer_zw = mesh.uv_layers.get(uvname.replace(".xy",".zw"))
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                vertex_index = mesh.loops[loop_index].vertex_index
                normal = mesh.vertices[vertex_index].normal
                if uv_layer_xy:
                    # 游戏buf法线是翻转y后的，这里也处理一下
                    uv = (normal.x, 1 + normal.y)
                    uv_layer_xy.data[loop_index].uv = uv
                if uv_layer_zw:
                    uv = (normal.z, 0) 
                    uv_layer_zw.data[loop_index].uv = uv


    @staticmethod
    def uv_load_to_normals(obj:bpy.types.Object, uvname):
        """从UV层读取数据并设置法线"""
        mesh = obj.data
        
        # 获取UV层
        uv_layer_xy = mesh.uv_layers.get(uvname)
        if uvname.replace(".xy",".zw") in mesh.uv_layers:
            uv_layer_zw = mesh.uv_layers.get(uvname.replace(".xy",".zw"))
        
        # 启用自定义法线
        mesh.use_auto_smooth = True
        if not mesh.has_custom_normals:
            mesh.create_normals_split()
        
        # 遍历所有循环顶点
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                # 从.xy层读取X,Y分量
                uv_xy = uv_layer_xy.data[loop_index].uv
                x = uv_xy.x
                y = uv_xy.y - 1.0  # 反向翻转Y分量
                
                # 从.zw层读取Z分量（如果存在）
                if uv_layer_zw:
                    uv_zw = uv_layer_zw.data[loop_index].uv
                    z = uv_zw.x
                else:
                    # 如果只有.xy层，计算Z分量（假设是单位向量）
                    z_squared = 1.0 - x*x - y*y
                    z = math.sqrt(max(0.0, z_squared))
                
                # 创建法线向量
                normal = (x, y, z)
                
                # 归一化
                length = math.sqrt(x*x + y*y + z*z)
                if length > 0:
                    normal = (x/length, y/length, z/length)
                
                # 设置自定义法线
                mesh.normals_split_custom_set([normal])


class MergeSplitObject:
    """
        按顶点组分离合并网格，将本属于同一个骨骼的不同名称的顶点组合并到一起
    """
    @staticmethod
    def get_boundary_vertices(obj:bpy.types.Object):
        """获取网格的边界顶点"""
        mesh = obj.data
        boundary_vertices = set()
        
        edge_count = defaultdict(int)
        for poly in mesh.polygons:
            for edge_key in poly.edge_keys:
                edge_count[edge_key]+=1
        
        for edge_key, count in edge_count.items():
            if count == 1:
                boundary_vertices.add(edge_key[0])
                boundary_vertices.add(edge_key[1])
        return boundary_vertices

    @staticmethod
    def get_vertex_weights(obj:bpy.types.Object, v_idx):
        """获取指定顶点的权重信息"""
        weight_dict = {}
        if v_idx < len(obj.data.vertices):
            vertex = obj.data.vertices[v_idx]
            vertex.select = True
            for vg in vertex.groups:
                group_name = obj.vertex_groups[vg.group].name
                weight_dict[group_name] = vg.weight
        #用权重排序
        sorted_items = sorted(weight_dict.items(), key=lambda x: x[1], reverse=True)
        # 分离为两个列表
        groups = [item[0] for item in sorted_items]
        weight = [item[1] for item in sorted_items]
        return groups,weight
    
    @staticmethod
    def calculate_vertices_center(obj:bpy.types.Object, vertex_indices):
        """
        计算一组顶点的中心点（平均位置）
        
        参数:
            obj: 网格对象
            vertex_indices: 顶点索引列表，如 [0, 1, 2, 3]
        
        返回:
            Vector: 中心点坐标
        """
        if not vertex_indices:
            return Vector((0, 0, 0))
        
        mesh = obj.data
        total = Vector((0, 0, 0))
        
        for v_idx in vertex_indices:
            if v_idx < len(mesh.vertices):
                total += mesh.vertices[v_idx].co
            else:
                print(f"顶点索引 {v_idx} 超出范围")
        
        center = total / len(vertex_indices)
        return center
    
    @staticmethod
    def calculate_max_radius(obj:bpy.types.Object, vertex_indices, center):
        """
        计算顶点到中心点的最大距离
        
        参数:
            obj: 网格对象
            vertex_indices: 顶点索引列表
            center: 中心点坐标 (Vector)
        
        返回:
            float: 最大半径
        """
        if not vertex_indices:
            return 0.0
        
        mesh = obj.data
        max_radius = 0.0
        
        for v_idx in vertex_indices:
            if v_idx < len(mesh.vertices):
                # 获取顶点世界坐标
                vertex_world_co = obj.matrix_world @ mesh.vertices[v_idx].co
                
                # 计算距离
                distance = (vertex_world_co - center).length
                
                # 更新最大值
                if distance > max_radius:
                    max_radius = distance
        
        return max_radius

    @staticmethod
    def split_vertex_groups(obj:bpy.types.Object):
        """
            按边界顶点的顶点组切分顶点组
        """
        #获取边界顶点索引
        boundary_vertices=MergeSplitObject.get_boundary_vertices(obj)
        vg_indices=defaultdict(list)
        #获取顶点索引的权重
        split_groups=[]
        """
            [
                {"group":group
                "weight":weight,
                "v_idxs":vg_indices,
                "center":center,
                "radius":radius,
                "group_size":size,
                }
            ]
        """
        temp_group_dict=defaultdict(dict)
        temp_weight_dict=defaultdict(list)
        for i in boundary_vertices:
            group,weight=MergeSplitObject.get_vertex_weights(obj,i)
            if len(weight)>0:
                temp_group_dict[str(group)]=group
                temp_weight_dict[str(group)].append({i:weight})
                vg_indices[str(group)].append(i)
        vg_keys=list(vg_indices.keys())
        vg_keys.sort()
        for vg in vg_keys:
            center=MergeSplitObject.calculate_vertices_center(obj,vg_indices[vg])
            radius=MergeSplitObject.calculate_max_radius(obj,vg_indices[vg],center)
            split_groups.append(dict({
                "group":temp_group_dict[vg],
                "weight":temp_weight_dict[vg],
                "v_idxs":vg_indices[vg],
                "center":center,
                "radius":radius,
                "group_size":len(temp_group_dict[vg])
            }))
        return split_groups

    @staticmethod
    def merge_object_by_vertex_groups(active_obj:bpy.types.Object,obj:bpy.types.Object)->bpy.types.Object:
        """
        # 匹配顶点组
        # 对顶点组改名
        # 复制一个新对象合并，并添加到当前集合
        """
        group_name_dict=defaultdict()

        #记录每个匹配顶点组的匹配顶点对和中心点，顶点对越多，中心点越近，置信度越高
        match_group_vertices_dict=defaultdict()
        merge_state=True #顶点组有冲突不合并
        active_obj_split_groups=MergeSplitObject.split_vertex_groups(active_obj)
        obj_split_groups=MergeSplitObject.split_vertex_groups(obj)
        for active_split_group in active_obj_split_groups:
            for split_group in obj_split_groups:
                if active_split_group["group_size"]==split_group["group_size"]:
                    #顶点组数量一致
                    active_center=active_split_group["center"]
                    active_radius=active_split_group["radius"]

                    center=split_group["center"]
                    radius=split_group["radius"]
                    #两个半径不能相差太多
                    min_radius=min(active_radius,radius)
                    max_radius=max(active_radius,radius)
                    if (active_center-center).length<max_radius and (max_radius/(min_radius+0.001))<2:
                        #中心点距离小于顶点组权重最小半径
                        #print(active_split_group["group"],split_group["group"])
                        match_vertex_pairs=[]#匹配位置非常靠近的顶点对
                        for active_obj_v_idx in active_split_group["v_idxs"]:
                            #开始验证顶点组匹配
                            for v_idx in split_group["v_idxs"]:
                                #验证条件 距离非常相近的顶点，数量越多置信度越高
                                if (active_obj.data.vertices[active_obj_v_idx].co-obj.data.vertices[v_idx].co).length<0.001:
                                    match_vertex_pairs.append((active_obj_v_idx,v_idx))
                        
                        if len(match_vertex_pairs)>1:
                            #默认两个顶点，至少要匹配一个面才行
                            #有对应的顶点对，开始匹配顶点组
                            
                            for i in range(0,len(active_split_group["group"])):
                                active_match_group_name = active_split_group["group"][i]
                                match_group_name = split_group["group"][i]
                                if active_match_group_name in group_name_dict:
                                    old_match_group_name=group_name_dict[active_match_group_name]
                                    old_match_pairs,old_center = match_group_vertices_dict[old_match_group_name]
                                    if group_name_dict[active_match_group_name]!=match_group_name:
                                        #顶点组冲突，看那个顶点比较多匹配那个
                                        # TODO 增加顶点权重比较。
                                        #比较顶点对,哪个多选那个，一样多则报错
                                        if (len(match_vertex_pairs)>len(old_match_pairs)) and ((active_center-center).length<(old_center-center).length):
                                            #print(match_vertex_pairs,old_match_pairs,center,old_center)
                                            print(f"update match: {active_match_group_name}:{old_match_group_name}->{match_group_name}")
                                            group_name_dict[active_match_group_name]=match_group_name
                                            match_group_vertices_dict[match_group_name]=[match_vertex_pairs,center]
                                        elif len(match_vertex_pairs)==len(old_match_pairs):
                                            print(f"conflict group name: {active_match_group_name}:{old_match_group_name} or {match_group_name}")
                                            merge_state=False
                                            break
                                elif match_group_name in active_match_group_name:
                                    # wci给骨骼增加了ib前缀，所以不可能会有不同ib的顶点组,
                                    # 若是出现则说明是同一个ib 或者已经合并过
                                    # 不用改名
                                    print(match_group_name,active_match_group_name)
                                    pass
                                else:
                                    print("match pair:",active_match_group_name,match_group_name)
                                    match_group_vertices_dict[match_group_name]=[match_vertex_pairs,center]
                                    group_name_dict[active_match_group_name]=match_group_name
        if merge_state:
            temp_obj=obj.copy()
            temp_obj.data=obj.data.copy()
            bpy.context.collection.objects.link(temp_obj)
            #开始改名
            rename_group_name_dict={}
            for vg in active_obj.vertex_groups:
                if vg.name in group_name_dict:
                    #默认,现在的数字索引名称在导出时需要，所以要记录
                    group_name=group_name_dict[vg.name]
                    active_obj.vertex_groups[vg.name].name=vg.name+","+group_name
                    rename_group_name_dict[group_name]=vg.name

            for vg in temp_obj.vertex_groups:
                if vg.name in rename_group_name_dict:
                    temp_obj.vertex_groups[vg.name].name=rename_group_name_dict[vg.name]
                

            # 取消选择所有
            bpy.ops.object.select_all(action='DESELECT')
            
            # 选择网格对象
            temp_obj.select_set(True)
            active_obj.select_set(True)
            
            bpy.context.view_layer.objects.active = active_obj
            
            # 合并
            bpy.ops.object.join()

            return active_obj
        else:
            return None
  
    @staticmethod
    def deselect_all_vertices(obj:bpy.types.Object):
        enterEditMode(obj)
        bpy.ops.mesh.select_all(action='DESELECT')
        selectAObject(obj)

    @staticmethod
    def invert_select_vertices(obj:bpy.types.Object):
        enterEditMode(obj)
        bpy.ops.mesh.select_all(action='INVERT')
        selectAObject(obj)

    @staticmethod
    def separate_object(obj: bpy.types.Object) -> List[bpy.types.Object]:
        """
            使用ops操作分离模型,比自己编写逻辑快
        """
        if obj.type != 'MESH':
            return []
        
        # 解析顶点组名称
        ib_to_vg_indices = defaultdict(list)
        ib_to_vg_names = defaultdict(list)

        for vg in obj.vertex_groups:
            parts = vg.name.split(",")
            for part in parts:
                if part:
                    try:
                        ib_hash, real_idx = part.split("_", 1)
                        ib_to_vg_indices[ib_hash].append(vg.index)
                        ib_to_vg_names[ib_hash].append(vg.name)
                    except:
                        continue
        
        splited_objects = []
        main_split_obj=obj

        for ib_hash in ib_to_vg_names:
            #改名
            main_split_obj.name=ib_hash+main_split_obj.name[8:]
            # 对每个分组执行分离操作
            MergeSplitObject.deselect_all_vertices(main_split_obj)
            selected_vertices=0
            for v_idx in range(0,len(obj.data.vertices)):
                vertex = obj.data.vertices[v_idx]
                for vg in vertex.groups:
                    group_name=main_split_obj.vertex_groups[vg.group].name
                    if ib_hash in group_name:
                        selected_vertices+=1
                        main_split_obj.data.vertices[v_idx].select=True
                        break
            if selected_vertices>0 and selected_vertices<len(main_split_obj.data.vertices):
                enterEditMode(main_split_obj)
                # 执行分离
                bpy.ops.mesh.separate(type='SELECTED')
                bpy.ops.object.mode_set(mode='OBJECT')
                #新对象才是分离后的模型，要做的就是
                all_selected = bpy.context.selected_objects
                for tmp_obj in all_selected:
                    if tmp_obj.name!=main_split_obj.name:
                        splited_objects.append(main_split_obj)
                        #这是当前ib_hash分离出顶点组的对象
                        #对顶点组进行改名
                        remove_vg_names=[]
                        for vg in tmp_obj.vertex_groups:
                            if ib_hash in vg.name:
                                vg.name=ib_hash+"_"+vg.name.split(ib_hash+"_")[1].split(",")[0]
                            else:
                                remove_vg_names.append(vg.name)
                        print(remove_vg_names)
                        for vg_name in remove_vg_names:
                            vg=tmp_obj.vertex_groups[vg_name]
                            tmp_obj.vertex_groups.remove(vg)
                        #将剩下的顶点组权重全部规格化
                        #if len(temp_obj.vertex_groups)>0:
                        #   bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False)
                    else:
                        main_split_obj=tmp_obj
                bpy.ops.object.select_all(action='DESELECT')
                bpy.context.view_layer.objects.active=main_split_obj
        return splited_objects    

class TangentCalculator:
    """切线计算工具类"""
    
    @staticmethod
    def calculate_tangents(mesh):
        """计算网格的切线（使用MikkTSpace算法）"""
        # Blender的calc_tangents使用MikkTSpace算法
        mesh.calc_tangents()
        
        # 收集切线数据
        tangents = []
        for loop in mesh.loops:
            tangent = loop.tangent
            bitangent_sign = loop.bitangent_sign
            # 返回(x, y, z, w)格式，w存储bitangent_sign
            tangents.append((tangent.x, tangent.y, tangent.z, bitangent_sign))
        
        return tangents
    
    @staticmethod
    def calculate_smooth_tangents(mesh):
        """计算平滑切线（顶点平均切线）"""
        # 先计算每面切线
        mesh.calc_tangents()
        
        # 初始化顶点切线累加器
        vertex_tangents = {}
        vertex_counts = {}
        
        # 遍历所有循环顶点
        for loop in mesh.loops:
            vertex_index = loop.vertex_index
            tangent = loop.tangent
            bitangent_sign = loop.bitangent_sign
            
            if vertex_index not in vertex_tangents:
                vertex_tangents[vertex_index] = [0.0, 0.0, 0.0, 0.0]
                vertex_counts[vertex_index] = 0
            
            # 累加切线（注意：需要处理bitangent_sign的一致性）
            vertex_tangents[vertex_index][0] += tangent.x
            vertex_tangents[vertex_index][1] += tangent.y
            vertex_tangents[vertex_index][2] += tangent.z
            # bitangent_sign平均（可能需要特殊处理）
            vertex_tangents[vertex_index][3] += bitangent_sign
            vertex_counts[vertex_index] += 1
        
        # 计算平均值并归一化
        smooth_tangents = []
        for vertex_index in range(len(mesh.vertices)):
            if vertex_index in vertex_tangents:
                count = vertex_counts[vertex_index]
                tx = vertex_tangents[vertex_index][0] / count
                ty = vertex_tangents[vertex_index][1] / count
                tz = vertex_tangents[vertex_index][2] / count
                tw = vertex_tangents[vertex_index][3] / count
                
                # 归一化切线向量
                length = math.sqrt(tx*tx + ty*ty + tz*tz)
                if length > 0:
                    tx /= length
                    ty /= length
                    tz /= length
                
                smooth_tangents.append((tx, ty, tz, tw))
            else:
                smooth_tangents.append((1.0, 0.0, 0.0, 1.0))  # 默认切线
        
        return smooth_tangents
    
    @staticmethod
    def tangent_save_to_uv(obj, uvname):
        """计算并保存切线到UV"""
        mesh = obj.data
        
        # 计算切线
        tangents = TangentCalculator.calculate_tangents(mesh)
        
        # 获取UV层
        uv_layer_xy = mesh.uv_layers.get(uvname)
        if uvname.replace(".xy",".zw") in mesh.uv_layers:
            uv_layer_zw = mesh.uv_layers.get(uvname.replace(".xy",".zw"))
        
        # 保存到UV
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                tangent = tangents[loop_index]
                tx, ty, tz, tw = tangent
                
                # 保存到.xy层（翻转Y）
                uv_xy = (tx, 1.0 + ty)
                uv_layer_xy.data[loop_index].uv = uv_xy
                
                # 如果有.zw层，保存Z和W分量
                if uv_layer_zw:
                    uv_zw = (tz, tw)
                    uv_layer_zw.data[loop_index].uv = uv_zw
    
    @staticmethod
    def smooth_tangent_save_to_uv(obj, uvname):
        """计算并保存平滑切线到UV"""
        mesh = obj.data
        
        # 确保有UV层
        
        # 获取UV层
        # 获取UV层
        uv_layer_xy = mesh.uv_layers.get(uvname)
        if uvname.replace(".xy",".zw") in mesh.uv_layers:
            uv_layer_zw = mesh.uv_layers.get(uvname.replace(".xy",".zw"))
        else:
            uv_layer_zw =None
        
        # 计算平滑切线
        smooth_tangents = TangentCalculator.calculate_smooth_tangents(mesh)
        
        # 建立顶点到切线的映射
        vertex_tangents = {}
        for loop in mesh.loops:
            vertex_index = loop.vertex_index
            vertex_tangents[vertex_index] = smooth_tangents[vertex_index]
        
        # 保存到UV
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                loop = mesh.loops[loop_index]
                vertex_index = loop.vertex_index
                
                tx, ty, tz, tw = vertex_tangents[vertex_index]
                
                # 保存到.xy层（翻转Y）
                uv_xy = (tx, 1.0 + ty)
                uv_layer_xy.data[loop_index].uv = uv_xy
                
                # 如果有.zw层，保存Z和W分量
                if uv_layer_zw:
                    uv_zw = (tz, tw)
                    uv_layer_zw.data[loop_index].uv = uv_zw

    @staticmethod
    def uv_load_to_tangents(obj, uvname):
        """从UV读取数据并设置切线"""
        mesh = obj.data
        
        # 确保有UV层
        # 获取UV层
        uv_layer_xy = mesh.uv_layers.get(uvname)
        if uvname.replace(".xy",".zw") in mesh.uv_layers:
            uv_layer_zw = mesh.uv_layers.get(uvname.replace(".xy",".zw"))
        
        # 创建自定义切线数据层（Blender不直接支持自定义切线，需要通过其他方式）
        # 这里我们创建一个顶点颜色层来存储切线数据，然后在着色器中使用
        
        # 创建顶点颜色层存储切线
        tan_color_name = f"TANGENT_{uvname}"
        if tan_color_name not in mesh.vertex_colors:
            mesh.vertex_colors.new(name=tan_color_name)
        
        tan_color_layer = mesh.vertex_colors[tan_color_name]
        
        # 遍历所有循环顶点
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                # 从.xy层读取切线X,Y分量
                uv_xy = uv_layer_xy.data[loop_index].uv
                tx = uv_xy.x
                ty = uv_xy.y - 1.0  # 反向翻转Y分量
                
                # 从.zw层读取切线Z分量和W分量（bitangent_sign）
                if uv_layer_zw:
                    uv_zw = uv_layer_zw.data[loop_index].uv
                    tz = uv_zw.x
                    tw = uv_zw.y
                else:
                    # 如果只有.xy层，计算Z分量（假设是单位向量）
                    tz_squared = 1.0 - tx*tx - ty*ty
                    tz = math.sqrt(max(0.0, tz_squared))
                    tw = 1.0  # 默认bitangent_sign
                
                # 归一化切线向量
                length = math.sqrt(tx*tx + ty*ty + tz*tz)
                if length > 0:
                    tx /= length
                    ty /= length
                    tz /= length
                
                # 将切线编码到顶点颜色（RGBA）
                # R,G,B存储切线向量，A存储bitangent_sign
                # 注意：需要将[-1,1]范围映射到[0,1]
                color_r = (tx + 1.0) * 0.5
                color_g = (ty + 1.0) * 0.5
                color_b = (tz + 1.0) * 0.5
                color_a = (tw + 1.0) * 0.5  # tw通常是±1，映射到[0,1]
                
                tan_color_layer.data[loop_index].color = (
                    color_r, color_g, color_b, color_a
                )



class VertexGroupProcessor:
    """顶点组数据处理工具"""
    
    @staticmethod
    def get_vertex_group_data(mesh, vertex_index, max_groups=4):
        """获取顶点的顶点组数据（索引和权重）"""
        vertex = mesh.vertices[vertex_index]
        groups = vertex.groups
        
        # 按权重排序
        sorted_groups = sorted(groups, key=lambda g: g.weight, reverse=True)
        
        # 限制数量
        groups_to_use = sorted_groups[:max_groups]
        
        # 提取索引和权重
        indices = []
        weights = []
        
        for group in groups_to_use:
            indices.append(group.group)
            weights.append(group.weight)
        
        # 填充到固定长度
        while len(indices) < max_groups:
            indices.append(0)
            weights.append(0.0)
        
        # 归一化权重（确保总和为1）
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        return indices, weights
    
    @staticmethod
    def encode_weights_to_uv(weights):
        """将4个权重编码到UV坐标"""
        # 将4个权重映射到2个UV坐标
        # 方案1：前2个权重作为UV.xy，后2个作为UV.zw
        # 方案2：使用编码算法压缩
        # 这里采用简单方案：w1,w2作为U,V
        
        if len(weights) >= 2:
            # 直接使用前两个权重
            u = weights[0] if len(weights) > 0 else 0.0
            v = weights[1] if len(weights) > 1 else 0.0
        else:
            u = weights[0] if len(weights) > 0 else 0.0
            v = 0.0
        
        return (u, v)


    @staticmethod
    def encode_indices_to_uv(indices):
        """将4个索引编码到UV坐标"""
        # 索引是整数，需要编码到[0,1]范围
        # 假设索引范围在0-255之间（8位）
        
        if len(indices) >= 2:
            # 将索引归一化到[0,1]
            u = indices[0] / 255.0 if len(indices) > 0 else 0.0
            v = indices[1] / 255.0 if len(indices) > 1 else 0.0
        else:
            u = indices[0] / 255.0 if len(indices) > 0 else 0.0
            v = 0.0
        
        return (u, v)

    
    @staticmethod
    def blendweight_save_to_uv(obj, uvname):
        """保存顶点组权重到UV"""
        mesh = obj.data
        
        # 检查顶点组数量
        if len(mesh.vertices) == 0:
            return
        
        #总顶点组只有2个
        vertex_groups = obj.vertex_groups
        if len(vertex_groups)>2:
            return 
        
        # 检查第一个顶点的顶点组数量（假设所有顶点类似）
        # 获取UV层
        uv_layer_xy = mesh.uv_layers.get(uvname)
        if uvname.replace(".xy",".zw") in mesh.uv_layers:
            uv_layer_zw = mesh.uv_layers.get(uvname.replace(".xy",".zw"))

        # 处理每个顶点
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                loop = mesh.loops[loop_index]
                vertex_index = loop.vertex_index
                
                # 获取顶点组权重
                indices, weights = VertexGroupProcessor.get_vertex_group_data(mesh, vertex_index, max_groups=2)
                
                # 编码到UV
                uv = VertexGroupProcessor.encode_weights_to_uv(weights)
                
                # 保存到UV
                uv_layer_xy.data[loop_index].uv = uv
    
    @staticmethod
    def blendindice_save_to_uv(obj, uvname):
        """保存顶点组索引到UV"""
        mesh = obj.data
        
        if len(mesh.vertices) == 0:
            return
        
        #总顶点组只有2个
        vertex_groups = obj.vertex_groups
        if len(vertex_groups)>2:
            return 
        
        # 获取UV层
        uv_layer_xy = mesh.uv_layers.get(uvname)
        if uvname.replace(".xy",".zw") in mesh.uv_layers:
            uv_layer_zw = mesh.uv_layers.get(uvname.replace(".xy",".zw"))
        
        # 处理每个顶点
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                loop = mesh.loops[loop_index]
                vertex_index = loop.vertex_index
                
                # 获取顶点组索引
                indices, weights = VertexGroupProcessor.get_vertex_group_data(mesh, vertex_index, max_groups=2)
                
                # 编码到UV
                uv = VertexGroupProcessor.encode_indices_to_uv(indices)
                
                # 保存到UV
                uv_layer_xy.data[loop_index].uv = uv

    @staticmethod
    def uv_load_to_blendindices(obj, uvname):
        """从UV读取数据并创建顶点组索引"""
        mesh = obj.data
        
        # 获取UV层
        uv_layer_xy = mesh.uv_layers.get(f"{uvname}.xy")
        
        if not uv_layer_xy:
            print(f"UV层 {uvname}.xy 不存在")
            return
        
        # 清除现有的顶点组（可选）
        while obj.vertex_groups:
            obj.vertex_groups.remove(obj.vertex_groups[0])
        
        # 创建顶点组
        # 先创建一定数量的顶点组（例如8个）
        num_groups = 8
        vertex_groups = []
        for i in range(num_groups):
            vg_name = f"BI_{uvname}_{i}"
            vg = obj.vertex_groups.new(name=vg_name)
            vertex_groups.append(vg)
        
        # 解码函数：从UV坐标解码索引
        def decode_indices_from_uv(u, v):
            """从UV坐标解码顶点组索引"""
            # 简单解码：将U,V映射到顶点组索引
            # 假设U,V在[0,1]范围，映射到[0,num_groups-1]
            idx1 = int(u * (num_groups - 1))
            idx2 = int(v * (num_groups - 1))
            
            # 限制范围
            idx1 = max(0, min(num_groups - 1, idx1))
            idx2 = max(0, min(num_groups - 1, idx2))
            
            return [idx1, idx2, 0, 0]  # 前两个索引有效
        
        # 处理每个顶点
        vertex_indices_cache = {}
        
        # 收集每个顶点的索引数据
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                loop = mesh.loops[loop_index]
                vertex_index = loop.vertex_index
                
                # 从UV读取数据
                uv = uv_layer_xy.data[loop_index].uv
                u, v = uv.x, uv.y
                
                # 解码索引
                indices = decode_indices_from_uv(u, v)
                
                if vertex_index not in vertex_indices_cache:
                    vertex_indices_cache[vertex_index] = {
                        'indices_sum': [0, 0, 0, 0],
                        'count': 0
                    }
                
                for i in range(4):
                    vertex_indices_cache[vertex_index]['indices_sum'][i] += indices[i]
                vertex_indices_cache[vertex_index]['count'] += 1
        
        # 解码权重：根据索引分配权重
        # 简单方案：给每个索引分配固定权重
        for vertex_index in range(len(mesh.vertices)):
            if vertex_index in vertex_indices_cache:
                count = vertex_indices_cache[vertex_index]['count']
                if count > 0:
                    # 计算平均索引（取整）
                    avg_indices = [
                        int(round(vertex_indices_cache[vertex_index]['indices_sum'][i] / count))
                        for i in range(4)
                    ]
                    
                    # 为每个索引分配权重
                    # 简单分配：前两个索引各0.5权重
                    weights = [0.5, 0.5, 0.0, 0.0]
                    
                    # 应用权重
                    for i in range(2):  # 只处理前两个索引
                        if 0 <= avg_indices[i] < num_groups:
                            vertex_groups[avg_indices[i]].add([vertex_index], weights[i], 'REPLACE')

    @staticmethod
    def uv_load_to_blendweights(obj, uvname):
        """从UV读取数据并创建顶点组权重"""
        mesh = obj.data
        
        # 获取UV层
        uv_layer_xy = mesh.uv_layers.get(f"{uvname}.xy")
        
        if not uv_layer_xy:
            print(f"UV层 {uvname}.xy 不存在")
            return
        
        # 清除现有的顶点组（根据需求）
        # 如果需要保留现有顶点组，可以跳过这一步
        while obj.vertex_groups:
            obj.vertex_groups.remove(obj.vertex_groups[0])
        
        # 创建顶点组（最多4个）
        vertex_groups = []
        for i in range(4):
            vg_name = f"BW_{uvname}_{i}"
            vg = obj.vertex_groups.new(name=vg_name)
            vertex_groups.append(vg)
        
        # 解码函数：从UV坐标解码权重
        def decode_weights_from_uv(u, v):
            """从UV坐标解码权重"""
            # 简单解码：直接使用U,V作为前两个权重
            # 更复杂的解码可能需要处理编码方案
            weights = [u, v, 0.0, 0.0]
            
            # 归一化（确保总和为1）
            total = sum(weights)
            if total > 0:
                weights = [w/total for w in weights]
            
            return weights
        
        # 处理每个顶点
        vertex_weights_cache = {}
        
        # 首先收集每个顶点的所有权重值
        for poly in mesh.polygons:
            for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                loop = mesh.loops[loop_index]
                vertex_index = loop.vertex_index
                
                # 从UV读取数据
                uv = uv_layer_xy.data[loop_index].uv
                u, v = uv.x, uv.y
                
                # 解码权重
                weights = decode_weights_from_uv(u, v)
                
                # 如果顶点有多个循环，取平均值
                if vertex_index not in vertex_weights_cache:
                    vertex_weights_cache[vertex_index] = {
                        'weights_sum': [0.0, 0.0, 0.0, 0.0],
                        'count': 0
                    }
                
                for i in range(4):
                    vertex_weights_cache[vertex_index]['weights_sum'][i] += weights[i]
                vertex_weights_cache[vertex_index]['count'] += 1
        
        # 应用权重到顶点组
        for vertex_index in range(len(mesh.vertices)):
            if vertex_index in vertex_weights_cache:
                count = vertex_weights_cache[vertex_index]['count']
                if count > 0:
                    # 计算平均权重
                    avg_weights = [
                        vertex_weights_cache[vertex_index]['weights_sum'][i] / count
                        for i in range(4)
                    ]
                    
                    # 归一化
                    total = sum(avg_weights)
                    if total > 0:
                        avg_weights = [w/total for w in avg_weights]
                    
                    # 分配到顶点组（只添加非零权重）
                    for i in range(4):
                        if avg_weights[i] > 0.001:  # 忽略太小的权重
                            vertex_groups[i].add([vertex_index], avg_weights[i], 'REPLACE')



#将属性写入UV
def attributes_save_to_uv(attr_name: str):
    """将顶点属性保存到UV层"""
    
    print(attr_name)
    for obj in bpy.context.selected_objects:
        if obj.type != 'MESH':
            continue
            
        mesh = obj.data
        
        # 获取当前活动的UV层名称
        if not mesh.uv_layers.active:
            print(f"对象 {obj.name} 没有UV层")
            continue
            
        uvname = mesh.uv_layers.active.name
        
        if attr_name == VERTEX_ATTRIBUTES.NORMAL:
            SmoothNormal.normals_save_to_uv(obj,uvname)
        
        elif attr_name == VERTEX_ATTRIBUTES.SMOOTH_NORMAL:
            # 计算平滑法线并保存到UV
            SmoothNormal.smooth_normal_save_to_uv(obj, uvname)
        
        elif attr_name == VERTEX_ATTRIBUTES.TANGENT:
            # 计算切线并保存到UV
            TangentCalculator.tangent_save_to_uv(obj, uvname)
        
        elif attr_name == VERTEX_ATTRIBUTES.SMOOTH_TANGENT:
            # 计算平滑切线并保存到UV
            TangentCalculator.smooth_tangent_save_to_uv(obj, uvname)
        
        elif attr_name == VERTEX_ATTRIBUTES.BLENDWEIGHT:
            # 保存顶点组权重到UV
            VertexGroupProcessor.blendweight_save_to_uv(obj, uvname)
        
        elif attr_name == VERTEX_ATTRIBUTES.BLENDINDICE:
            # 保存顶点组索引到UV
            VertexGroupProcessor.blendindice_save_to_uv(obj, uvname)
        
        else:
            print(f"未知属性类型: {attr_name}")

#从UV加载数据
def uv_load_to_attributes(attr_name:str):
    for obj in bpy.context.selected_objects:
        mesh = obj.data
        uvname = mesh.uv_layers.active.name
        if attr_name==VERTEX_ATTRIBUTES.NORMAL:
            # uv数据存入法线
            SmoothNormal.uv_load_to_normals(obj,uvname)
        elif attr_name==VERTEX_ATTRIBUTES.SMOOTH_NORMAL:
            pass
        elif attr_name==VERTEX_ATTRIBUTES.TANGENT:
            TangentCalculator.uv_load_to_tangents(obj,uvname)
        elif attr_name==VERTEX_ATTRIBUTES.SMOOTH_TANGENT:
            pass
        elif attr_name==VERTEX_ATTRIBUTES.BLENDWEIGHT:
            VertexGroupProcessor.uv_load_to_blendweights(obj,uvname)
        elif attr_name==VERTEX_ATTRIBUTES.BLENDINDICE:
            #不能有顶点组
            VertexGroupProcessor.uv_load_to_blendindices(obj,uvname)


def set_active_collection_to_objects_collection(operator):
    """设置活动集合为活动对象所在的集合"""

    def find_layer_collection(layer_coll, collection_name):
        """递归查找层集合"""
        if layer_coll.name == collection_name:
            return layer_coll
        
        for child in layer_coll.children:
            found = find_layer_collection(child, collection_name)
            if found:
                return found
    active_obj = bpy.context.active_object
    selected_objs = bpy.context.selected_objects
    if not active_obj:
        if len(selected_objs)>0:
            active_obj=selected_objs[0]
        else:
            operator.report({"ERROR"},"没有活动对象！")
            return False
    
    # 获取对象所在的第一个集合
    if not active_obj.users_collection:
        operator.report({"ERROR"},f"对象 '{active_obj.name}' 不在任何集合中")
        return False
    
    target_coll = active_obj.users_collection[0]
    
    # 设置活动集合
    view_layer = bpy.context.view_layer
    layer_coll = find_layer_collection(
        view_layer.layer_collection, 
        target_coll.name
    )
    
    if layer_coll:
        view_layer.active_layer_collection = layer_coll
        operator.report({"INFO"},f"已设置活动集合为: {target_coll.name}")
        return True
    else:
        operator.report({"ERROR"},f"找不到集合 '{target_coll.name}' 的层集合")
        return False
    

def is_collection_truly_empty(collection):
    """
    递归判断集合是否真正为空：自身无对象，且所有子集合也递归为空。
    """
    # 如果当前集合有对象，则不为空
    if len(collection.objects) > 0:
        return False
    
    # 检查所有子集合
    for child in collection.children:
        if not is_collection_truly_empty(child):
            return False
    
    # 自身无对象，且所有子集合递归为空
    return True

import mathutils
from .constants import Game
#根据不同游戏对游戏的模型进行调整
def normalize_object(obj:bpy.types.Object,axis_y=False,output=False):
    game=bpy.context.scene.wci_props.game
    if game=="":
        return obj
    scale_mat = mathutils.Matrix.Scale(1, 4) #缩放为1
    rot_mat = mathutils.Matrix.Rotation(math.radians(0), 4, 'X')
    if output:
        #export
        # 构建变换矩阵
        if game in [Game.WUWA]:
            rot_mat = mathutils.Matrix.Rotation(math.radians(180), 4, 'Z')  # z轴180度
            scale_mat = mathutils.Matrix.Scale(100, 4)
        elif game in [Game.GI]:
            rot_mat = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X')  # x 轴90度
        if axis_y:
            rot_mat = rot_mat @ mathutils.Matrix.Rotation(math.radians(-90), 4, 'X')  #绕X轴旋转-90度
    else:
        #import 
        if game in [Game.WUWA]:
            # 构建变换矩阵
            rot_mat = mathutils.Matrix.Rotation(math.radians(180), 4, 'Z')  # z 轴180度
            scale_mat = mathutils.Matrix.Scale(0.01, 4) # 0.01缩放
        elif game in [Game.GI]:
            rot_mat = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')  # x 轴90度        

    matrix = rot_mat @ scale_mat
    obj.matrix_world @= matrix

    for selected_obj in bpy.context.selectable_objects:
        deselectObject(selected_obj)
    selectAObject(obj)
    bpy.ops.object.transform_apply(location=True,rotation=True, scale=True)
    if game in [Game.WUWA]:
        #WuWa需要翻转法线
        obj.data.flip_normals()
    return obj



