import bpy
import json
import os
from bpy.types import Operator
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    EnumProperty
)
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .keyboard_items import KEYBOARD_ITEMS


from .properties import refresh_key_summary
from ..auto_register import auto_register
from ..locale.translations import auto_translate

@auto_translate
@auto_register(category="key_bindings")
class OBJECT_OT_add_key_binding(Operator):
    """添加新的按键绑定"""
    
    bl_idname = "object.add_key_binding"
    bl_label = "添加按键绑定"
    bl_description = "添加新的按键绑定配置"
    bl_options = {'REGISTER', 'UNDO'}
    
    # 按键属性
    keyboard: EnumProperty(
        name="按键",
        description="标准3dmigoto按键",
        items=KEYBOARD_ITEMS,
        default="A",
    ) #type: ignore
    
    swap: StringProperty(
        name="切换值",
        description="切换值列表",
        default="",
        maxlen=256
    ) #type: ignore
    
    is_ctrl: BoolProperty(
        name="Ctrl",
        description="需要 Ctrl 键",
        default=False
    ) #type: ignore
    
    is_shift: BoolProperty(
        name="Shift",
        description="需要 Shift 键",
        default=False
    ) #type: ignore
    
    is_alt: BoolProperty(
        name="Alt",
        description="需要 Alt 键",
        default=False
    ) #type: ignore
    
    is_or: BoolProperty(
        name="Or 逻辑",
        description="使用 OR 逻辑组合（默认 AND）",
        default=False
    ) #type: ignore

    default: StringProperty(
        name="按键默认值",
        description="按键默认值",
        default="0",
        maxlen=256
    ) #type: ignore
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "请先选择一个网格对象")
            return {'CANCELLED'}
        
        if not hasattr(obj, 'wci_key_bindings'):
            self.report({'ERROR'}, "按键绑定属性未初始化")
            return {'CANCELLED'}
        
        # 添加新绑定
        bindings = obj.wci_key_bindings
        bindings.add_binding(
            keyboard=self.keyboard,
            swap=self.swap,
            is_ctrl=self.is_ctrl,
            is_shift=self.is_shift,
            is_alt=self.is_alt,
            is_or=self.is_or,
            default=0,
        )
        
        # 设置新添加的项为活动项
        bindings.active_index = len(bindings.items) - 1
        
        # 显示成功消息
        mods = []
        if self.is_ctrl:
            mods.append("Ctrl")
        if self.is_shift:
            mods.append("Shift")
        if self.is_alt:
            mods.append("Alt")
        
        mod_str = " ".join(mods) if mods else ""
        self.report({'INFO'}, f"添加了绑定: {mod_str} {self.keyboard} = {self.swap}")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        """弹出对话框"""
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        """绘制对话框"""
        layout = self.layout
        
        # 修饰键设置
        box = layout.box()
        row = box.row(align=True)
        row.prop(self, "is_ctrl", toggle=True)
        row.prop(self, "is_shift", toggle=True)
        row.prop(self, "is_alt", toggle=True)
        row.prop(self, "is_or", toggle=True)
        
        # 按键设置
        box = layout.box()
        box.label(text="按键设置:", icon='KEY_HLT')
        box.prop(self, "keyboard")
        box.prop(self, "swap")
        
        # 预览
        box = layout.box()
        box.label(text="绑定预览:", icon='VIEWZOOM')
        
        mods = []
        if self.is_ctrl:
            mods.append("Ctrl")
        if self.is_shift:
            mods.append("Shift")
        if self.is_alt:
            mods.append("Alt")
        
        if mods:
            preview = f"{'+'.join(mods)}+{self.keyboard}"
        else:
            preview = self.keyboard
        
        box.label(text=f"按键: {preview}={self.swap}")

@auto_translate
@auto_register(category="key_bindings")
class OBJECT_OT_remove_key_binding(Operator):
    """移除按键绑定"""
    
    bl_idname = "object.remove_key_binding"
    bl_label = "移除绑定"
    bl_description = "移除选中的按键绑定"
    bl_options = {'REGISTER', 'UNDO'}
    
    index: IntProperty(
        name="索引",
        description="要移除的绑定索引（-1表示当前选中）",
        default=-1,
        min=-1
    ) #type: ignore
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "请先选择一个网格对象")
            return {'CANCELLED'}
        
        if not hasattr(obj, 'wci_key_bindings'):
            self.report({'ERROR'}, "按键绑定属性未初始化")
            return {'CANCELLED'}
        
        bindings = obj.wci_key_bindings
        
        # 确定要移除的索引
        if self.index == -1:
            index = bindings.active_index
        else:
            index = self.index
        
        # 检查索引有效性
        if index < 0 or index >= len(bindings.items):
            self.report({'ERROR'}, "无效的绑定索引")
            return {'CANCELLED'}
        
        # 获取要移除的绑定信息（用于报告）
        binding = bindings.items[index]
        mods = []
        if binding.is_ctrl:
            mods.append("Ctrl")
        if binding.is_shift:
            mods.append("Shift")
        if binding.is_alt:
            mods.append("Alt")
        
        mod_str = " ".join(mods) if mods else ""
        if mod_str:
            binding_name = f"{mod_str} {binding.keyboard}"
        else:
            binding_name = binding.keyboard
        
        # 移除绑定
        if bindings.remove_binding(index):
            self.report({'INFO'}, f"已移除绑定: {binding_name}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "移除绑定失败")
            return {'CANCELLED'}

@auto_translate
@auto_register(category="key_bindings")
class OBJECT_OT_clear_key_bindings(Operator):
    """清空所有按键绑定"""
    
    bl_idname = "object.clear_key_bindings"
    bl_label = "清空所有"
    bl_description = "清空所有按键绑定配置"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "请先选择一个网格对象")
            return {'CANCELLED'}
        
        if not hasattr(obj, 'wci_key_bindings'):
            self.report({'ERROR'}, "按键绑定属性未初始化")
            return {'CANCELLED'}
        
        bindings = obj.wci_key_bindings
        
        if len(bindings.items) == 0:
            self.report({'WARNING'}, "没有可清空的绑定")
            return {'CANCELLED'}
        
        # 确认对话框
        count = len(bindings.items)
        bindings.clear_all()
        
        self.report({'INFO'}, f"已清空 {count} 个绑定配置")
        return {'FINISHED'}

@auto_translate
@auto_register(category="key_bindings")
class OBJECT_OT_move_key_binding_up(Operator):
    """向上移动绑定项"""
    
    bl_idname = "object.move_key_binding_up"
    bl_label = "上移"
    bl_description = "向上移动绑定项"
    bl_options = {'REGISTER', 'UNDO'}
    
    index: IntProperty(
        name="索引",
        description="要移动的绑定索引",
        default=-1,
        min=-1
    ) #type: ignore
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "请先选择一个网格对象")
            return {'CANCELLED'}
        
        if not hasattr(obj, 'wci_key_bindings'):
            self.report({'ERROR'}, "按键绑定属性未初始化")
            return {'CANCELLED'}
        
        bindings = obj.wci_key_bindings
        
        # 确定索引
        if self.index == -1:
            index = bindings.active_index
        else:
            index = self.index
        
        # 移动
        if bindings.move_binding_up(index):
            self.report({'INFO'}, "绑定项已上移")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "无法上移绑定项")
            return {'CANCELLED'}

@auto_translate
@auto_register(category="key_bindings")
class OBJECT_OT_move_key_binding_down(Operator):
    """向下移动绑定项"""
    
    bl_idname = "object.move_key_binding_down"
    bl_label = "下移"
    bl_description = "向下移动绑定项"
    bl_options = {'REGISTER', 'UNDO'}
    
    index: IntProperty(
        name="索引",
        description="要移动的绑定索引",
        default=-1,
        min=-1
    ) #type: ignore
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "请先选择一个网格对象")
            return {'CANCELLED'}
        
        if not hasattr(obj, 'wci_key_bindings'):
            self.report({'ERROR'}, "按键绑定属性未初始化")
            return {'CANCELLED'}
        
        bindings = obj.wci_key_bindings
        
        # 确定索引
        if self.index == -1:
            index = bindings.active_index
        else:
            index = self.index
        
        # 移动
        if bindings.move_binding_down(index):
            self.report({'INFO'}, "绑定项已下移")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "无法下移绑定项")
            return {'CANCELLED'}

@auto_translate
@auto_register(category="key_bindings")
class OBJECT_OT_update_key_summary(Operator):
    """清空所有按键绑定"""
    
    bl_idname = "object.update_key_summary"
    bl_label = "刷新"
    bl_description = "刷新所有按键绑定配置"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        refresh_key_summary(context)
        return {'FINISHED'}