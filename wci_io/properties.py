import bpy
import os
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    StringProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
    EnumProperty
)
from .locale.translations import auto_translate
from .constants import DEFAULT_ITEM_NAME,EXPORT_TYPE
from .constants import Game,TEX_STYLE,TEX_ENCODE,VERTEX_ATTRIBUTES,IMAGE_SIZE
from .auto_register import auto_register
from .auto_register import auto_property
from .game.game_dict import game_to_enum_items,get_registered_games

#更新UV
def update_texcoord_uv_callback(self, context):
    # 获取当前选择的枚举值
    def set_obj_uv_layer(obj,uv_layer_name):
        if obj.type == 'MESH' and ".vb" in obj.name:
            uv_layer = obj.data.uv_layers.get(uv_layer_name)
            if uv_layer:
                # 如果存在，设置为活动 UV 层
                obj.data.uv_layers.active = uv_layer
            else:
                # 如果不存在，创建新的 UV 层
                new_uv_layer = obj.data.uv_layers.new(name=uv_layer_name)
                obj.data.uv_layers.active = new_uv_layer
    uv_layer_name = context.scene.wci_props.texcoord_uv
    if context.collection:
        for obj in context.collection.all_objects:
            # 判断对象是否为网格
            set_obj_uv_layer(obj,uv_layer_name)
    elif context.object:
        set_obj_uv_layer(context.object,uv_layer_name)
    else:
        self.report({"ERROR"},"未选择任何对象！")
    return None
       

# 更新路径
def update_dump_path(self, context):
    """当 3dmigoto 路径改变时，自动设置 3Dmigoto 帧转储路径"""
    props=context.scene.wci_props
    if props.migoto_path:
        # 或者基于 buf_path 生成新的路径
        analysis=[]
        for file in os.listdir(bpy.path.abspath(props.migoto_path)):
            if "FrameAnalysis" in file:
                analysis.append(file)
        analysis.sort()
        if len(analysis)>0:
            props.dump_path = bpy.path.abspath(os.path.join(props.migoto_path,analysis[-1]))
        #清除工程目录下的.wci
        wci_proj=os.path.join(bpy.path.abspath(props.buf_path),".wci")
        if os.path.isfile(wci_proj):
            os.remove(wci_proj)



@auto_translate
@auto_register(order=-100, category="properties")
class WciProperties(bpy.types.PropertyGroup):
    buf_path: bpy.props.StringProperty(
        name="工程路径",
        description="MOD工程路径，请勿设置在3dmigoto文件夹下",
        default="",
        subtype="DIR_PATH",
    ) # type: ignore

    dump_path: bpy.props.StringProperty(
        name="3Dmigoto 帧提取文件路径",
        description="3Dmigoto 帧提取文件路径",
        default="",
        subtype="DIR_PATH",
    ) # type: ignore

    migoto_path: bpy.props.StringProperty(
        name="3Dmigoto 路径",
        description="3Dmigoto 路径",
        default="",
        subtype="DIR_PATH",
        update=update_dump_path,
    ) # type: ignore
    dump_ib: bpy.props.StringProperty(
        name="IB",
        description="IB",
        default="",
    ) # type: ignore
    dump_ib_alias: bpy.props.StringProperty(
        name="IB别名",
        description="ib的别名，缺省为 ib自己的hash值",
        default="",
    ) # type: ignore
    game: bpy.props.EnumProperty(
        name ="游戏",
        description="需要提取的游戏，决定了提取数据结构",
        items=game_to_enum_items(),
        default=get_registered_games()[0],
    ) # type: ignore 

    show_dump_options:bpy.props.BoolProperty(
        default=False,
    )# type: ignore

    texcoord_uv: bpy.props.EnumProperty(
        name ="UV",
        description="模型UV,不存在则自动创建",
        items=[('TEXCOORD.xy','TEXCOORD.xy','',0),
            ('TEXCOORD1.xy','TEXCOORD1.xy','',1),
            ('TEXCOORD2.xy','TEXCOORD2.xy','',2),
            ('TEXCOORD3.xy','TEXCOORD3.xy','',3),
            ('TEXCOORD4.xy','TEXCOORD4.xy','',4),],
        default='TEXCOORD.xy',
        update=update_texcoord_uv_callback,
    ) # type: ignore

    export_diffuse: bpy.props.BoolProperty(
        name="导出漫射贴图",
        description="贴图导出时导出漫射贴图",
        default=True,
    ) # type: ignore 
   
    export_y_axis: bpy.props.BoolProperty(
        name="导出时Y轴向上",
        description="导出时自动改变轴向为y轴",
        default=False
    ) # type: ignore
    export_wci_shapekey: bpy.props.BoolProperty(
        name="导出wci形态键",
        description="导出wci形态键,会自动导出初始顶点模型和合并形态键的模型",
        default=False
    ) # type: ignore

    copy_key_bindings: bpy.props.BoolProperty(
        name="复制按键",
        description="属性复制时附带复制绑定按键",
        default=False,
    ) # type: ignore 
    copy_name: bpy.props.BoolProperty(
        name="复制名称",
        description="属性复制时附带复制附加名称",
        default=True,
    ) # type: ignore 
    min_image_size: bpy.props.EnumProperty(
        name ="过滤尺寸(px)",
        description="提取时过滤贴图的最小尺寸",
        items=IMAGE_SIZE.to_enum_items(),
        default=IMAGE_SIZE.DEFAULT,
    ) # type: ignore
    tex_style: bpy.props.EnumProperty(
        name ="贴图风格",
        description="贴图风格",
        items=TEX_STYLE.to_enum_items(),
        default=TEX_STYLE.SLOT,
    ) # type: ignore

    tex_encode: bpy.props.EnumProperty(
        name ="贴图编码",
        description="贴图编码",
        items=TEX_ENCODE.to_enum_items(),
        default=TEX_ENCODE.DEFAULT,
    ) # type: ignore
    vertex_attribute:bpy.props.EnumProperty(
        name ="顶点属性",
        description="顶点的属性，可以选择写入UV或者从UV读取",
        items=VERTEX_ATTRIBUTES.to_enum_items(),
        default=VERTEX_ATTRIBUTES.SMOOTH_NORMAL,
    ) # type: ignore
    
    extension: bpy.props.BoolProperty(
        name="扩展导出",
        description="扩展导出",
        default=True
    ) # type: ignore    
    custom_mod_path: bpy.props.StringProperty(
        name="提取MOD路径",
        description="提取MOD数据的路径",
        default="",
        subtype="DIR_PATH",
    ) # type: ignore
    extract_keys: bpy.props.BoolProperty(
        name="提取按键切换",
        description="提取按键切换",
        default=False,
    ) # type: ignore


@auto_translate
@auto_register(order=-90, category="properties")
class WciExportItem(PropertyGroup):
    """单个导出项"""
    
    # 为了在列表中显示名称
    name: StringProperty(
        name="name",
        description="导出项名称",
        default=DEFAULT_ITEM_NAME
    ) #type: ignore
    
    index_count: IntProperty(
        name="index_count",
        description="索引总数",
        default=0
    ) #type: ignore
    
    start_index: IntProperty(
        name="start_index",
        description="索引起始位置",
        default=0
    ) #type: ignore
    base_start_vertex: IntProperty(
        name="base_start_vertex",
        description="基础顶点索引位置,形态键使用",
        default=0,
    ) #type: ignore
    start_vertex:  IntProperty(
        name="start_vertex",
        description="顶点起始位置",
        default=0
    ) #type: ignore
    
    vertex_count: IntProperty(
        name="vertex_count",
        description="顶点总数",
        default=0
    ) #type: ignore
    
    export_type: EnumProperty(
        name="export_type",
        description="导出项类型",
        items=EXPORT_TYPE.to_enum_items(),
        default=EXPORT_TYPE.MESH
    ) #type: ignore

    
@auto_translate
@auto_register(order=-80, category="properties")
class WciExportList(PropertyGroup):
    """按键绑定列表管理器"""
    
    items: CollectionProperty(
        type=WciExportItem,
        name="item",
        description="导出项列表"
    ) #type: ignore
    
    index: IntProperty(
        name="index",
        description="当前导出项索引",
        default=0,
        min=0
    ) #type: ignore
    
    def add_item(self, **kwargs):
        """添加"""
        item = self.items.add()
        item.name = kwargs.get('name', DEFAULT_ITEM_NAME)
        item.index_count = kwargs.get('index_count', 0)
        item.start_index = kwargs.get('start_index', 0)
        item.start_vertex = kwargs.get('start_vertex', 0)
        item.base_start_vertex = kwargs.get('base_start_vertex', 0)
        item.vertex_count = kwargs.get('vertex_count', 0)
        item.export_type = kwargs.get('export_type', EXPORT_TYPE.MESH)
        return item
    
    def remove_item(self, index):
        """移除"""
        if 0 <= index < len(self.items):
            self.items.remove(index)
            return True
        return False
    
    def to_list(self):
        l=[]
        for item in self.items:
            l.append({
                "name":item.name,
                "start_index":item.start_index,
                "index_count":item.index_count,
                "vertex_count":item.vertex_count,
                "base_start_vertex":item.base_start_vertex,
                "export_type":item.export_type,
            })
        return l
    
    def clear_all(self):
        """清空"""
        self.items.clear()
        self.active_index = 0

# 使用装饰器标记需要自动注册的属性
@auto_property("Object", PointerProperty, type=WciExportList)
def wci_exports():
    """Object 类型的 wci_exports 属性"""
    pass


@auto_property("Scene", PointerProperty, type=WciProperties)  
def wci_props():
    """Scene 类型的 wci_props 属性"""
    pass