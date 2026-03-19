import os
import shutil
import bpy
import os
from .constants import Game
from .ops.operators import *

from .auto_register import auto_register

@auto_register
@auto_translate
class WciImportToolPanel(bpy.types.Panel):
    bl_label = "WCI导入" 
    bl_idname = "VIEW3D_PT_WCI_IMPORT_TOOL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WCI'

    def draw_header(self, context):
        """绘制面板标题"""
        layout = self.layout
        layout.label(icon='IMPORT')

    def draw(self, context):
        layout = self.layout
        props=context.scene.wci_props

        layout.prop(props,'game')
        layout.prop(props,'migoto_path')
        layout.prop(props, "buf_path")
        box = layout.box()
        # 折叠框的标题行
        row = box.row()
        row.prop(props, "show_dump_options", 
                icon='TRIA_DOWN' if props.show_dump_options else 'TRIA_RIGHT',
                icon_only=True, 
                emboss=False)
        
        # 折叠内容（仅当展开时显示）
        if props.show_dump_options:
            box.prop(props, "dump_ib")
            box.prop(props, "dump_ib_alias")
            box.prop(props, "dump_path")
            box.prop(props,'min_image_size')
            box.operator(WciBufDumper.bl_idname)
            if props.game in [Game.AE,Game.ZZZ]:
                box.operator(WciMatchLodsImporter.bl_idname)
        layout.operator(WciBufImporter.bl_idname)
        layout.operator(WciAnalysisImporter.bl_idname)
        layout.operator(WciOpenCollextionFolder.bl_idname)

@auto_register
@auto_translate
class WciExportToolPanel(bpy.types.Panel):
    bl_label = "WCI导出" 
    bl_idname = "VIEW3D_PT_WCI_EXPORT_TOOL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WCI'

    def draw_header(self, context):
        """绘制面板标题"""
        layout = self.layout
        layout.label(icon='EXPORT')

    def draw(self, context):
        layout = self.layout
        props=context.scene.wci_props

        layout.prop(props, "tex_style")
        layout.prop(props, "export_y_axis")
        layout.operator(WciAddSkipIbCollectionOperator.bl_idname)
        layout.operator(WciBufCollectionExporter.bl_idname) 

@auto_register
@auto_translate
class WciTextureToolPanel(bpy.types.Panel):
    bl_label = "网格和贴图" 
    bl_idname = "VIEW3D_PT_WCI_TEX_TOOL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WCI'
    

    @classmethod
    def poll(cls, context):
        """面板显示条件"""
        return context.active_object and context.active_object.type == 'MESH'
    
    def draw_header(self, context):
        """绘制面板标题"""
        layout = self.layout
        layout.label(text="", icon='MESH_DATA')

    def draw(self, context):
        layout = self.layout
        props=context.scene.wci_props
        row=layout.row()
        layout.prop(props, "export_diffuse")
        layout.prop(props,"tex_encode")
        layout.operator(WciOutputMeshTextureOperator.bl_idname)
        layout.prop(props, "copy_name")
        layout.prop(props, "copy_key_bindings")
        layout.operator(WciCopy3DMAttributes2MeshOperator.bl_idname)
        layout.operator(WciCopyWeight2MeshOperator.bl_idname)
        layout.operator(SeparateByMaterialsOperator.bl_idname)
        layout.operator(WciMergeMeshByVGroupOperator.bl_idname)
        layout.operator(WciSplitMeshByVGroupOperator.bl_idname)

@auto_register
@auto_translate
class WciUVToolPanel(bpy.types.Panel):
    bl_label = "uv" 
    bl_idname = "VIEW3D_PT_WCI_UV_TOOL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WCI'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        """面板显示条件"""
        return context.active_object and context.active_object.type == 'MESH'

    def draw_header(self, context):
        """绘制面板标题"""
        layout = self.layout
        layout.label(text="", icon='MOD_UVPROJECT')
    
    def draw(self, context):
        layout = self.layout
        props=context.scene.wci_props
        
        #TODO 添加一键投影
        layout.separator()
        row=layout.box()
        row.prop(props, "texcoord_uv")
        row.prop(props,'vertex_attribute')
        row.operator(WciAttributeSaveToUVOperator.bl_idname)
        row.operator(WciUVloadToAttributesOperator.bl_idname)

@auto_register
@auto_translate
class WciBoneToolPanel(bpy.types.Panel):
    bl_label = "骨骼权重" 
    bl_idname = "VIEW3D_PT_WCI_BONE_TOOL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WCI'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        """面板显示条件"""
        return context.active_object and context.active_object.type == 'ARMATURE'
    
    def draw_header(self, context):
        """绘制面板标题"""
        layout = self.layout
        layout.label(text="", icon='GROUP_BONE')

    def draw(self, context):
        layout = self.layout
        props=context.scene.wci_props
        box = layout.box()
        box.operator(WciChangeWciBoneNameOperator.bl_idname)
        box.operator(WciRenameBoneOperator.bl_idname)
