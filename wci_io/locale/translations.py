import bpy
from bpy.props import _PropertyDeferred


from . import en_us
from . import zh_cn


def get_translations_dict():
    """获取翻译字典"""
    return {
        en_us.locale_key: en_us.translation_dictionary(),
        zh_cn.locale_key: zh_cn.translation_dictionary(),
    }

translations_dict = get_translations_dict()


def get_translation(text, context="*", locale=None):
    """
    获取翻译文本
    
    Args:
        text: 原文
        context: 上下文，默认为 "*"，Operator 的 bl_label 使用 "Operator"
        locale: 语言代码，默认为当前 Blender 语言
    
    Returns:
        译文，如果找不到则返回原文
    """
    trans_dict = get_translations_dict().get(en_us.locale_key, {})
    
    result = trans_dict.get((context, text))
    if result:
        return result
    
    result = trans_dict.get(("*", text))
    if result:
        return result
    
    return text

def translate_property(prop_deferred, trans_dict):
    """
    翻译 Property 定义中的 name 和 description 参数
    
    Args:
        prop_deferred: _PropertyDeferred 对象（属性定义）
        trans_dict: 翻译字典
    """
    # _PropertyDeferred 存储了创建属性的函数和参数
    if not hasattr(prop_deferred, 'function') or not hasattr(prop_deferred, 'keywords'):
        return
    
    # 获取原始参数
    keywords = prop_deferred.keywords
    
    # 翻译 name 参数
    if 'name' in keywords:
        original_name = keywords['name']
        if original_name:
            # 先尝试 "*" 上下文
            translated = trans_dict.get(("*", original_name))
            if translated:
                keywords['name'] = translated
    
    # 翻译 description 参数
    if 'description' in keywords:
        original_desc = keywords['description']
        if original_desc:
            translated = trans_dict.get(("*", original_desc))
            if translated:
                keywords['description'] = translated

def auto_translate(cls):
    """
    自动翻译装饰器
    用于 Operator、Panel 和 PropertyGroup 类，自动翻译：
    - bl_label 和 bl_description（类属性）
    - bpy.props 类型属性中的 name 和 description 参数
    """
    # 获取翻译字典（使用 en_US 将中文翻译为英文）
    trans_dict = get_translations_dict().get(en_us.locale_key, {})
    
    # 处理 bl_label - 使用 "Operator" 上下文
    if hasattr(cls, 'bl_label'):
        original = cls.bl_label
        # 先尝试 Operator 上下文
        translated = trans_dict.get(("Operator", original))
        if translated:
            cls.bl_label = translated
        else:
            # 再尝试通配符上下文
            translated = trans_dict.get(("*", original))
            if translated:
                cls.bl_label = translated
    
    # 处理 bl_description - 使用 "*" 上下文
    if hasattr(cls, 'bl_description'):
        original = cls.bl_description
        translated = trans_dict.get(("*", original))
        if translated:
            cls.bl_description = translated
    
    # 处理 bpy.props 类型属性
    for attr_name in getattr(cls, '__annotations__', {}):
        annotation = cls.__annotations__[attr_name]
        
        # 检查是否是 _PropertyDeferred 类型（bpy.props 类型）
        if isinstance(annotation, _PropertyDeferred):
            # 翻译这个属性的 name 和 description
            translate_property(annotation, trans_dict)
    
    return cls
