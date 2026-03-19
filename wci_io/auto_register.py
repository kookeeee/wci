from typing import List, Dict, Any, Optional
import bpy
import os
import importlib
import pkgutil
from pathlib import Path

_registered_classes: List[Dict[str, Any]] = []
_registered_properties: List[Dict[str, Any]] = []
_modules_scanned = False


def auto_register(cls=None, *, order: int = 0, category: str = "main") -> Any:
    def decorator(wrapped_cls):
        # 将类信息添加到注册表
        class_info = {
            'cls': wrapped_cls,
            'order': order,
            'category': category,
            'module': wrapped_cls.__module__
        }
        _registered_classes.append(class_info)
        
        return wrapped_cls
    if cls is None:
        return decorator
    else:
        return decorator(cls)


def get_registered_classes(category: Optional[str] = None) -> List[Any]:
    ensure_modules_scanned()
    
    filtered_classes = _registered_classes
    if category:
        filtered_classes = [info for info in _registered_classes if info['category'] == category]
    sorted_classes = sorted(filtered_classes, key=lambda x: x['order'])
    
    return [info['cls'] for info in sorted_classes]


def register_classes(category: Optional[str] = None) -> None:
    classes_to_register = get_registered_classes(category)
    
    for cls in classes_to_register:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"注册失败: {cls.__name__} - {e}")


def unregister_classes(category: Optional[str] = None) -> None:
    classes_to_unregister = get_registered_classes(category)
    for cls in reversed(classes_to_unregister):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"注销失败: {cls.__name__} - {e}")


def _scan_modules_for_classes() -> None:
    global _modules_scanned
    
    if _modules_scanned:
        return
    current_file = Path(__file__)
    package_root = current_file.parent
    modules:List[str]=[]
    for root, dirs, files in os.walk(package_root):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                rel_path = Path(root).relative_to(package_root)
                module_parts = list(rel_path.parts)
                module_name = file[:-3]  # 去掉 .py 后缀
                if module_name != '__init__':
                    module_parts.append(module_name)
                full_module_name = '.'.join(['wci_io'] + module_parts)
                modules.append(full_module_name)
    #先加载最深的模块，确保依赖关系得到满足
    modules.sort(key=lambda x: len(x.split('.')), reverse=True)
    for full_module_name in modules:
        try:
            importlib.import_module(full_module_name)
        except ImportError as e:
            print(f"导入失败: {full_module_name} - {e}")
        except Exception as e:
            print(f"模块导入异常: {full_module_name} - {e}")
    
    _modules_scanned = True


def ensure_modules_scanned() -> None:
    if not _modules_scanned:
        _scan_modules_for_classes()


def auto_property(bl_type: str, property_factory: Any, **kwargs) -> Any:
    def decorator(func):
        # 将属性信息添加到注册表
        property_info = {
            'bl_type': bl_type,
            'property_name': func.__name__,
            'property_factory': property_factory,
            'kwargs': kwargs,
            'module': func.__module__
        }
        _registered_properties.append(property_info)
        
        return func
    
    return decorator


def get_registered_properties() -> List[Dict[str, Any]]:
    return _registered_properties


def register_properties() -> None:
    properties_to_register = get_registered_properties()
    
    for prop_info in properties_to_register:
        try:
            bl_type = getattr(bpy.types, prop_info['bl_type'])
            property_name = prop_info['property_name']
            property_factory = prop_info['property_factory']
            kwargs = prop_info['kwargs']
            setattr(bl_type, property_name, property_factory(**kwargs))
        except Exception as e:
            print(f"属性注册失败: {prop_info['bl_type']}.{property_name} - {e}")


def unregister_properties() -> None:
    properties_to_unregister = get_registered_properties()
    
    for prop_info in reversed(properties_to_unregister):
        try:
            bl_type = getattr(bpy.types, prop_info['bl_type'])
            property_name = prop_info['property_name']
            
            # 删除属性
            if hasattr(bl_type, property_name):
                delattr(bl_type, property_name)
        except Exception as e:
            print(f"属性注销失败: {prop_info['bl_type']}.{property_name} - {e}")