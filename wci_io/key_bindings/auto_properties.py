"""
key_bindings 模块的自动属性注册
"""

import bpy
from bpy.props import BoolProperty, PointerProperty, CollectionProperty, IntProperty
from . import properties
from ..auto_register import auto_property


# 注册 Object 类型的按键绑定属性
@auto_property("Object", PointerProperty, type=properties.KeyBindingList, name="按键绑定", description="按键绑定列表")
def wci_key_bindings():
    """Object 类型的按键绑定属性"""
    pass


# 注册 Scene 类型的显示详情属性
@auto_property("Scene", BoolProperty, name="显示详情", description="显示绑定项的详细信息", default=True)
def wci_key_binding_show_details():
    """Scene 类型的显示详情属性"""
    pass


# 注册 Scene 类型的按键汇总集合属性
@auto_property("Scene", CollectionProperty, type=properties.KeySummaryItem, name="按键汇总", description="全局按键绑定汇总数据")
def key_summary_items():
    """Scene 类型的按键汇总集合属性"""
    pass


# 注册 Scene 类型的汇总索引属性
@auto_property("Scene", IntProperty, name="汇总索引", default=0, min=0)
def key_summary_index():
    """Scene 类型的汇总索引属性"""
    pass