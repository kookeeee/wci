import bpy
from .game import game_dict
from bpy.app.translations import register as translations_register, unregister as translations_unregister

from .quick_menu import *
from .locale.translations import translations_dict
from .auto_register import register_classes, unregister_classes, register_properties, unregister_properties


bl_info = {
    "name": "wci_io",
    "description": "wci's Blender addon for export and import 3dmigoto buffer",
    "blender": (4, 2, 0),
    "version": (0, 1, 0, 7),
    "url":"https://github.com/kookeeee/wci",
    "author":"kookeeee",
    "location": "View3D",
    "category": "WCI"
}
import sys
sys.dont_write_bytecode = True

# plugin register 

def register():
    translations_register(bl_info["name"], translations_dict)
    register_classes()
    register_properties()
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)
    print("register games:",game_dict.get_registered_games())
    print(bl_info["name"] + " register!")


def unregister():
    unregister_properties()
    unregister_classes()
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)    
    translations_unregister(bl_info["name"])
    print(bl_info["name"] + " unregister!")