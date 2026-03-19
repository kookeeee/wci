import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    StringProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
    EnumProperty
)

from .keyboard_items import KEYBOARD_ITEMS
from ..locale.translations import auto_translate
from ..auto_register import auto_register

@auto_translate
@auto_register(order=-1, category="properties")
class KeyBindingItem(PropertyGroup):
    """单个按键绑定项"""
    
    # 为了在列表中显示名称
    name: StringProperty(
        name="名称",
        description="绑定项名称",
        default="按键绑定"
    ) #type: ignore
    
    is_ctrl: BoolProperty(
        name="Ctrl",
        description="Ctrl 键",
        default=False
    ) #type: ignore
    
    is_shift: BoolProperty(
        name="Shift",
        description="Shift 键",
        default=False
    ) #type: ignore
    
    is_alt: BoolProperty(
        name="Alt",
        description="Alt 键",
        default=False
    ) #type: ignore
    
    is_or: BoolProperty(
        name="Or",
        description="使用 OR 逻辑连接各个变量（默认 AND）",
        default=False
    ) #type: ignore
    
    keyboard: EnumProperty(
        name="按键",
        description="键盘按键，符合3migoto keyboard定义",
        items=KEYBOARD_ITEMS,
        default="A",
    ) #type: ignore
    
    swap: StringProperty(
        name="切换值",
        description="切换值列表 ,分隔",
        default="",
        maxlen=256
    ) #type: ignore

    condition: StringProperty(
        name="切换控制集合",
        description="切换控制集合",
        default="",
        maxlen=256
    ) #type: ignore

    defaultvalue: IntProperty(
        name="默认初始值",
        description="默认初始值",
        default=0,
    ) #type: ignore
    
    def update_name(self):
        """更新显示名称"""
        modifiers = []
        if self.is_ctrl:
            modifiers.append("Ctrl")
        if self.is_shift:
            modifiers.append("Shift")
        if self.is_alt:
            modifiers.append("Alt")
        
        mod_str = "+".join(modifiers) if modifiers else ""
        key_str = self.keyboard if self.keyboard else "未设置"
        
        if mod_str:
            self.name = f"{mod_str}+{key_str}"
        else:
            self.name = key_str
    

@auto_translate
@auto_register(order=-1, category="properties")
class KeyBindingList(PropertyGroup):
    """按键绑定列表管理器"""
    
    items: CollectionProperty(
        type=KeyBindingItem,
        name="按键绑定列表",
        description="按键绑定项列表"
    ) #type: ignore
    
    active_index: IntProperty(
        name="活动索引",
        description="当前选中的绑定项索引",
        default=0,
        min=0
    ) #type: ignore
    
    def add_binding(self, **kwargs):
        """添加新的按键绑定"""
        item = self.items.add()
        item.is_ctrl = kwargs.get('is_ctrl', False)
        item.is_shift = kwargs.get('is_shift', False)
        item.is_alt = kwargs.get('is_alt', False)
        item.is_or = kwargs.get('is_or', False)
        item.keyboard = kwargs.get('keyboard', '')
        item.swap = kwargs.get('swap', '')
        item.update_name()
        return item
    
    def remove_binding(self, index):
        """移除按键绑定"""
        if 0 <= index < len(self.items):
            self.items.remove(index)
            # 更新活动索引
            if self.active_index >= len(self.items):
                self.active_index = max(0, len(self.items) - 1)
            return True
        return False
    
    def move_binding_up(self, index):
        """向上移动绑定项"""
        if index > 0 and index < len(self.items):
            self.items.move(index, index - 1)
            self.active_index = index - 1
            return True
        return False
    
    def move_binding_down(self, index):
        """向下移动绑定项"""
        if index >= 0 and index < len(self.items) - 1:
            self.items.move(index, index + 1)
            self.active_index = index + 1
            return True
        return False
    
    def clear_all(self):
        """清空所有绑定"""
        self.items.clear()
        self.active_index = 0
    

@auto_translate
@auto_register(order=-1, category="properties")
class KeySummaryItem(PropertyGroup):
    """全局面板中每行对应的临时数据"""
    normalized_keyboard: StringProperty(
        name="规格化按键",
        description="符合3dmigoto定义的按键名称",
        default=""
    )  # type: ignore

    defaultvalue: IntProperty(
        name="默认值",
        description="所有对象该按键的默认值（统一设置）",
        default=0,
        update=lambda self, context: update_all_objects_key(self, context, 'defaultvalue')
    )  # type: ignore

    condition: StringProperty(
        name="条件集合",
        description="关联的场景集合名称",
        default="",
        update=lambda self, context: update_all_objects_key(self, context, 'condition')
    )  # type: ignore


def get_n_keyboard(is_alt,is_ctrl,is_shift,keyboard):
    v=""
    if is_alt==False and is_ctrl==False and is_shift==False:
        v+="no_modifiers "
    else:
        if is_alt:
            v+="alt "
        else:
            v+="no_alt "
        if is_ctrl:
            v+="ctrl "
        else:
            v+="no_ctrl "
        if is_shift:
            v+="shift "
        else:
            v+="no_shift "
    return (v+keyboard).upper()

def update_all_objects_key(summary_item, context, prop_name):
    """将汇总行的值应用到所有对象的对应 keyboard 项上"""
    # 避免重复进入更新循环（简单锁）
    if hasattr(update_all_objects_key, "is_updating"):
        return
    update_all_objects_key.is_updating = True

    try:
        target_key = summary_item.normalized_keyboard
        new_value = getattr(summary_item, prop_name)

        for obj in bpy.data.objects:
            if hasattr(obj, "wci_key_bindings") and obj.wci_key_bindings:
                for binding in obj.wci_key_bindings.items:
                    nk=get_n_keyboard(binding.is_alt,binding.is_ctrl,binding.is_shift,binding.keyboard)
                    if nk == target_key:
                        setattr(binding, prop_name, new_value)

        # 可选：强制刷新UI
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    finally:
        del update_all_objects_key.is_updating

def refresh_key_summary(context):
    """扫描所有对象，更新场景的汇总列表"""
    scene = context.scene
    # 收集所有存在的 keyboard
    all_keys = set()
    for obj in bpy.data.objects:
        if hasattr(obj, "wci_key_bindings") and obj.wci_key_bindings:
            for binding in obj.wci_key_bindings.items:
                nk=get_n_keyboard(binding.is_alt,binding.is_ctrl,binding.is_shift,binding.keyboard)
                all_keys.add(nk)

    # 删除已经不存在的 keyboard
    for i in range(len(scene.key_summary_items) - 1, -1, -1):
        if scene.key_summary_items[i].normalized_keyboard not in all_keys:
            scene.key_summary_items.remove(i)

    # 添加新出现的 keyboard（保留原有输入值，若无则取第一个对象的当前值）
    for nk in sorted(all_keys):
        if nk not in [item.normalized_keyboard for item in scene.key_summary_items]:
            new_item = scene.key_summary_items.add()
            new_item.normalized_keyboard = nk

            # 从任意一个对象中获取当前值作为默认显示（可选）
            for obj in bpy.data.objects:
                if hasattr(obj, "wci_key_bindings"):
                    for binding in obj.wci_key_bindings.items:
                        nnk=get_n_keyboard(binding.is_alt,binding.is_ctrl,binding.is_shift,binding.keyboard)
                        if nnk == nk:
                            new_item.defaultvalue = binding.defaultvalue
                            new_item.condition = binding.condition
                            break
                if new_item.defaultvalue != 0 or new_item.condition:
                    break