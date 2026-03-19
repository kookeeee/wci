
import bpy
import struct
import os
import time
import json
import numpy as np
import traceback
from collections import defaultdict
from typing import List,Dict,Tuple,Any,Set

from .format import DXGIFormater
from ..tool_functions import normalize_object
from ..utils import get_normalized_name,get_keys_by_toggle,format_size
from .utils import WciLayoutElement,read_binary_buffer,compute_d2_histogram

# ---------- 主导入类 ----------
class ModelImporter:
    def __init__(self, json_path:str, ib_path:str):
        self.json_path:str = json_path
        self.ib_path:str = ib_path
        self.data:Dict[str,Any] = None #analysis.json
        self.group_indices = set()  #顶点组索引
        self.vertices = []  # 存储所有顶点数据
        self.faces = defaultdict(dict)     # 存储所有面
        self.d2:List = []   # d2的直方图，用来与lod模型对比
        self.materials:Dict[str,bpy.types.Material] = {} # 存储材质信息
        self.alias_semantic_names=[]
        self.elements:List[WciLayoutElement]=[]

    def init_vertex_data(self,semantic):
        if semantic.startswith("POSITION"):
            return (0.0, 0.0, 0.0)
        elif semantic.startswith("NORMAL"):
            return (0.0, 0.0, 0.0)
        elif semantic.startswith("TANGENT"):
            return (0.0, 0.0, 0.0, 1.0)
        elif semantic.startswith("COLOR"):
            return (0.0, 0.0, 0.0, 1.0)
        elif semantic.startswith("TEXCOORD"):
            return (0.0,0.0)
        elif semantic.startswith("BLENDWEIGHT"):
            return (0.0, 0.0, 0.0, 0.0)
        elif semantic.startswith("BLENDINDICE"):
            return (0, 0, 0, 0)

        
    def load_json(self):
        """加载JSON配置文件"""
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"JSON文件不存在: {self.json_path}")
        
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        #进行数据校验
        for buf in self.data:
            if "metadata" in self.data[buf]:
                for buf_info in self.data[buf]["metadata"]:
                    if "metadata" in buf_info and "file" in buf_info:
                        if len(buf_info["metadata"]["elements"])==0:
                            raise Exception("alanysis.json信息缺失: "+self.json_path)
                        else:
                            for elem in buf_info["metadata"]["elements"]:
                                wciLayoutElement=WciLayoutElement(elem)
                                self.elements.append(wciLayoutElement)
    
    def process_vertex_buffers(self):
        """加载所有顶点缓冲区"""
        self.vertices=[]

        # 处理每个顶点缓冲区
        # 先进行顶点数校验和elemnts排列
        
        vertex_count=-1
        bufs=list(self.data.keys())
        bufs.remove("ib")
        bufs.sort()
        for buf_name in bufs:
            for fmt in self.data[buf_name]["fmts"]:
                #fmt用来区分不同的buf文件，每一个fmt代表一个buf文件
                #一个slot中可能有多个fmt
                if "file" not in fmt:
                    continue
                file_path = os.path.join(self.ib_path, fmt['file'])
                metadata = fmt['metadata']
                # 读取缓冲区数据
                buffer = read_binary_buffer(file_path)
                if buffer == None:
                    continue
                if vertex_count==-1:
                    vertex_count=len(buffer)//metadata["stride"]
                elif vertex_count!=len(buffer)//metadata["stride"]:
                    raise Exception("缓冲区文件顶点不一致，导入失败!",fmt["file"])
                for element in metadata["elements"]:
                    init_val=self.init_vertex_data(element["SemanticName"])
                    if len(self.vertices)==0:
                        self.vertices=[{element["AliasSemanticName"]:init_val} for _ in range(vertex_count)]
                    else:
                        for i in range(vertex_count):
                            self.vertices[i][element["AliasSemanticName"]]=init_val
                for elem in metadata['elements']:
                    element=WciLayoutElement(elem)
                    elem_type = element.type
                    alias_semantic=element.AliasSemanticName
                    self.alias_semantic_names.append(alias_semantic)
                    formatter =  element.decode_formatter
                    # 为每个顶点解析该属性
                    for v_idx in range(vertex_count):
                        #字节码
                        value = element.parse_vertex_attribute(buffer,v_idx,metadata["stride"])
                        if value is None:
                            continue
                        # 根据语义存储数据
                        if elem_type == "position":
                            self.vertices[v_idx][alias_semantic] = formatter(value)
                        elif elem_type == "normal":
                            self.vertices[v_idx][alias_semantic] = formatter(value,z_normal=self.data["ib"]["z-normal"])
                        elif elem_type == "tangent":
                            self.vertices[v_idx][alias_semantic] = formatter(value)
                        elif elem_type == "color":
                            self.vertices[v_idx][alias_semantic] = formatter(value)
                        elif elem_type == "texcoord":
                            xy,zw=formatter(value)
                            self.vertices[v_idx][alias_semantic+".xy"] = xy
                            self.vertices[v_idx][alias_semantic+".zw"] = zw
                        elif elem_type == "blendweight":
                            ivalue=formatter(value)
                            if len(ivalue)<4:
                                ivalue =  element.pad(ivalue,0.0)   
                            self.vertices[v_idx][alias_semantic] = ivalue
                        elif elem_type == "blendindice":
                            ivalue=formatter(value)
                            self.group_indices.update(ivalue)
                            ivalue = element.pad(ivalue,0)
                            self.vertices[v_idx][alias_semantic] = ivalue
    
    def process_index_buffer(self):
        ib_info = self.data['ib']
        for key, submesh_info in ib_info['info'].items():
            alias=ib_info["info"][key]["alias"]
            self.faces[alias]=[]
            
            # 读取索引文件
            file_path = os.path.join(self.ib_path, submesh_info['file'])
            buffer = read_binary_buffer(file_path)  # 整个文件
            
            if buffer is None:
                continue
            # 解析
            fmt=submesh_info["metadata"]["format"]
            fmt_char, elem_size,val_size = format_size(fmt)
            count_indices=len(buffer)//elem_size
            # 读取所有索引
            indices = []
            for i in range(count_indices):
                start = i * elem_size
                end = start + elem_size
                if end > len(buffer):
                    break
                
                idx_data = buffer[start:end]
                try:
                    idx = struct.unpack(fmt_char, idx_data)[0]
                    indices.append(idx)
                except struct.error:
                    print(f"索引解包失败: 位置 {start}")
                    break
            
            # 构建三角面
            triangle_count = count_indices // 3
            for i in range(triangle_count):
                if i * 3 + 2 >= len(indices):
                    break
                face = (indices[i * 3], indices[i * 3 + 1], indices[i * 3 + 2])
                self.faces[alias].append(face)

    def create_obj(self,
                   ib_hash:str,
                   ib_alias:str,
                   name:str,
                   alias_semantic_names:List[str],
                   faces:List[List[int]],
                   vertices:List[Dict[str,float]]):
        mesh_name=get_normalized_name(ib_hash,ib_alias,name)
        mesh = bpy.data.meshes.new(f"{mesh_name}_mesh")
        obj = bpy.data.objects.new(mesh_name, mesh)
        positions = [v['POSITION'][:3] for v in vertices]  # 只取 x,y,z 给 Blender
        mesh.from_pydata(positions, [], faces)
        mesh.update()
        
        for alias_semantic_name in alias_semantic_names:
            if alias_semantic_name.startswith("NORMAL"):
                # 设置法线
                normals = [v[alias_semantic_name] for v in vertices]
                if normals is None:
                    if hasattr(mesh, 'calc_normals'):
                        mesh.calc_normals()
                    continue
                elif bpy.app.version >= (4, 1):
                    mesh.normals_split_custom_set_from_vertices(normals)
                else:                        
                    # 准备循环法线数据
                    # 根据vertex_ids映射法线到每个循环
                    # 应用法线与平滑
                    for poly in mesh.polygons:
                        poly.use_smooth = True

                    loop_normals = []
                    for i, loop in enumerate(mesh.loops):
                        vid = loop.vertex_index  # 循环关联的顶点索引
                        mesh.loops[i].normal=normals[vid]
                        if 0 <= vid < len(normals):
                            normal = normals[vid]
                        else:
                            normal = (0.0, 0.0, 1.0)
                        loop_normals+=normal
    
            elif alias_semantic_name.startswith("TANGENT"):
                if any(v[alias_semantic_name] != (0.0, 0.0, 0.0) for v in vertices):
                    tangents=[v[alias_semantic_name] for v in vertices]
                    tan_attr = mesh.attributes.new(name=alias_semantic_name, type='FLOAT_VECTOR', domain='POINT')
                    tan_attr.data.foreach_set("vector", [val for t in tangents for val in t[:3]])
            
            elif alias_semantic_name.startswith("COLOR"):
                # 设置顶点颜色
                if any(v[alias_semantic_name] != (0.0, 0.0, 0.0, 1.0) for v in vertices):
                    color_layer = mesh.vertex_colors.new(name=alias_semantic_name)
                    for poly in mesh.polygons:
                        for loop_idx in poly.loop_indices:
                            vert_idx = mesh.loops[loop_idx].vertex_index
                            color = vertices[vert_idx][alias_semantic_name]
                            color_layer.data[loop_idx].color = color
            elif alias_semantic_name.startswith("TEXCOORD"):
                # 设置UV坐标
                xy_uv_name=alias_semantic_name+".xy"
                zw_uv_name=alias_semantic_name+".zw"
                xy_uv=[v[xy_uv_name] for v in vertices]
                zw_uv=[v[zw_uv_name] for v in vertices]
                if any(xy != (0,0) for xy in xy_uv):
                    uv_layer = mesh.uv_layers.new(name=xy_uv_name)
                    for poly in mesh.polygons:
                       for loop_idx in poly.loop_indices:
                            vert_idx = mesh.loops[loop_idx].vertex_index
                            uv_layer.data[loop_idx].uv = xy_uv[vert_idx] 
                if any(zw != (0,0) for zw in zw_uv):
                    uv_layer = mesh.uv_layers.new(name=zw_uv_name)
                    for poly in mesh.polygons:
                       for loop_idx in poly.loop_indices:
                            vert_idx = mesh.loops[loop_idx].vertex_index
                            uv_layer.data[loop_idx].uv = zw_uv[vert_idx]
            elif alias_semantic_name.startswith("BLENDINDICE"):
                # 设置 混合权重和索引
                suf = alias_semantic_name.replace("BLENDINDICE","")
                index_str = suf.replace("S","")
                if len(index_str)>0:
                    index=int(index_str)
                else:
                    index = 0

                blend_weights_name="BLENDWEIGHT"+suf
                if True:
                    groups = list(self.group_indices)
                    groups.sort()
                    for i in range(0,groups[-1]+1):
                        vertex_group = obj.vertex_groups.new(name=ib_hash+"_"+str(i))
                        
                    for poly in mesh.polygons:
                        for loop_idx in poly.loop_indices:
                            vert_idx = mesh.loops[loop_idx].vertex_index
                            #没有blendweights说明只有一个顶点组
                            if blend_weights_name not in self.alias_semantic_names:
                                #默认值填充
                                weight=(1,0,0,0)
                            else:
                                weight=vertices[vert_idx][blend_weights_name]
                            bones=vertices[vert_idx][alias_semantic_name]
                            b_info=list(zip(bones,weight))
                            for b_id, w in b_info:
                                if w > 0.001:
                                    grp = obj.vertex_groups.get(f"{ib_hash}_{b_id}") or obj.vertex_groups.new(name=f"{ib_hash}_{b_id}")
                                    grp.add([vert_idx], w, 'REPLACE')
        return obj
    
    def create_blender_objs(self,collection_name = None):
        """在Blender中创建网格"""
        ib_hash=self.data["ib"]["hash"]
        alias_semantic_names:List[str]=list(set(self.alias_semantic_names))
        alias_semantic_names.sort()
        # 创建网格和对象
        objs=[]
        collection = bpy.data.collections.new(ib_hash)
        if collection_name is not None:
            parent_collection = bpy.data.collections.get(collection_name)
            if parent_collection is not None:
                parent_collection.children.link(collection)
            else:
                bpy.context.scene.collection.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)
        for key in self.data["ib"]["info"]: 
            alias=self.data["ib"]["info"][key]["alias"]
            if "exports" not in self.data["ib"]["info"][key]:
                exports=[
                    {
                        "name":"",
                        "toggle":"",
                        "first_index":0,
                        "index_count":len(self.faces[alias])*3,
                    }
                ]
            else:
                exports=self.data["ib"]["info"][key]["exports"]    
            for export in exports:
                    first_index = export["first_index"]//3
                    index_count = export["index_count"]//3
                    name = export["name"]
                    toggle = export["toggle"]
                    vertices = []
                    faces = []
                    max_value = max(max(item) for item in self.faces[alias][first_index:first_index+index_count])
                    min_value = min(min(item) for item in self.faces[alias][first_index:first_index+index_count])
                    vertices=self.vertices[min_value:max_value+1]
                    for face in self.faces[alias][first_index:first_index+index_count]:
                        v1,v2,v3=face
                        faces.append((v1-min_value,v2-min_value,v3-min_value))
                    if len(vertices)<=0:
                        #没有顶点或者面
                        continue
                    else:
                        obj = self.create_obj(ib_hash,alias,name,alias_semantic_names,faces,vertices)
                        collection.objects.link(obj)
                        if "slot" in self.data["ib"]["info"][key]:
                            self.create_material(obj,ib_hash,alias,self.data["ib"]["info"][key]["slot"])
                        normalize_object(obj)
                    if len(toggle)>0 and "if" in toggle:
                        key_bindings = get_keys_by_toggle(toggle)
                        if hasattr(obj,'wci_key_bindings'):
                            for keyboard in key_bindings:
                                key_info = key_bindings[keyboard]
                                obj.wci_key_bindings.add_binding(
                                    keyboard=keyboard,
                                    swap=",".join(sorted(key_info["swap"])),
                                    is_ctrl=key_info["is_ctrl"],
                                    is_shift=key_info["is_shift"],
                                    is_alt=key_info["is_alt"],
                                    is_or=key_info["is_or"],
                                    default=0,
                                )                                        
                                # 设置新添加的项为活动项
                                obj.wci_key_bindings.active_index = len(obj.wci_key_bindings.items) - 1
                    objs.append(obj)
        return objs
    
    def create_material(self, obj:bpy.types.Object,ib_hash:str,sub_alias:str,slot_info:Dict[str,Dict[str,str]]):
        """创建材质并关联纹理"""
        mat_name = f"Mat_{ib_hash}-{sub_alias}"
        if mat_name in self.materials:
            mat=self.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            self.materials[mat_name]=mat
            mat.use_nodes = True
        
            # 清除默认节点
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()
            
            # 创建节点
            output = nodes.new(type='ShaderNodeOutputMaterial')
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            output.location = (300, 0)
            principled.location = (0, 0)
            links.new(principled.outputs['BSDF'], output.inputs['Surface'])
            
            # 添加纹理
            last_node = principled
            x_offset = -300
            
            for slot_key, tex_info in slot_info.items():
                tex_file = tex_info.get('file')
                texname = tex_info.get('name')
                tex_file=tex_file[0:-4]+".jpg"
                if not tex_file:
                    continue
                
                tex_path = os.path.join(self.ib_path, tex_file)
                if not os.path.exists(tex_path):
                    continue
                
                # 创建纹理节点
                tex_node = nodes.new(type='ShaderNodeTexImage')
                tex_node.location = (x_offset, 0)
                x_offset -= 300

                tex_image = bpy.data.images.load(tex_path, check_existing=True)
                tex_image.reload()
                tex_node.image = tex_image

                # 确保图片不被打包
                tex_image.source = 'FILE'
                    
                # 根据纹理类型连接
                if 'Diffuse' in texname:
                    links.new(tex_node.outputs["Color"], principled.inputs['Base Color'])                
                last_node = tex_node
                print(f"  添加纹理: {tex_file}")
        obj.data.materials.append(mat)
    
    def import_model(self,operator,collection_name:str = None):
        """主导入函数"""
        try:
            # 加载JSON配置
            self.load_json()
            t=time.time()
            # 处理顶点数据
            self.process_vertex_buffers()
            # 处理索引数据
            self.process_index_buffer()
            # 创建Blender网格
            objs = self.create_blender_objs(collection_name=collection_name)
            return True
            
        except Exception as e:
            traceback.print_exc()
            operator.report({"ERROR"},f"导入失败: {e}!")
            return False

    def calculate_d2(self):
        self.d2 = compute_d2_histogram(self.vertices,self.faces, 
                         num_samples=1024,
                         num_pairs=10000,
                         bins=64)

    def import_model_raw(self):
        try:
            # 加载JSON配置
            self.load_json()
            # 处理顶点数据
            self.process_vertex_buffers()
            # 处理索引数据
            self.process_index_buffer()

            self.calculate_d2()
        except Exception as e:
            self.vertices = {}
            self.faces = {}
            self.d2 = []
            pass 