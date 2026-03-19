import bpy
from bpy.types import Panel

from ..auto_register import auto_register

from ..locale.translations import auto_translate

@auto_translate
@auto_register(category="key_bindings")
class VIEW3D_PT_key_bindings(Panel):
    """按键绑定管理面板"""
    
    bl_label = "按键切换"
    bl_idname = "VIEW3D_PT_key_bindings"
    #bl_space_type = 'PROPERTIES'
    #bl_context = "object"
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
        layout.label(text="", icon='KEYINGSET')
    
    def draw(self, context):
        from bpy.app.translations import pgettext
        """绘制面板内容"""
        layout = self.layout
        obj = context.active_object
        
        # 检查属性是否存在
        if not hasattr(obj, 'wci_key_bindings'):
            layout.label(text=pgettext("按键绑定属性未加载"), icon='ERROR')
            layout.operator("wm.operator_defaults")
            return
        
        bindings = obj.wci_key_bindings
        
        # === 第一部分：添加按钮区域 ===
        row=layout.row()
        row.operator(
            "object.add_key_binding",
            icon='ADD'
        )        
        # === 第二部分：绑定列表 ===
        layout.separator()
        
        if len(bindings.items) == 0:
            # 没有绑定时显示提示
            box = layout.box()
            box.label(text=pgettext("暂无按键绑定"), icon='INFO')
            return
        
        # 列表标题和统计
        row = layout.row()
        row.label(text=pgettext("绑定按键")+f" ({len(bindings.items)}):", icon='OUTLINER_DATA_GP_LAYER')
        
        # 展开/折叠按钮
        row.prop(context.scene, "wci_key_binding_show_details", 
                icon='DISCLOSURE_TRI_DOWN' if context.scene.wci_key_binding_show_details else 'DISCLOSURE_TRI_RIGHT',
                emboss=False)
        
        # 绑定列表
        for i, item in enumerate(bindings.items):
            is_active = (i == bindings.active_index)
            
            # 每个绑定项的外框
            box = layout.box()
            box.scale_y = 0.9
            
            # 标题行
            title_row = box.row()
            
            # 绑定名称和基本信息
            title_row.label(text=obj.name)
            
            # 操作按钮
            op_row = title_row.row(align=True)
            op_row.alignment = 'RIGHT'
            
            # 设置活动项按钮
            if not is_active:
                op = op_row.operator(
                    "object.add_key_binding",
                    text="", 
                    icon='RESTRICT_SELECT_OFF'
                )
                op.keyboard = item.keyboard
                op.swap = item.swap
                op.is_ctrl = item.is_ctrl
                op.is_shift = item.is_shift
                op.is_alt = item.is_alt
                op.is_or = item.is_or
                op_row.label(text="")  # 间距
            
            # 移动按钮
            if i > 0:
                op_row.operator(
                    "object.move_key_binding_up", 
                    text="", 
                    icon='TRIA_UP'
                ).index = i
            
            if i < len(bindings.items) - 1:
                op_row.operator(
                    "object.move_key_binding_down", 
                    text="", 
                    icon='TRIA_DOWN'
                ).index = i
            
            # 移除按钮
            op_row.operator(
                "object.remove_key_binding", 
                text="", 
                icon='X'
            ).index = i
            
            # 详细信息（可折叠）
            if context.scene.wci_key_binding_show_details:
                details_box = box.box()
                details_box.scale_y = 0.8
                
                # 修饰键状态
                mod_col = details_box.column(align=True)
                mod_row = mod_col.row(align=True)
                
                # 使用不同颜色显示状态
                mod_row.prop(item, "is_ctrl", 
                           text="Ctrl", 
                           toggle=True,
                           icon='CHECKBOX_HLT' if item.is_ctrl else 'CHECKBOX_DEHLT')
                mod_row.prop(item, "is_shift", 
                           text="Shift", 
                           toggle=True,
                           icon='CHECKBOX_HLT' if item.is_shift else 'CHECKBOX_DEHLT')
                mod_row.prop(item, "is_alt", 
                           text="Alt", 
                           toggle=True,
                           icon='CHECKBOX_HLT' if item.is_alt else 'CHECKBOX_DEHLT')
                mod_row.prop(item, "is_or", 
                           text="Or", 
                           toggle=True,
                           icon='CHECKBOX_HLT' if item.is_or else 'CHECKBOX_DEHLT')
                
                # 按键和交换目标
                key_col = details_box.column(align=True)
                key_col.prop(item, "keyboard")
                key_col.prop(item, "swap")
                
                # 预览信息
                preview_row = details_box.row()
                preview_row.alignment = 'CENTER'
                
                mods = []
                if item.is_ctrl:
                    mods.append("Ctrl")
                if item.is_shift:
                    mods.append("Shift")
                if item.is_alt:
                    mods.append("Alt")
                
                if mods:
                    trigger = f"{' '.join(mods)} {item.keyboard}"
                else:
                    trigger = item.keyboard
                
                logic = "OR" if item.is_or else "AND"
                preview_row.label(text=pgettext("切换")+f": {trigger} = {item.swap}")
            
            # 分隔线
            if i < len(bindings.items) - 1:
                layout.separator()
        
        # === 第三部分：批量操作 ===
        layout.separator()
        
        batch_box = layout.box()
        batch_box.label(text=pgettext("批量操作")+":", icon='MODIFIER')
        
        batch_row = batch_box.row(align=True)
        batch_row.scale_y = 1.2
        
        # 清空所有按钮
        clear_op = batch_row.operator(
            "object.clear_key_bindings", 
            icon='TRASH'
        )    
        # 清空所有按钮
        update_op = batch_row.operator(
            "object.update_key_summary", 
            icon='FILE_REFRESH'
        )  
        # === 第四部分：统计信息 ===
        if len(bindings.items) > 0:
            stats_box = layout.box()
            stats_box.label(text=pgettext("按鍵配置")+":", icon='INFO')
            
            stats_col = stats_box.column(align=True)
        
            # 表头
            col = layout.column(align=True)
            row = col.row()
            row.label(text=pgettext("  按键   "), icon='PINNED')
            row.label(text=pgettext(" 默认值  "), icon='DECORATE')
            row.label(text=pgettext("条件集合 "), icon='OUTLINER_COLLECTION')

            # 遍历汇总行
            for item in context.scene.key_summary_items:
                row = col.row()
                # 按键（只读）
                row.label(text=item.normalized_keyboard)

                # 默认值（整数输入，立即更新所有对象）
                row.prop(item, "defaultvalue", text="")

                # 条件集合选择（使用 prop_search 从 bpy.data.collections 中选择）
                row.prop_search(
                    item,                     # 包含 condition 属性的对象
                    "condition",              # 属性名（字符串）
                    bpy.data,                # 包含集合组的ID库
                    "collections",           # 集合组名称
                    text="",                 # 不显示额外标签
                    icon='OUTLINER_COLLECTION'
                )