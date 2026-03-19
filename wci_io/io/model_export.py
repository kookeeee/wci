
import bpy
import struct
import os
import time
import json
import numpy as np
import traceback
from mathutils import Vector
from collections import defaultdict
from typing import List,Dict,Tuple,Any
import bmesh
from functools import partial

from .format import DXGIFormater
from ..tool_functions import normalize_object
from ..utils import parse_obj_name,format_size
from ..constants import EXPORT_TYPE,WCI_BASE_CONST,Game,FOLDER_NAME
from .utils import WciLayoutElement,VertexWriteBuffer
from .utils import smooth_normals,smooth_normals_by_angle

# ---------- 主导出类 ----------
class ModelExporter:
    def __init__(self, operator:bpy.types.Operator,game,buf_path:str):
        self.data:Dict[str,Any] = None
        self.buf_path:str = buf_path
        self.game = game
        self.objects:List[bpy.types.Object] = []
        self.ib_objs:Dict[str,List[bpy.types.Object]] = {} 
        self.operator:bpy.types.Operator = operator
        self.z_normal=False #记录是不是压缩法线
        self.elements:Dict[str,WciLayoutElement]={}



    def load_analysis_json(self,ib):
        """加载JSON配置"""
        json_path = os.path.join(self.buf_path, ib, "analysis.json")
        if os.path.isfile(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.z_normal = self.data['ib'].get('z-normal', False)
            for buf in self.data.keys():
                if "ib" == buf:
                    continue
                else:
                    #生成带顺序的elements列表，
                    for buf_info in self.data[buf]["fmts"]:
                        if "file" not in buf_info:
                            continue
                        else:
                            fmt=buf_info["metadata"]
                            element_info=fmt["elements"]
                            for elem in element_info:
                                wciLayoutElement=WciLayoutElement(elem)
                                self.elements[wciLayoutElement.name]=wciLayoutElement
        else:
            self.operator.report({"ERROR"},f"analysis.json 不存在，在{ib}中")
            return False
        return True

    def clear_analysis_json(self):
        self.data = None
        self.z_normal=False
        self.elements={}

    def evaluated_mesh(self,obj:bpy.types.Object,remove_vertex_groups,export_y_axis):
        #复制一个临时对象，所有的修改都在临时对象上生效
        temp_obj = obj.copy()
        temp_obj.data = obj.data.copy()  # 复制数据
        bpy.context.collection.objects.link(temp_obj)
        # 应用所有形态键
        bpy.context.selected_objects.clear()
        bpy.context.view_layer.objects.active=temp_obj
        if temp_obj.data.shape_keys is not None:
            bpy.ops.object.shape_key_remove(all=True,apply_mix=True)
        
        # 应用所有修改器
        for modifier in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=modifier.name) 
                                   
        if len(remove_vertex_groups)>0:
            # 删除指定的顶点组
            for vg_name in remove_vertex_groups:
                vg=temp_obj.vertex_groups[vg_name]
                #operator.report({'INFO'}, "删除顶点组："+vg_name)
                temp_obj.vertex_groups.remove(vg)
            #将剩下的顶点组权重全部规格化
            if len(temp_obj.vertex_groups)>0:
                bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False)
        
        #修改temp_obj向上轴改为y轴
        if export_y_axis:
            temp_obj=normalize_object(temp_obj,axis_y=True,output=True)
        else:
            temp_obj=normalize_object(temp_obj,axis_y=False,output=True)
        #获取最终网格，处理剩下的uv孤岛数据
        mesh=temp_obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        if mesh is None:
            raise ValueError("Failed to create temporary mesh")
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        temp_data=temp_obj.data
        bpy.data.objects.remove(temp_obj, do_unlink=True)
        bpy.data.meshes.remove(temp_data)
        return mesh
    
    def merge_mesh(self,obj:bpy.types.Object,name:str,src_mesh:bpy.types.Mesh,des_mesh:bpy.types.Mesh,start_vertex:int,start_index:int,base_start_vertex,export_type:str):

        index_count= len(src_mesh.polygons)
        vertex_count= len(src_mesh.vertices)
        obj.wci_exports.add_item(
            base_start_vertex = base_start_vertex,
            start_index = start_index,
            index_count = index_count,
            vertex_count = vertex_count,
            start_vertex = start_vertex,
            name=name,
            export_type = export_type,
        )
        #将mesh合并到并记录信息
        if des_mesh==None:
            des_mesh=src_mesh.copy()
        else:
            # 创建一个bmesh来合并网格
            bm = bmesh.new()
            bm.from_mesh(des_mesh)
            # 将评估结果添加到bmesh中
            bm.from_mesh(src_mesh)
            # 更新目标网格
            bm.to_mesh(des_mesh)
            bm.free()

        start_index += index_count
        start_vertex += vertex_count
        return des_mesh,start_index,start_vertex

    def merge_objects(self,objs:List[bpy.types.Object]):
        """合并同一个ib的所有网格数据"""
        ib_hash=self.data["ib"]["hash"]
        export_y_axis = bpy.context.scene.wci_props.export_y_axis
        start_index=0
        start_vertex=0
        target_mesh=None
        old_sub_alias="1"
        for obj in objs:
            #默认在第0帧导出
            bpy.context.scene.frame_set(0)
            obj.wci_exports.clear_all()#先清空。
            sub_ib_hash,sub_alias,item_name=parse_obj_name(obj.name)
            if ib_hash!=sub_ib_hash:
                continue
            if old_sub_alias!=sub_alias:
                start_index=0
            old_sub_alias=sub_alias  
            #复制一个临时对象，所有的修改都在临时对象上生效
            temp_obj = obj.copy()
            temp_obj.data = obj.data.copy()  # 复制数据
            bpy.context.collection.objects.link(temp_obj)
            # 清空旋转，缩放，位置，为后续位置转换做准备
            temp_obj.location=(0,0,0)
            temp_obj.rotation_euler=(0,0,0)
            temp_obj.scale=(1,1,1)
            
            #记录所有需要导出的形态键
            wci_shapekey_list=[]
            if temp_obj.data.shape_keys is not None:
                shape_keys = temp_obj.data.shape_keys.key_blocks
                # 遍历形态键
                for key in shape_keys:
                    if key.name[0:len(WCI_BASE_CONST.WCI_SHAPEKEY_PREFIX)]==WCI_BASE_CONST.WCI_SHAPEKEY_PREFIX:
                        wci_shapekey_list.append(key.name)
                        # 将形态键值设置为其初始值
                        key.value = key.slider_min
            
            #顶点组处理，记录导出时删除WCI_B_开头的顶点组,删除合并的顶点组，没有{ib_hash}_的顶点组
            remove_vertex_groups=[] #记录要移除的顶点组
            for vg in temp_obj.vertex_groups:
                if WCI_BASE_CONST.WCI_BONE_PREFIX in vg.name or f"{ib_hash}_" not in vg.name:
                    remove_vertex_groups.append(vg.name)

            #顶点组改名
            max_bone_index = -1
            temp_bones:set=set()
            for vg in temp_obj.vertex_groups:
                if f"{ib_hash}_" in vg.name:
                    #改名成数字顶点组，默认数字顶点组不影响骨骼权重？有谁会用原本的顶点组制作骨骼然后制作动画吗，好像没有
                    new_name=vg.name.split(f"{ib_hash}_")[1].split(",")[0]
                    temp_obj.vertex_groups[vg.name].name=new_name
                    #一定是可以int转换的，不能说明顶点组有问题
                    temp_bones.add(new_name.strip())
                    max_bone_index = max(max_bone_index,int(vg.name))
                    # 设想是一个网格进行初始化的，但是最终会有很多个网格，而且同样名称的索引不一样。暂时保留这个逻辑
                    # 由程序自动对顶点组进行填充
            # 填充顶点组
            if max_bone_index>-1:
                bpy.context.selected_objects.clear()
                bpy.context.view_layer.objects.active=temp_obj
                temp_obj.update_from_editmode()

                missing = set([f"{i}" for i in range(max_bone_index + 1)]) - temp_bones
                for number in missing:
                    temp_obj.vertex_groups.new(name=f"{number}")
                bpy.ops.object.vertex_group_sort()
            #获取评估网格
            temp_mesh=self.evaluated_mesh(temp_obj,remove_vertex_groups,export_y_axis)
            #更新目标mesh和开始索引
            base_vertex_index = start_vertex
            target_mesh,start_index, start_vertex = self.merge_mesh(obj,obj.name,temp_mesh,target_mesh,start_vertex,start_index,base_vertex_index,EXPORT_TYPE.MESH)
            if hasattr(obj,"wci_motion"):
                wci_motion = obj.wci_motion
                if wci_motion.is_motion:
                    #设置当前帧，然后遍历生成
                    start_frame= wci_motion.start_frame
                    end_frame = wci_motion.end_frame
                    bpy.context.scene.frame_start=start_frame
                    bpy.context.scene.frame_end=end_frame
                    #从第0帧移动，防止物理效果没有缓存导致解算失败
                    for i in range(0,start_frame+1):
                        bpy.context.scene.frame_set(i)
                    for i in range(start_frame,end_frame+1):
                        bpy.context.scene.frame_set(i)
                        #获取评估网格
                        temp_mesh = self.evaluated_mesh(temp_obj,remove_vertex_groups,export_y_axis)
                        #更新目标mesh和开始索引
                        target_mesh, start_index, start_vertex = self.merge_mesh(obj,obj.name+f"_frame={i}",temp_mesh,target_mesh,start_vertex, start_index,base_vertex_index,EXPORT_TYPE.FRAME_MESH)
            #默认第0帧导出   
            bpy.context.scene.frame_set(0)
            if hasattr(obj,"wci_shapekey"):
                wci_shapekey = obj.wci_shapekey
                if wci_shapekey.export_shapekey and temp_obj.data.shape_keys:
                    #设置形态键
                    #所有形态键遍历一次
                    for i  in range(0,len(wci_shapekey_list)):
                        #设置对应的wci的形态键为最大值
                        shapekey_name=wci_shapekey_list[i]
                        shape_keys = temp_obj.data.shape_keys.key_blocks
                        # 遍历形态键
                        for key in shape_keys:
                            if key.name in wci_shapekey_list:
                                if key.name == shapekey_name:
                                    key.value = key.slider_max
                                else:
                                    key.value = key.slider_min
                        #只设置一个导出形态键为最大值
                        temp_mesh=self.evaluated_mesh(temp_obj,remove_vertex_groups,export_y_axis)
                        #更新目标mesh和索引
                        target_mesh,start_index,start_vertex = self.merge_mesh(obj,obj.name+"_shapekey="+shapekey_name,temp_mesh,target_mesh,start_vertex, start_index,base_vertex_index,EXPORT_TYPE.SHAPEKEY_MESH)

            temp_data=temp_obj.data
            bpy.data.objects.remove(temp_obj, do_unlink=True)
            bpy.data.meshes.remove(temp_data)
        # 计算切线
        target_mesh.calc_tangents()

        return target_mesh
      

    def init_vertices(self,mesh:bpy.types.Mesh):
        """顶点数据初始化"""        
        vertices = mesh.vertices
        loops = mesh.loops
        vertex_count = len(vertices)
        loop_count = len(loops)

        # 构建相同位置顶点到所有loop索引的映射
        vert_loop_indices:defaultdict[int,List[int]]=defaultdict(list)
        for i, loop in enumerate(loops):
            vert_loop_indices[loop.vertex_index].append(i)

        
        vertex_coords = [None] * vertex_count
        for i, v in enumerate(vertices):
            vertex_coords[i] = (v.co.x, v.co.y, v.co.z)

        # 预计算平均法线
        avg_normals = np.empty((loop_count, 3), dtype=np.float32)

        avg_tangents = np.empty((loop_count, 4), dtype=np.float32)
        if self.game in [Game.GI,Game.HI3]:
            # 原神将平滑法线存到切线里面了，且切线的w分量为 -1
            avg_normals,avg_tangents = smooth_normals(vertices, loops)

        else:
            #_,avg_tangents = smooth_normals_by_angle(vertices, loops,angle_threshold=180)
            #avg_normals,_ = smooth_normals(vertices, loops)
            #直接用第一个loop的法线和切线
            for v_idx in range(vertex_count):
                loop_indices = vert_loop_indices[v_idx]
                if len(loop_indices)>0:
                    loop_idx= loop_indices[0]
                    n_avg =np.array(loops[loop_idx].normal)
                    avg_normals[v_idx] = n_avg
                    avg_tangents[v_idx][0:3] =np.array(loops[loop_idx].tangent[:3],dtype=float)
                    avg_tangents[v_idx][3] = loops[loop_idx].bitangent_sign

        # 顶点组处理
        vertex_groups_data = []
        for v in vertices:
            groups = v.groups
            if groups:
                group_data = sorted(groups, key=lambda x: x.weight, reverse=True)
                # 按权重排序
                vertex_groups_data.append(group_data)
            else:
                vertex_groups_data.append([])

        # UV处理,只存elements中存在的uv名称
        uv_data_cache = {}
        if mesh.uv_layers:
            for uv_layer in mesh.uv_layers:
                # 直接创建列表,通过uv
                uv_list = []
                for uv in uv_layer.data:
                    uv_list.append((uv.uv.x, uv.uv.y))
                uv_data_cache[uv_layer.name] = uv_list
        
        color_data_cache = {}
        if mesh.vertex_colors:
            for color_layer in mesh.vertex_colors:
                color_list = []
                for color in color_layer.data:
                    #每个loop的color
                    color_list.append(color)
                color_data_cache[color_layer.name] = color_list
        
        # 批量处理顶点
        indexed_vertices = [None] * vertex_count
        
        uv_data_cache_get = uv_data_cache.get
        
        for v_idx in range(vertex_count):
            vertex = {}
            position=vertex_coords[v_idx]
            if len(vert_loop_indices[v_idx])>0:
                loop_idx = vert_loop_indices[v_idx][0]
            else:
                loop_idx = 0

            # 获取顶点组数据
            groups = vertex_groups_data[v_idx]
            
            for elem_name in self.elements:
                element = self.elements[elem_name]
                elem_type = element.type
                formatter = element.encode_formatter
                elem_name = element.name
                if elem_type == 'position':
                    value = element.pad(position, 1.0)
                    vertex[elem_name] = formatter(value)
                    
                elif elem_type == 'normal':
                    vertex[elem_name] = formatter(Vector(avg_normals[v_idx]),Vector(avg_tangents[v_idx][0:3]),avg_tangents[v_idx][3],z_normal=self.z_normal)
                    
                elif elem_type == 'tangent':
                    value = avg_tangents[v_idx]
                    vertex[elem_name] = formatter(value)
                    
                elif elem_type == 'color':
                    elem = self.elements[elem_name]
                    if elem_name in mesh.vertex_colors:
                        value = color_data_cache[elem_name][loop_idx]
                    vertex[elem_name] = formatter(value)
                    
                elif elem_type == 'blendindice':
                    #会有多于4根骨骼的情况，那就需要index_offset
                    elem = self.elements[elem_name]
                    index_offset = getattr(elem, 'indexOffset', 0)
                    indices = [0, 0, 0, 0]
                    for i in range(index_offset,index_offset+4):
                        if i < len(groups):
                            indices[i] = groups[i].group
                    vertex[elem_name] = formatter(tuple(indices))
                    
                elif elem_type == 'blendweight':
                    elem = self.elements[elem_name]
                    index_offset = getattr(elem, 'indexOffset', 0)
                    weights = [0.0, 0.0, 0.0, 0.0]
                    total = 0.0
                    for i in range(index_offset,index_offset+4):
                        if i < len(groups):
                            weight=groups[i].weight
                            weights[i] = weight
                            total += weight
                    # 归一化
                    if total > 0:
                        weights = [w/total for w in weights]
                    
                    vertex[elem_name] = formatter(tuple(weights))
                    
                elif elem_type == 'texcoord':
                    elem = self.elements[elem_name]
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
                    
                    # 填充
                    while len(uvs) < 4:
                        uvs.append(0.0)
                    vertex[elem_name] = formatter(uv=uvs)
            
            indexed_vertices[v_idx] = vertex
        return indexed_vertices

    def export_vertices_buffers(self, vertices,elements, output_path):
        """导出顶点缓冲区"""
        
        bufs=list(self.data.keys())
        bufs.remove("ib")
        buffers:Dict[str,VertexWriteBuffer]={}#是名称和
        vertex_count=len(vertices)
        self.data["ib"]["vertex_count"]=int(vertex_count)
        #初始化，将WriteBuffer改造成字典，通过elementName调用
        for buf in bufs:
            for buf_info in self.data[buf]["fmts"]:
                if "file" not in buf_info:
                    continue
                metadata=buf_info["metadata"]
                elements=[WciLayoutElement(element) for element in metadata["elements"]]
                output_file = os.path.join(output_path, self.data["ib"]["hash"] + buf_info["suf"])
                vwb=VertexWriteBuffer(output_file,elements,metadata["stride"],vertex_count)
                buffers[buf_info["suf"]]=vwb
                for elem in elements:
                    buffers[elem.name]=vwb
        
        #遍历顶点
        for v_idx in range(0,len(vertices)):
            vertex = vertices[v_idx]
            #获取writebuffer
            for elementName in vertex:
                # 写入缓冲区
                writeBuffer=buffers[elementName]
                writeBuffer.write_byte_data(elementName,v_idx,vertex[elementName])
            
        # 写入文件
        for buf in bufs:
            for buf_info in self.data[buf]["fmts"]:
                if "file" not in buf_info:
                    continue
                buffers[buf_info["suf"]].save()
                buffer_path=buffers[buf_info["suf"]].buffer_path
                #print(f"导出： {buffer_path}")
    
    def export_index_buffers(self, faces, output_path):
        """导出索引缓冲区（基于循环）"""
        ib_info = self.data['ib']
        all_index_count = 0
        # 按起始索引排序
        keys=[]
        for key in ib_info["info"]:
            keys.append((key,ib_info["info"][key]["alias"]))
        keys = sorted(keys, key=lambda x: int(x[1]))
        for key,sub_alias in keys:
            self.data["ib"]["info"][key]["metadata"]["format"]="DXGI_FORMAT_R32_UINT"
            half_ib=self.data["ib"]["hash"] + f"-{sub_alias}"
            output_file = os.path.join(output_path, half_ib + self.data["ib"]["suf"])


            #索引初始化
            indices=0
            for obj in self.ib_objs[self.data["ib"]["hash"]]:
                for export_item in obj.wci_exports.items:
                    if half_ib in export_item.name:
                        indices+= export_item.index_count
            print(f"export：{half_ib}: {output_file}")           
            # 编码索引
            fmt_char, elem_size, val_size= format_size("DXGI_FORMAT_R32_UINT")
            buffer = bytearray(indices*3 * elem_size)
            for i in range(0,indices):
                base_start=i*3*elem_size
                face_index=all_index_count+i
                buffer[base_start+(elem_size*0):base_start+(elem_size*1)] = struct.pack(fmt_char, faces[face_index][0])
                buffer[base_start+(elem_size*1):base_start+(elem_size*2)] = struct.pack(fmt_char, faces[face_index][1])
                buffer[base_start+(elem_size*2):base_start+(elem_size*3)] = struct.pack(fmt_char, faces[face_index][2])
            all_index_count+=indices
            # 写入文件
            with open(output_file, 'wb') as f:
                f.write(buffer)
        # 保存更新后的JSON
        buf_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
        export_json_path = os.path.join(buf_path, self.data["ib"]["hash"], "analysis_export.json")
        
        with open(export_json_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def export_buffers(self,ib_hash:str,mesh:bpy.types.Mesh, output_path):
        indexed_vertices = self.init_vertices(mesh)   
        #存储三角面索引
        faces = [[] for i in range(0,len(mesh.loop_triangles))]
        for i,tri in enumerate(mesh.loop_triangles):
            faces[i]=[tri.vertices[0], tri.vertices[1], tri.vertices[2]]

        # 导出顶点缓冲区
        self.export_vertices_buffers(indexed_vertices,self.elements,output_path)
            
        # 导出索引缓冲区
        self.export_index_buffers(faces,output_path)

        return True
                

    def export_model(self, ib_objs:Dict[str,List[bpy.types.Object]]):
        """主导出函数"""
        # 创建输出目录
        output_path = os.path.join(self.buf_path, FOLDER_NAME.BUFFER)
        os.makedirs(output_path, exist_ok=True)
        # 按ib分类对象
        self.ib_objs = ib_objs
        output_count=0
        for ib in self.ib_objs:
            try:
                objs=self.ib_objs[ib]
                if self.load_analysis_json(ib):
                    t = time.time()
                    mesh=self.merge_objects(objs)
                    #print(f"merge objects speed time:",format(time.time()-t,".6f")+"s")
                    t = time.time()
                    if self.export_buffers(ib,mesh,output_path):
                        #print(f"export buffer speed time:",format(time.time()-t,".6f")+"s")
                        output_count+=1
                self.clear_analysis_json()
            except Exception as e:
                traceback.print_exc()
                self.operator.report({"ERROR"},f"{ib}导出失败:{e}")
                return False
        if output_count>0:
            self.operator.report({"INFO"},f"导出成功!")
            return True
        else:
            self.operator.report({"INFO"},f"导出对象数量为0,跳过生成！")
            return False
