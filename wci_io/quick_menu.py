import bpy

from .ops.operators import *
from .constants import Game
    
  
@auto_translate
@auto_register(order=10,category="menu")
class WciQuickMenu(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_object_wci"
    bl_label = "WCI快捷菜单"
    
    def draw(self, context):
        from bpy.app.translations import pgettext
        layout = self.layout
        layout.operator(WCI_PACK_SELECTED_OBJECT_OT_operator.bl_idname)
        layout.operator(WciClearCollectionOperator.bl_idname)
        if len(context.selected_objects)==1:
            layout.operator(WciUpdateTextOperator.bl_idname)
        if context.scene.wci_props.game in [Game.AE,Game.ZZZ]:
            layout.operator(WciClearLoDsCollectionOperator.bl_idname)
            layout.operator(WciCustomMatchLodsImporter.bl_idname)
        if len(context.selected_objects)>0:
            op=layout.operator(WciBufCollectionExporter.bl_idname,text=pgettext("从选中对象生成MOD"))
            op.from_selected=True

def menu_func(self, context):
    self.layout.menu(WciQuickMenu.bl_idname)
