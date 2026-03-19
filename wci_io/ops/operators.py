import os
import shutil
import bpy
import os
import re
import json
from  bpy_extras.io_utils import ImportHelper
from collections import defaultdict

from gettext import pgettext
from ..constants import WCI_BASE_CONST, FOLDER_NAME,Game
from ..analysis.analysis import analysis_dumps
from ..generate.generate import ModGenerater
from ..io.model_export import ModelExporter
from ..io.model_import import ModelImporter
from ..tool_functions import separateByMaterials,MergeSplitObject,attributes_save_to_uv,uv_load_to_attributes
from ..tool_functions import set_active_collection_to_objects_collection,is_collection_truly_empty
from ..utils import parse_obj_name,DEFAULT_ITEM_NAME

from ..auto_register import auto_register
from ..locale.translations import auto_translate



@auto_register  
@auto_translate
class WciRenameBoneOperator(bpy.types.Operator):
    bl_idname="wci.tool_rename_bone"
    bl_label="重命名对称骨骼"
    bl_description = "将骨骼及顶点组用 .L,.R格式重命名，让blender可以自动识别"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls,context):
        if context.object and context.object.type=='ARMATURE':
            return True
        else:
            return False
    
    def execute(self, context):
        #将骨骼重命名为.R .L这种命名风格
        bone_change_sum=0
        vg_change_sum=0
        rename_bone_dict={}
        #存储所有骨骼原名称与改名后的名称
        if context.object.type=="ARMATURE":
            for bone in context.object.data.bones:
                boneName=bone.name.upper()
                if " L" in boneName or "_L" in boneName or "-L" in boneName:
                    rename_bone_dict[bone.name]=bone.name.replace(" L","").replace("_L","").replace("-L","")+".L"
                    bone.name = rename_bone_dict[bone.name]
                    bone_change_sum+=1
                if " R" in boneName or "_R" in boneName or "-R" in boneName:
                    #需要对骨骼进行扭转，这里就不操作，有问题自己改吧
                    rename_bone_dict[bone.name]=bone.name.replace(" R","").replace("_R","").replace("-R","")+".R"
                    bone.name = rename_bone_dict[bone.name]
                    bone_change_sum+=1
            for obj in context.object.children_recursive:
                if obj.type=="MESH":
                    for group in obj.vertex_groups:
                        if group.name in rename_bone_dict:
                            group.name = rename_bone_dict[group.name]
                            vg_change_sum+=1
            self.report({'INFO'}, f"已改名：骨骼{bone_change_sum}个,顶点组{vg_change_sum}个")
        return {'FINISHED'} 

@auto_register 
@auto_translate
class WciChangeWciBoneNameOperator(bpy.types.Operator):
    bl_idname = "wci.tool_bone_rename"
    bl_label = f"重命名为{WCI_BASE_CONST.WCI_BONE_PREFIX}前缀骨骼"
    bl_description = f"给所有骨骼添加{WCI_BASE_CONST.WCI_BONE_PREFIX}前缀,用以WCI识别，导出时会应用骨架后自动移除这些带前缀的骨骼顶点组."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls,context):
        if context.object and context.object.type=='ARMATURE':
            return True
        else:
            return False


    def execute(self, context):
        #修改非数字骨骼名称及顶点组
        bone_change_sum=0
        vg_change_sum=0
        if context.object.type=="ARMATURE":
            for bone in context.object.data.bones:
                if not bone.name.isdigit() and WCI_BASE_CONST.WCI_BONE_PREFIX not in bone.name:
                    bone.name = WCI_BASE_CONST.WCI_BONE_PREFIX+bone.name
                    bone_change_sum+=1
            for obj in context.object.children_recursive:
                if obj.type=="MESH":
                    for group in obj.vertex_groups:
                        if not group.name.isdigit() and WCI_BASE_CONST.WCI_BONE_PREFIX not in group.name:
                            group.name = WCI_BASE_CONST.WCI_BONE_PREFIX+group.name
                            vg_change_sum+=1
            self.report({'INFO'}, f"已重命名：骨骼{bone_change_sum}个,顶点组{vg_change_sum}个")
        return {'FINISHED'}


@auto_register 
@auto_translate
class WciCopy3DMAttributes2MeshOperator(bpy.types.Operator):
    bl_idname = "wci.tool_copy_migoto_attributes_to_mesh"
    bl_label = "复制属性到网格"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls,context):
        if len(context.selected_objects)>1:
            return True
        else:
            return False
        
    def execute(self, context):
        active_obj=context.active_object
        ib_hash,sub_alias,item_name=parse_obj_name(active_obj.name)
        for select_obj in context.selected_objects:
            if select_obj is not active_obj:
                s_ib_hash,s_sub_alias,s_item_name=parse_obj_name(select_obj.name)
                for key, value in active_obj.items():
                    if key != '_RNA_UI':
                        if key == "wci_key_bindings":
                            if context.scene.wci_props.copy_key_bindings:
                                select_obj[key] = value
                        else:
                            select_obj[key] = value

                if context.scene.wci_props.copy_name:
                    if s_item_name!=None:
                        if s_item_name == DEFAULT_ITEM_NAME:
                            select_obj.name=f"{ib_hash}-{sub_alias}.vb"
                        else:
                            select_obj.name=f"{ib_hash}-{sub_alias}.vb.{s_item_name}"
                    else:
                        select_obj.name=f"{ib_hash}-{sub_alias}.vb.{select_obj.name}"
                    select_obj.data.name=select_obj.name
        self.report({'INFO'}, "已复制")
        return {'FINISHED'}   


@auto_register 
@auto_translate
class WciOutputMeshTextureOperator(bpy.types.Operator):
    bl_idname="wci.tool_output_texture"
    bl_label ="网格贴图命名导出"

    @classmethod
    def poll(cls,context):
        if context.object and context.object.type=='MESH':
            return True
        else:
            return False


    def execute(self, context):
        #导出网格diffuse材质为dds，需要有blender_dds_addon插件
        buf_path = bpy.path.abspath(context.scene.wci_props.buf_path)
        tex_encode = context.scene.wci_props.tex_encode
        try:
            import inspect
            script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
            script_dir = os.path.dirname(os.path.dirname(script_path))
            from blender_dds_addon.ui.export_dds import save_dds # type:ignore
            from blender_dds_addon.directx.texconv import Texconv,unload_texconv# type:ignore
            from blender_dds_addon.astcenc.astcenc import Astcenc,unload_astcenc# type:ignore
        except:
            self.report({"ERROR"},"请先安装blender_dds_addon插件再点击导出!")
            return {"FINISHED"}
        if os.path.isdir(buf_path):
            # 遍历所有选定的对象
            output_path=os.path.join(buf_path,FOLDER_NAME.TEXTURE)
            os.makedirs(output_path,exist_ok=True)
            ib_alias_dict={} #ib_hash:ib_alias
            for obj in bpy.context.selected_objects:
                if obj.type == 'MESH':
                    ib_hash,sub_alias,item_name =parse_obj_name(obj.name)
                    if ib_hash:
                        #有ib_hash则添加ib_hash别名前缀，没有则直接输出
                        if ib_hash in ib_alias_dict:
                            ib_alias=ib_alias_dict[ib_hash]
                        else:
                            # 为什么使用别名，是为了在游戏ib改变的时候原始数据命名基本不用做什么修改
                            # 遵循原始数据来自原始文件开发原则，以ib作为唯一查询方式
                            with open(os.path.join(buf_path,ib_hash,"analysis.json"),"r",encoding="utf-8") as f:
                                data=json.loads(f.read())
                            ib_alias=data["ib"]["alias"]
                            ib_alias_dict[ib_hash]=ib_alias
                        #去掉.001,.002的后缀和空格
                        widgetname = item_name.strip().split(".")[0]
                        suffix=ib_alias+"-"+widgetname
                    else:
                        widgetname = obj.name.strip().split(".")[0]
                        suffix = widgetname
                    #复制默认的dds到output
                    resource_path=os.path.join(script_dir,"dds",context.scene.wci_props.game)
                    print(resource_path)
                    if os.path.isdir(resource_path):
                        for file in os.listdir(resource_path):
                            file_path=os.path.join(resource_path,file)
                            dds_path=os.path.join(output_path,suffix+file)
                            if os.path.isfile(dds_path):
                                continue
                            else:
                                if os.path.isfile(file_path):
                                    shutil.copyfile(file_path,dds_path)
                    if not context.scene.wci_props.export_diffuse:
                        #不输出diffuse
                        continue
                    #只选取第一个材质
                    if obj.material_slots and len(obj.material_slots)>0:
                        material=obj.material_slots[0].material
                        if material and material.use_nodes:
                            nodes = material.node_tree.nodes
                            links = material.node_tree.links
                            # 查找基础色输入
                            bsdf_node = next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)
                            if bsdf_node is None:
                                bsdf_node=next((node for node in nodes if node.type == '原理化BSDF'), None)
                            if bsdf_node is None:
                                bsdf_node=next((node for node in nodes if node.type == 'GROUP' and node.name == 'mmd_shader'), None)
                            if bsdf_node is not None:
                                if bsdf_node.type == 'BSDF_PRINCIPLED':
                                    base_color_input = bsdf_node.inputs['Base Color']
                                elif bsdf_node.name == 'mmd_shader':
                                    base_color_input = bsdf_node.inputs['Base Tex']
                                # 查找与基础色相连的图像纹理节点
                                link = next((link for link in links if link.to_socket == base_color_input), None)
                                if link is not None and link.from_node.type == 'TEX_IMAGE':
                                    image_node = link.from_node
                                    if image_node.image:
                                        texconv = Texconv()
                                        astcenc = Astcenc()
                                        # Use image's properties
                                        save_dds(image_node.image, os.path.join(output_path,suffix+"-DiffuseMap.dds"), tex_encode,
                                            invert_normals=False, no_mip=False,
                                            image_filter="LINEAR",
                                            allow_slow_codec=False,
                                            texture_type="2d",
                                            cubemap_layout="h-cross",
                                            extra_texture_list=None,
                                            texconv=texconv, astcenc=astcenc) 
                                        unload_texconv()
                                        unload_astcenc()                                         
                                    else:
                                        self.report({"ERROR"},f"{obj.name}图像纹理图像为空!")
                                else:
                                    self.report({"ERROR"},f"未找{obj.name}到图像纹理!")
                                    break
                            else:
                                self.report({"ERROR"},f"未找到{obj.name}原理化BSDF节点,请检查材质!")
                                break
                        else:
                            self.report({"ERROR"},f"{obj.name}材质未启用!")
                            break
                    else:
                        self.report({"ERROR"},f"请检查{obj.name}材质插槽是否存在!")
                        break
            self.report({"INFO"},"命名贴图导出完毕!")
        else:
            self.report({"ERROR"},f"路径不存在{output_path}!")
        return {"FINISHED"}

@auto_register     
@auto_translate
class WciCopyWeight2MeshOperator(bpy.types.Operator):
    bl_idname = "wci.tool_copy_weight_mesh"
    bl_label = "同网格权重复制"

    @classmethod
    def poll(cls,context):
        if len(context.selected_objects)==2 and context.active_object:
            return True
        else:
            return False


    def execute(self, context):
        #修改非数字骨骼名称及顶点组
        src_obj=None
        des_obj=context.active_object
        for obj in context.selected_objects:
            if obj is not des_obj:
                src_obj=obj
                break
        if len(src_obj.data.vertices)!=len(des_obj.data.vertices):
            self.report({"ERROR"},"顶点不一致！")
        else:
            for vg in src_obj.vertex_groups:
                if vg.name not in des_obj.vertex_groups:
                    des_obj.vertex_groups.new(name=vg.name)
                des_vg = des_obj.vertex_groups[vg.name]
                des_vg.remove(range(len(des_obj.data.vertices)))
                for v in src_obj.data.vertices:
                    for g in v.groups:
                        if g.group==vg.index:
                            des_vg.add([v.index], g.weight, 'REPLACE')
            self.report({"INFO"},"顶点权重复制完毕!")  
        return {'FINISHED'}   

@auto_register     
@auto_translate
class WciAddSkipIbCollectionOperator(bpy.types.Operator):
    bl_label = "将集合加入SKIP IB"
    bl_description = "将当前集合关联ib的SKIP配置写入wci.ini.pre文件中"
    bl_idname = "wci.tool_add__skip_ib_collection"

    def execute(self, context):
        output_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
        game = bpy.context.scene.wci_props.game
        selected_collection = context.collection.name
        ib=selected_collection[0:8]
        if len(ib)==8:
            if os.path.isfile(os.path.join(output_path,".wci")):
                if game in [Game.AE]:
                    #需要读取first_index和index_count
                    with open(os.path.join(output_path,ib,"analysis.json"),"r",encoding="utf-8") as f:
                        buf_dict=json.loads(f.read())
                        hash=buf_dict["ib"]["real_ib"]
                        for key in buf_dict["ib"]["info"]:
                            first_index = buf_dict["ib"]["info"][key]["metadata"]["first_index"]
                            index_count = buf_dict["ib"]["info"][key]["metadata"]["index_count"]
                            sub_alias = buf_dict["ib"]["info"][key]["alias"]
                            break
                    write_txt = f"\n[TextureOverride_{ib}_Component{sub_alias}]\n" + \
                                f"hash = {hash}\n" + \
                                f"match_first_index = {first_index}\n" + \
                                f"match_index_count = {index_count}\n" + \
                                f"handling = skip\n"
                else:
                    write_txt=f"\n[TextureOverride_{ib}_IB]\nhash = {ib}\nhandling = skip\n"
                with open(os.path.join(output_path,"wci.ini.pre"),"a",encoding="utf-8") as f:
                    f.write(write_txt)
                self.report({'INFO'}, f"集合{selected_collection}关联{ib}已添加！")
            else:
                self.report({'ERROR'}, f"{output_path}非导出路径！")
        else:
            self.report({"INFO"},"没有ib信息！")
        return {"FINISHED"}


@auto_register 
@auto_translate
class WciClearCollectionOperator(bpy.types.Operator):
    bl_label = "清理IB及集合"
    bl_description = "谨慎操作！清理当前空ib集合，会同时删除工程路径下对应的ib文件夹，以及不存在于当前场景的ib文件夹"
    bl_idname = "wci.tool_clear_collection"

    def execute(self, context):
        output_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
        collections=bpy.data.collections.keys()
        for name in collections:
            col=bpy.data.collections[name]
            if is_collection_truly_empty(col):
                #集合为空，从其他集合中移除子集合
                for parent_col in bpy.data.collections:
                    if name in parent_col.children:
                        parent_col.children.unlink(col)
                # 从场景根集合移除并删除
                if col.name in bpy.context.scene.collection.children:
                    bpy.context.scene.collection.children.unlink(col)
                if col.name in bpy.data.collections:
                    bpy.data.collections.remove(col)
        #收集ib
        ib_dict=defaultdict(list)
        for collection in bpy.data.collections:
            ib_dict[collection.name.strip()[0:8]].append(collection.name)
        #清理
        ib=""
        for file in os.listdir(output_path):
            if os.path.isfile(os.path.join(output_path,file,"analysis.json")):
                #是ib路径
                ib=file.strip()[0:8]
                if len(ib)>0 and ib not in ib_dict and os.path.isdir(os.path.join(output_path,ib)):
                    shutil.rmtree(os.path.join(output_path,ib))
        return {"FINISHED"}

@auto_register 
@auto_translate
class WciClearLoDsCollectionOperator(bpy.types.Operator):
    bl_label = "清理Lods及集合"
    bl_description = "谨慎操作！清理当前lods文件夹下空ib集合，会同时删除工程路径loDs下对应的ib文件夹，以及不存在于当前场景的ib文件夹"
    bl_idname = "wci.tool_clear_lods_collection"

    def execute(self, context):
        output_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
        game = bpy.context.scene.wci_props.game
        #还要清理wci.json中的lods配对数据，删除不存在当前场景的ib数据，有任何一个不存在都删除
        from ..generate.extend.ex_config import ExConfig
        from ..constants import FOLDER_NAME
        config=ExConfig(game,output_path,os.path.join(output_path,FOLDER_NAME.MOD))
        output_path=os.path.join(output_path,"loDs")
        collections=bpy.data.collections.keys()
        for name in collections:
            col=bpy.data.collections[name]
            if is_collection_truly_empty(col):
                #集合为空，从其他集合中移除子集合
                for parent_col in bpy.data.collections:
                    if name in parent_col.children:
                        parent_col.children.unlink(col)
                # 从场景根集合移除并删除
                if col.name in bpy.context.scene.collection.children:
                    bpy.context.scene.collection.children.unlink(col)
                if col.name in bpy.data.collections:
                    bpy.data.collections.remove(col)
        # 收集ib
        ib_dict=defaultdict(list)
        for collection in bpy.data.collections:
            ib_dict[collection.name.strip()[0:8]].append(collection.name)
        # 清理
        ib=""
        for file in os.listdir(output_path):
            if os.path.isfile(os.path.join(output_path,file,"analysis.json")):
                #是ib路径
                ib=file.strip()[0:8]
                if len(ib)>0 and ib not in ib_dict and os.path.isdir(os.path.join(output_path,ib)):
                    shutil.rmtree(os.path.join(output_path,ib))
        lods_ib_dict={}
        for main_ib in config.wci_lods:
            if "hash" in config.wci_lods[main_ib]:
                lod_ib = config.wci_lods[main_ib]["hash"]
                lods_ib_dict[lod_ib]=main_ib
            lods_ib_dict[main_ib]=main_ib
        for ib in lods_ib_dict:
            if ib not in ib_dict:
                if lods_ib_dict[ib] in config.wci_lods:
                    del config.wci_lods[lods_ib_dict[ib]]
        config.update_wci_json()
        self.report({"INFO"},"清理完毕！")
        return {"FINISHED"}

@auto_register 
@auto_translate  
class WciOpenCollextionFolder(bpy.types.Operator):
    bl_label = "打开集合文件夹"
    bl_idname = "wci.tool_open_collection_folder"

    def execute(self, context):
        output_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
        selected_collection = bpy.context.collection
        if os.path.isdir(os.path.join(output_path,selected_collection.name[0:8])):
            os.startfile(os.path.join(output_path,selected_collection.name[0:8]))
        else:
            if os.path.isdir(os.path.join(output_path,FOLDER_NAME.LODS,selected_collection.name[0:8])):
                os.startfile(os.path.join(output_path,FOLDER_NAME.LODS,selected_collection.name[0:8]))
            else:
                os.startfile(output_path)
        return {"FINISHED"}


@auto_register 
@auto_translate
class WciAttributeSaveToUVOperator(bpy.types.Operator):
    bl_idname = "wci.tool_attributes_save_to_uv"
    bl_label = "将顶点的属性存入UV"
    bl_description = "顶点属性存入UV" 
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        vertex_attribute=context.scene.wci_props.vertex_attribute
        attributes_save_to_uv(vertex_attribute)
        return {'FINISHED'}

@auto_register     
@auto_translate
class WciUVloadToAttributesOperator(bpy.types.Operator):
    bl_idname = "wci.tool_uv_load_to_attribute"
    bl_label = "从UV加载顶点的属性"
    bl_description = "从UV加载顶点的属性" 
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        vertex_attribute=context.scene.wci_props.vertex_attribute
        uv_load_to_attributes(vertex_attribute)
        return {'FINISHED'}

@auto_register    
@auto_translate
class SeparateByMaterialsOperator(bpy.types.Operator):
    bl_idname = 'wci.tool_separate_by_materials'
    bl_label = '按材质分离网格'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def __can_remove(self,key_block):
        if key_block.relative_key == key_block:
            return False # Basis
        for v0, v1 in zip(key_block.relative_key.data, key_block.data):
            if v0.co != v1.co:
                return False
        return True

    def execute(self, context):
        separateByMaterials(context.active_object)
        for ob in context.selected_objects:
            if ob.type != 'MESH' or ob.data.shape_keys is None:
                continue
            if not ob.data.shape_keys.use_relative:
                continue # not be considered yet
            for kb in ob.data.shape_keys.key_blocks:
                if self.__can_remove(kb):
                    ob.shape_key_remove(kb)
            if len(ob.data.shape_keys.key_blocks) == 1:
                ob.shape_key_remove(ob.data.shape_keys.key_blocks[0])
        return {'FINISHED'}

@auto_register 
@auto_translate
class WciBufDumper(bpy.types.Operator):
    bl_label = "数据提取"
    bl_idname = "wci.tool_buf_dumper"

    def execute(self, context):
        game=context.scene.wci_props.game
        if game and game=="":
            self.report({"ERROR"},"请先选择游戏")
            return {"FINISHED"}
        dumps=bpy.path.abspath(context.scene.wci_props.dump_path)
        if not os.path.isdir(dumps):
            self.report({"ERROR"},"请先选择帧转储文件路径")
            return {"FINISHED"}
        output=bpy.path.abspath(context.scene.wci_props.buf_path)
        if not os.path.isdir(output):
            self.report({"ERROR"},"请先选择提取路径")
            return {"FINISHED"}
        min_image_size=(context.scene.wci_props.min_image_size)
        if min_image_size.isdigit() and  int(min_image_size)>0:
            pass
        else:
            self.report({"ERROR"},"贴图尺寸不合规！")
            return {"FINISHED"}
        ib = context.scene.wci_props.dump_ib
        collection:bpy.types.Collection = None
        if ib == "":
            analysis_files,reason=analysis_dumps(output,dumps,game,min_image_size=int(min_image_size))
            if len(analysis_files)>0:
                for analysis_file in analysis_files:
                    if collection is None:
                        collection = bpy.data.collections.new("pack")
                        context.scene.collection.children.link(collection)
                    #清理一下材质，若是有选出来的材质，只要更新一下就好了
                    importer = ModelImporter(analysis_file, os.path.split(analysis_file)[0])
                    importer.import_model(self,collection_name=collection.name)
            else:
                self.report({"ERROR"},"没有找到对应的缓冲区文件！")
        else:
            ib_alias=context.scene.wci_props.dump_ib_alias
            if ib_alias=="":
                ib_alias=ib           
            analysis_files,reason = analysis_dumps(output,dumps,game,ib_infos=[(ib,ib_alias)],min_image_size=int(min_image_size))
            self.report({"INFO"},reason)
            if len(analysis_files)>0 and os.path.isfile(analysis_files[0]):
                importer = ModelImporter(analysis_files[0], os.path.split(analysis_files[0])[0])
                importer.import_model(self)
        return {"FINISHED"}
    
@auto_register  
@auto_translate
class WciBufImporter(bpy.types.Operator):
    bl_label = "从工程路径导入模型"
    bl_idname = "wci.tool_buf_importer"
    bl_options = {'UNDO'}

    def execute(self, context):
        # buf文件路径
        import time
        t=time.time()
        buf_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
        if os.path.isdir(buf_path):
            for dir in os.listdir(buf_path):
                if os.path.isfile(os.path.join(buf_path,dir,"analysis.json")):
                    ib_path=os.path.join(buf_path,dir)
                    importer = ModelImporter(os.path.join(ib_path,"analysis.json"), ib_path)
                    importer.import_model(self)
                    self.report({"INFO"},f"{dir}导入成功！")
            print("time:",time.time()-t)
            return {"FINISHED"}
        else:
            self.report({"ERROR"},f"请选择有效的提取路径！")
            return{"FINISHED"}


@auto_register 
@auto_translate
class WciAnalysisImporter(bpy.types.Operator,ImportHelper):
    bl_idname = "wci.tool_analysis_importer"
    bl_label = "从analysis文件导入模型"
    bl_options = {'UNDO'}

    filename_ext = '.json'

    filter_glob: bpy.props.StringProperty(
        default='*.json;*.ib',
        options={'HIDDEN'},
    ) # type: ignore

    # 2. 定义目录属性（会自动由文件选择器填充）
    directory: bpy.props.StringProperty(
        subtype='DIR_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    ) # type: ignore

    files: bpy.props.CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    ) # type: ignore

    def invoke(self, context, event):
        buf_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
        if os.path.isdir(buf_path):
            self.directory = buf_path
        else:
            # 如果Blend文件已保存，使用其所在目录
            if bpy.data.filepath:
                blend_dir = os.path.dirname(bpy.data.filepath)
                self.directory = blend_dir
            else:
                # 未保存时使用默认路径
                buf_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
                if os.path.isdir(buf_path):
                    self.directory = buf_path
        
        return super().invoke(context, event)

    def execute(self, context):
        self.as_keywords(ignore=('files', 'directory', 'filter_glob'))
        analysis_count=0
        for filename  in self.files:
            if filename.name in ["analysis.json","analysis_export.json"]:
                analysis_count+=1
                ib_path=self.directory
                importer = ModelImporter(os.path.join(self.directory,filename.name), ib_path)
                importer.import_model(self)
        if analysis_count<1:
            self.report({"ERROR"},f"不存在analysis文件！")
        return {'FINISHED'}

@auto_register     
@auto_translate
class WciBufCollectionExporter(bpy.types.Operator):
    bl_label = "从当前集合生成MOD"
    bl_description ="从当前集合或者选中的对象中生成MOD"
    bl_idname = "wci.tool_buf_collection_exporter"

    from_selected: bpy.props.BoolProperty(
        name="从选中对象导出",
        default=False, 
    ) #type: ignore

    @classmethod
    def poll(cls,context):
        if context.view_layer.active_layer_collection:
            return True
        else:
            return False    

    
    def execute(self, context):
        game = context.scene.wci_props.game
        buf_path = bpy.path.abspath(bpy.context.scene.wci_props.buf_path)
        if not os.path.isdir(buf_path):
            self.report({"ERROR"},"请选择工程路径！")
        from ..utils import collect_objects
        from typing import Dict,List
        ib_objs:Dict[str,List[bpy.types.Object]]={}
        import time
        t=time.time()
        if self.from_selected:
            ib_objs=collect_objects(buf_path,context.selected_objects)
        elif context.view_layer.active_layer_collection:
            ib_objs=collect_objects(buf_path,None,collection=context.view_layer.active_layer_collection)
        if len(ib_objs)>0:
            exporter=ModelExporter(self,game,buf_path)
            if exporter.export_model(ib_objs):
                print("export model time:",time.time()-t)
                t=time.time()
                tex_style=bpy.context.scene.wci_props.tex_style
                gen=ModGenerater(self,bpy.context.scene.wci_props.game,buf_path,tex_style=tex_style)
                gen.create_mod(ib_objs)
                print("generate mod time:",time.time()-t)
        else:
            self.report({"ERROR"},"没有可导出对象！")
        self.from_selected=False
        return {"FINISHED"}

@auto_register    
@auto_translate
class WciMergeMeshByVGroupOperator(bpy.types.Operator):
    bl_label = "按顶点组合并网格"
    bl_idname = "wci.tool_buf_merge_mesh_by_vg_operator"

    @classmethod
    def poll(cls,context):
        if len(context.selected_objects)>1:
            return True
        else:
            return False

    def execute(self,context):
        if set_active_collection_to_objects_collection(self):
            main_active_obj_name = context.object.name
            selected_obj_names= [i.name for i in context.selected_objects]
            if len(selected_obj_names)>1:
                #通过名称吧，不然会出错
                #复制最初的active object 按顶点组合并网格一般是用来传递权重的
                temp_active_obj = bpy.data.objects[main_active_obj_name].copy()
                temp_active_obj.data = bpy.data.objects[main_active_obj_name].data.copy()  # 复制数据
                bpy.context.collection.objects.link(temp_active_obj)
                active_obj=temp_active_obj
                for obj_name in selected_obj_names:
                    if obj_name!=main_active_obj_name:
                        obj=bpy.data.objects[obj_name]
                        #返回一个active_obj
                        # #用于进行下一个对象合并
                        print(active_obj.name,obj.name)
                        active_obj=MergeSplitObject.merge_object_by_vertex_groups(active_obj,obj)
                        print(active_obj.name)
                        if not active_obj:
                            self.report({"ERROR"},"顶点组冲突，合并失败！")
                            break
            self.report({"INFO"},"网格合并完毕！")
        return {"FINISHED"}
    

@auto_register 
@auto_translate
class WciSplitMeshByVGroupOperator(bpy.types.Operator):
    bl_label = "按顶点组分离网格"
    bl_idname = "wci.tool_buf_split_mesh_by_vg_operator"


    @classmethod
    def poll(cls,context):
        if len(context.selected_objects)==1 and context.selected_objects[0].mode=='OBJECT':
            return True
        else:
            return False

    def execute(self,context):
        if set_active_collection_to_objects_collection(self):
            objs=MergeSplitObject.separate_object(context.active_object)
            if len(objs)>0:
                self.report({"INFO"},"分离成功")
            else:
                self.report({"INFO"},"分离完毕，未找到需要拆分的数据！")
        return {"FINISHED"}
        
@auto_register 
@auto_translate
class WCI_PACK_SELECTED_OBJECT_OT_operator(bpy.types.Operator):
    """将选中的集合及其子集打包到一个新集合中"""
    bl_idname = "object.pack_selected"
    bl_label = "打包集合"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        # 获取所有选中对象的集合
        selected_collections=[]
        for selected_obj in bpy.context.selected_objects:
            for collection in selected_obj.users_collection:
                if collection not in selected_collections:
                    selected_collections.append(collection)

        if not selected_collections:
            self.report({'WARNING'}, "没有选中的集合")
            return {'CANCELLED'}

        # 创建新集合（自动处理重名）
        new_collection = bpy.data.collections.new("pack")
        scene.collection.children.link(new_collection)


        # 构建从场景根集合开始的父子关系映射
        parent_map = {}
        def build_parent_map(parent_col, children):
            for child in children:
                parent_map[child] = parent_col
                build_parent_map(child, child.children)

        build_parent_map(scene.collection, scene.collection.children)

        # 筛选出顶层选中的集合（即父级不在选中集合中的集合）
        selected_set = set(selected_collections)
        top_level = []
        for col in selected_collections:
            parent = parent_map.get(col)  # 如果不在映射中，说明是孤立集合，但这种情况很少
            if parent not in selected_set:
                top_level.append(col)

        # 移动前检查：确保新集合不是任何待移动集合的后代（虽然新建的不会，但保留检查确保安全）
        def is_descendant(potential_parent, child):
            for c in potential_parent.children:
                if c == child:
                    return True
                if is_descendant(c, child):
                    return True
            return False

        for col in top_level:
            if is_descendant(col, new_collection):
                # 如果发生，说明新集合被意外添加到了col的后代中（理论上不会）
                self.report({'ERROR'}, f"无法移动集合 '{col.name}'，因为新集合是其子集，会导致循环引用")
                bpy.data.collections.remove(new_collection)
                return {'CANCELLED'}

        # 执行移动：将顶层选中的集合从原父级移除，添加到新集合
        moved_count = 0
        for col in top_level:
            original_parent = parent_map.get(col)
            if original_parent:
                original_parent.children.unlink(col)
            new_collection.children.link(col)
            moved_count += 1

        self.report({'INFO'}, f"已将 {moved_count} 个集合打包到 '{new_collection.name}'")
        return {'FINISHED'}

@auto_register 
@auto_translate
class WciMatchLodsImporter(bpy.types.Operator):
    """导入lods模型"""
    bl_idname = "wci.tool_match_lods_importer"
    bl_label = "匹配loDs并导入"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import time
        from ..generate.extend.ex_config import ExConfig
        from ..io.utils import chi2_distance,match_vertex_groups
        from typing import List
        t = time.time()
        game=context.scene.wci_props.game
        dumps=bpy.path.abspath(context.scene.wci_props.dump_path)
        if not os.path.isdir(dumps):
            self.report({"ERROR"},"请先选择帧转储文件路径")
            return {"FINISHED"}
        buf_path=bpy.path.abspath(context.scene.wci_props.buf_path)
        if not os.path.isdir(buf_path):
            self.report({"ERROR"},"请先选择提取路径")
            return {"FINISHED"}
        lods_buf_path = os.path.join(buf_path,"loDs")
        os.makedirs(lods_buf_path,exist_ok=True)
        lods_importers:List[ModelImporter]=[]        
        files= os.listdir(lods_buf_path)
        if len(files)<=0:
            analysis_files,reason=analysis_dumps(lods_buf_path,dumps,game,min_image_size=128)
            if len(analysis_files)>0:
                for analysis_file in analysis_files:
                    importer = ModelImporter(analysis_file, os.path.split(analysis_file)[0])
                    importer.import_model_raw()
                    lods_importers.append(importer)
            else:
                self.report({"ERROR"},"没有找到对应的缓冲区文件！")
                return {"FINISHED"}
            print("extract time:",time.time()-t)
            t=time.time()
        else:
            for dir in files:
                if os.path.isfile(os.path.join(lods_buf_path,dir,"analysis.json")):
                    ib_path=os.path.join(lods_buf_path,dir)
                    importer = ModelImporter(os.path.join(ib_path,"analysis.json"), ib_path)
                    importer.import_model_raw()
                    lods_importers.append(importer)  
        print("load lods time:",time.time()-t)
        t =time.time()
        importers:List[ModelImporter]=[]
        for dir in os.listdir(buf_path):
            if os.path.isfile(os.path.join(buf_path,dir,"analysis.json")):
                ib_path=os.path.join(buf_path,dir)
                importer = ModelImporter(os.path.join(ib_path,"analysis.json"), ib_path)
                importer.import_model_raw()
                importers.append(importer)
        lods_collection:bpy.types.Collection = None
        print("load bufs time:",time.time()-t)
        t =time.time()
        #开始比较
        # 存储所有的卡方距离
        match_ib_dist=defaultdict(list)
        match_ibs={}
        for importer in importers:
            ib_hash = importer.data["ib"]["hash"]
            vertex_count = len(importer.vertices)
            group_indices=list(importer.group_indices)
            group_indices.sort()
            group_count = len(group_indices)
            for lod_importer in lods_importers:
                match_ib_hash = lod_importer.data["ib"]["hash"]
                match_vertex_count = len(lod_importer.vertices)
                match_group_count = len(lod_importer.group_indices)
                if ib_hash!=match_ib_hash and match_vertex_count < vertex_count and group_count>match_group_count-2 and group_count<match_group_count+2:
                    dist = chi2_distance(importer.d2,lod_importer.d2)
                    match_ib_dist[ib_hash].append((match_ib_hash,dist))
        for ib_hash in match_ib_dist:
            sorted_hash = sorted(match_ib_dist[ib_hash],key = lambda x:x[1])
            if sorted_hash[0][1]<0.1:
                match_ibs[sorted_hash[0][0]]=ib_hash
        if len(match_ibs)>0:
            ex_config = ExConfig(game,buf_path,os.path.join(buf_path,"mod"))
            for lod_importer in lods_importers:
                if lod_importer.data["ib"]["hash"] not in match_ibs.keys():
                    if len(lod_importer.group_indices)==0 or lod_importer.data["ib"]["hash"] in match_ib_dist:
                        #移除ib_path
                        if os.path.isdir(lod_importer.ib_path):
                            shutil.rmtree(lod_importer.ib_path)
                else:
                    #写匹配编号，并匹配顶点组
                    ib_hash=match_ibs[lod_importer.data["ib"]["hash"]]
                    for importer in importers:
                        if ib_hash == importer.data["ib"]["hash"]:
                            if len(importer.group_indices)>0 and len(lod_importer.group_indices)>0:#有顶点组才能匹配
                                match_vgs=match_vertex_groups(importer.vertices,lod_importer.vertices)
                            else:
                                match_vgs={}
                            ex_config.wci_lods[importer.data["ib"]["hash"]]={
                                "hash":lod_importer.data["ib"]["hash"],
                                "vg":match_vgs,
                            }
                    if lods_collection is None:
                        lods_collection = bpy.data.collections.new("lods")
                        context.scene.collection.children.link(lods_collection)
                    #后续修改二进制blend.buf文件就行
                    lod_importer.create_blender_objs(collection_name=lods_collection.name)
            ex_config.update_wci_json()
        print("match time:",time.time()-t)
        return{"FINISHED"}

@auto_register 
@auto_translate
class WciCustomMatchLodsImporter(bpy.types.Operator):
    """手动匹配lods模型"""
    bl_idname = "wci.tool_custom_match_lods_importer"
    bl_label = "手动匹配loDs"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import time
        from ..generate.extend.ex_config import ExConfig
        from ..io.utils import match_vertex_groups,chi2_distance
        from typing import List
        t = time.time()
        game=context.scene.wci_props.game
        dumps=bpy.path.abspath(context.scene.wci_props.dump_path)
        if not os.path.isdir(dumps):
            self.report({"ERROR"},"请先选择帧转储文件路径")
            return {"FINISHED"}
        buf_path=bpy.path.abspath(context.scene.wci_props.buf_path)
        if not os.path.isdir(buf_path):
            self.report({"ERROR"},"请先选择提取路径")
            return {"FINISHED"}
        lods_buf_path = os.path.join(buf_path,"loDs")
        if not os.path.isdir(lods_buf_path):
            self.report({"ERROR"},"请先匹配lods并导入！")
            return {"FINISHED"}
        if len(context.selected_objects)!=2:
            self.report({"INFO"},"只能两个不同物体匹配！")
            return {"FINISHED"}
        #收集两个ib
        if not context.active_object:
            self.report({"ERROR"},"没有激活对象!")
            return {"FINISHED"}
        main_ib = context.active_object.name.strip()[0:8]
        for obj in context.selected_objects:
            if obj !=context.active_object:
                lod_ib = obj.name.strip()[0:8]
                break
        if main_ib == lod_ib:
            self.report({"INFO"},"ib一致，已跳过")
            return {"FINISHED"}
        if not os.path.isfile(os.path.join(buf_path,main_ib,"analysis.json")):
            self.report({"ERROR"},f"ib：{main_ib},数据在路径中不存在")
            return {"FINISHED"}
        if not os.path.isfile(os.path.join(lods_buf_path,lod_ib,"analysis.json")):
            self.report({"ERROR"},f"ib：{lod_ib},数据在路径中不存在")
            return {"FINISHED"}  
        
        ex_config = ExConfig(game,buf_path,os.path.join(buf_path,FOLDER_NAME.MOD))  
        main_importer = ModelImporter(os.path.join(buf_path,main_ib,"analysis.json"),
                                      os.path.join(buf_path,main_ib))
        main_importer.import_model_raw()
        lod_importer = ModelImporter(os.path.join(lods_buf_path,lod_ib,"analysis.json"),
                                     os.path.join(lods_buf_path,lod_ib))
        lod_importer.import_model_raw()
        #依然计算一次卡方，只输出
        dist = chi2_distance(main_importer.d2,lod_importer.d2)
        print(main_ib,lod_ib,dist)
        
        if len(main_importer.group_indices)>0 and len(lod_importer.group_indices)>0:
            #有顶点组才能匹配
            match_vgs=match_vertex_groups(main_importer.vertices,lod_importer.vertices)
        else:
            match_vgs={}
        ex_config.wci_lods[main_importer.data["ib"]["hash"]]={
            "hash":lod_importer.data["ib"]["hash"],
            "vg":match_vgs,
        }
        ex_config.update_wci_json()
        return{"FINISHED"}
    

@auto_register 
@auto_translate
class WciUpdateTextOperator(bpy.types.Operator):
    bl_label = "更新异常贴图"
    bl_idname = "wci.tool_update_tex"


    @classmethod
    def poll(cls,context):
        if len(context.selected_objects)>0:
            return True
        else:
            return False

    def execute(self,context):
        buf_path = bpy.path.abspath(context.scene.wci_props.buf_path)
        from ..analysis.analysis_slot import update_custom_tex
        for obj in context.selected_objects:
            ib_hash,sub_alias,name = parse_obj_name(obj.name)
            if ib_hash and sub_alias:
                slot,slot_info = update_custom_tex(buf_path,ib_hash,sub_alias)
                if slot:
                    if not obj.active_material:
                        obj.active_material = bpy.data.materials.new(name=f"Mat_{ib_hash}-{sub_alias}")
                    mat = bpy.data.materials[obj.active_material.name]                    
                    # 遍历材质节点树中的所有节点
                    bsdf_node = None
                    diff_node = None
                    output_node = None
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            bsdf_node = node
                        if node.type == 'OUTPUT_MATERIAL':
                            output_node = node
                        # 检查节点是否为图像纹理节点且包含图像
                        if node.type == 'TEX_IMAGE' and node.image:
                            if "Diffuse" in node.image.name:
                                diff_node = node
                            node.image.reload()  # 直接重载节点引用的图像
                    if not output_node:
                        # 没有输出节点，重新生成
                        output_node = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
                        output_node.location = (0, 0)
                    if not bsdf_node:
                        # 没有bsdf节点，重新生成
                        bsdf_node = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
                        bsdf_node.location = (-300, 0)
                        mat.node_tree.links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
                    if not diff_node:
                        tex_file = None
                        for slot_name in slot_info:
                            if slot_info[slot_name]["name"]=="DiffuseMap":
                                tex_file = slot_info[slot_name]["file"]
                                break
                        if tex_file:
                            tex_path = os.path.join(buf_path,ib_hash,tex_file)
                            # 没有diffuse节点，重新生成
                            diff_node = mat.node_tree.nodes.new(type='ShaderNodeTexImage')
                            diff_node.location = (-600, 0)
                            # 创建纹理节点
                            tex_image = bpy.data.images.load(tex_path, check_existing=True)
                            tex_image.reload()
                            diff_node.image = tex_image
                            # 确保图片不被打包
                            tex_image.source = 'FILE'
                            mat.node_tree.links.new(diff_node.outputs["Color"], bsdf_node.inputs['Base Color'])     
                    self.report({"INFO"},f"更新成功：{slot}")
        return {"FINISHED"}
