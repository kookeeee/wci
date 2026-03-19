from typing import Dict, Tuple, Any
from ..constants import WCI_BASE_CONST

locale_key = "en_US"

#中译英
def translation_dictionary() -> Dict[Tuple[str, str], str]:
    """
    翻译字典
    格式: {(上下文, 原文): 译文}
    上下文说明:
    - "Operator": 用于 Operator 的 bl_label 和 bl_description
    - "*": 用于其他所有文本（属性 name/description、报告消息等）
    """
    return {
        # ==================== Operator bl_label (使用 "Operator" 上下文) ====================
        # tool_operators.py 中的 Operator bl_label
        ("Operator", "重命名对称骨骼"): "Rename Symmetrical Bones",
        ("Operator", "复制属性到网格"): "Copy Attributes to Mesh",
        ("Operator", "网格贴图命名导出"): "Export Named Mesh Textures",
        ("Operator", "同网格权重复制"): "Copy Weights to Same Mesh",
        ("Operator", "将集合加入SKIP IB"): "Add Collection to SKIP IB",
        ("Operator", "清理IB及集合"): "Clear IB and Collection",
        ("Operator", "清理Lods及集合"): "Clear LODs and Collection",
        ("Operator", "打开集合文件夹"): "Open Collection Folder",
        ("Operator", "将顶点的属性存入UV"): "Save Vertex Attributes to UV",
        ("Operator", "从UV加载顶点的属性"): "Load Vertex Attributes from UV",
        ("Operator", "按材质分离网格"): "Separate Mesh by Material",
        ("Operator", "数据提取"): "Extract Data",
        ("Operator", "从工程路径导入模型"): "Import Models from Project Path",
        ("Operator", "从analysis文件导入模型"): "Import Models from analysis.json",
        ("Operator", "从当前集合生成MOD"): "Generate MOD from Current Collection",
        ("Operator", "按顶点组合并网格"): "Merge Meshes by Vertex Groups",
        ("Operator", "按顶点组分离网格"): "Split Mesh by Vertex Groups",
        ("Operator", "打包集合"): "Pack Collections",
        ("Operator", "匹配loDs并导入"): "Match LODs and Import",
        ("Operator", "手动匹配loDs"): "Custom Match LoDs",
        
        # Panel bl_label
        ("*", "WCI快捷菜单"): "WCI Quick Menu",
        ("*", "WCI导入"): "WCI Import",
        ("*", "WCI导出"): "WCI Export",
        ("*", "网格和贴图"): "Mesh and Texture",
        ("*", "骨骼权重"): "Bone Weights",
        ("*", "形态键"): "Shape Keys",
        ("*", "帧动画"): "Frame Animation",
        ("*", "按键切换"): "Key Bindings",
        ("*", "提取"): "Extract",
        ("*", "提取按键切换"): "Extract Key Bindings",
        
        # key_bindings operators
        ("Operator", "添加按键绑定"): "Add Key Binding",
        ("Operator", "移除绑定"): "Remove Binding",
        ("Operator", "清空所有"): "Clear All",
        ("Operator", "上移"): "Move Up",
        ("Operator", "下移"): "Move Down",
        ("Operator", "刷新"): "Refresh",
        
        # extract operators
        ("Operator", "从mod文件提取相似数据"): "Extract Similar Data from MOD",
        
        # ==================== Operator bl_description (使用 "*" 上下文) ====================
        ("*", "将骨骼及顶点组用 .L,.R格式重命名，让blender可以自动识别"): "Rename bones and vertex groups to .L/.R format for Blender automatic recognition",
        ("*", "将当前集合关联ib的SKIP配置写入wci.ini.pre文件中"): "Write current collection's IB SKIP configuration to wci.ini.pre file",
        ("*", "谨慎操作！清理当前空ib集合，会同时删除工程路径下对应的ib文件夹，以及不存在于当前场景的ib文件夹"): "Caution! Clearing empty IB collections will also delete corresponding IB folders in the project path",
        ("*", "谨慎操作！清理当前lods文件夹下空ib集合，会同时删除工程路径loDs下对应的ib文件夹，以及不存在于当前场景的ib文件夹"): "Caution! Clearing empty IB collections in LODs folder will also delete corresponding folders",
        ("*", "顶点属性存入UV"): "Store vertex attributes in UV",
        ("*", "从UV加载顶点的属性"): "Load vertex attributes from UV",
        ("*", "从当前集合或者选中的对象中生成MOD"): "Generate MOD from current collection or selected objects",
        
        # ==================== 属性 name 和 description (使用 "*" 上下文) ====================
        # properties.py 中的属性
        ("*", "工程路径"): "Project Path",
        ("*", "MOD工程路径，请勿设置在3dmigoto文件夹下"): "MOD project path, do not set in 3dmigoto folder",
        ("*", "3Dmigoto 帧转储文件路径"): "3Dmigoto Frame Dump Path",
        ("*", "3Dmigoto 路径"): "3Dmigoto Path",
        ("*", "3Dmigoto 路径"): "3Dmigoto path",
        ("*", "IB别名"): "IB Alias",
        ("*", "ib的别名，缺省为 ib自己的hash值"): "IB alias, defaults to IB's own hash value",
        ("*", "游戏"): "Game",
        ("*", "需要提取的游戏，决定了提取数据结构"): "Game to extract, determines extraction data structure",
        ("*", "模型UV,不存在则自动创建"): "Model UV, auto-created if not exists",
        ("*", "导出漫射贴图"): "Export Diffuse Map",
        ("*", "贴图导出时导出漫射贴图"): "Export diffuse map when exporting textures",
        ("*", "导出时Y轴向上"): "Y-Axis Up on Export",
        ("*", "导出时自动改变轴向为y轴"): "Automatically change axis to Y-axis on export",
        ("*", "导出wci形态键"): "Export WCI Shape Keys",
        ("*", "导出wci形态键,会自动导出初始顶点模型和合并形态键的模型"): "Export WCI shape keys, will auto-export initial vertex model and merged shape key model",
        ("*", "复制按键"): "Copy Key Bindings",
        ("*", "属性复制时附带复制绑定按键"): "Copy key bindings when copying attributes",
        ("*", "复制名称"): "Copy Name",
        ("*", "属性复制时附带复制附加名称"): "Copy additional names when copying attributes",
        ("*", "过滤尺寸(px)"): "Filter Size (px)",
        ("*", "提取时过滤贴图的最小尺寸"): "Minimum texture size for filtering during extraction",
        ("*", "贴图风格"): "Texture Style",
        ("*", "贴图风格"): "Texture style",
        ("*", "贴图编码"): "Texture Encoding",
        ("*", "贴图编码"): "Texture encoding",
        ("*", "顶点属性"): "Vertex Attribute",
        ("*", "顶点的属性，可以选择写入UV或者从UV读取"): "Vertex attribute, can be written to UV or read from UV",
        ("*", "扩展导出"): "Extended Export",
        ("*", "扩展导出"): "Extended export",
        
        # 集合属性
        ("*", "导出项名称"): "Export Item Name",
        ("*", "索引总数"): "Total Indices",
        ("*", "索引起始位置"): "Index Start Position",
        ("*", "基础顶点索引位置,形态键使用"): "Base vertex index position, used by shape keys",
        ("*", "顶点起始位置"): "Vertex Start Position",
        ("*", "顶点总数"): "Total Vertices",
        ("*", "导出项类型"): "Export Item Type",
        ("*", "导出项列表"): "Export Item List",
        ("*", "当前导出项索引"): "Current Export Item Index",
        
        # ==================== 其他 UI 文本 (使用 "*" 上下文) ====================
        ("*", "3dmigoto路径"): "3DMigoto Path",
        ("*", "别名"): "Alias",
        ("*", "帧转储路径"): "Frame Dump Path",
        ("*", "贴图过滤(px)"): "Texture Filter (px)",
        ("*", "提取"): "Extract",
        ("*", "匹配loDs"): "Match LODs",
        ("*", "贴图风格"): "Texture Style",
        ("*", "导出时轴向转换为Y"): "Convert Axes to Y on Export",
        ("*", "将当前集合加入SKIP IB"): "Add Current Collection to SKIP IB",
        ("*", "从选中对象生成MOD"): "Generate MOD from Selected Objects",
        ("*", "编码"): "Encoding",
        ("*", "复制IB名称前缀"): "Copy IB Name Prefix",
        ("*", "选择UV"): "Select UV",
        ("*", "选择属性"): "Select Attribute",
        ("*", "写入UV"): "Write to UV",
        ("*", "从UV加载"): "Load from UV",
        ("*", "重命名为{}前缀骨骼"): "Rename to {} Prefix Bone",
        ("*", "网格和贴图"): "Mesh and Texture",
        ("*", "骨骼权重"): "Bone Weights",
        
        # reverse/operators.py - WciReverseModOperator
        ("*", "MOD提取"): "MOD Extraction",
        ("Operator", "MOD提取"): "MOD Extraction",

        ("*", "通过逆向分析mod文件，生成对应的可导入缓冲区分析文件"): "Generate importable buffer analysis files by reverse analyzing MOD files",
        
        # tool_panel.py - Panels
        ("*", "WCI导入"): "WCI Import",
        ("*", "WCI导出"): "WCI Export",
        ("*", "网格和贴图"): "Mesh and Texture",
        
        # quick_menu.py - WciQuickMenu
        ("*", "WCI快捷菜单"): "WCI Quick Menu",
        
        # properties.py - WciProperties
        ("*", "工程路径"): "Project Path",
        ("*", "帧转储数据的提取路径"): "Frame dump data extraction path",
        ("*", "3Dmigoto 帧提取文件路径"): "3Dmigoto frame extraction file path",
        ("*", "3Dmigoto 路径"): "3Dmigoto Path",
        ("*", "IB别名"): "IB Alias",
        ("*", "ib的别名，缺省为 ib自己的hash值"): "IB alias, defaults to IB's own hash value",
        ("*", "游戏"): "Game",
        ("*", "需要提取的游戏，决定了提取数据结构"): "Game to extract, determines extraction data structure",
        ("*", "模型UV,不存在则自动创建"): "Model UV, auto-created if not exists",
        ("*", "导出漫射贴图"): "Export Diffuse Map",
        ("*", "贴图导出时导出漫射贴图"): "Export diffuse map when exporting textures",
        ("*", "导出时Y轴向上"): "Y-Axis Up on Export",
        ("*", "导出时自动改变轴向为y轴"): "Automatically change axis to Y-axis on export",
        ("*", "导出wci形态键"): "Export WCI Shape Keys",
        ("*", "导出wci形态键,会自动导出初始顶点模型和合并形态键的模型"): "Export WCI shape keys, will auto-export initial vertex model and merged shape key model",
        ("*", "复制顶点组"): "Copy Vertex Groups",
        ("*", "属性复制时附带复制顶点组"): "Copy vertex groups when copying attributes",
        ("*", "复制名称"): "Copy Name",
        ("*", "属性复制时附带复制附加名称"): "Copy additional names when copying attributes",
        ("*", "过滤尺寸(px)"): "Filter Size (px)",
        ("*", "提取时过滤贴图的最小尺寸"): "Minimum texture size for filtering during extraction",
        ("*", "贴图风格"): "Texture Style",
        ("*", "贴图编码"): "Texture Encoding",
        ("*", "顶点属性"): "Vertex Attribute",
        ("*", "顶点的属性，可以选择写入UV或者从UV读取"): "Vertex attribute, can be written to UV or read from UV",
        ("*", "扩展导出"): "Extended Export",
        ("*", "提取MOD路径"): "Extract MOD Path",
        ("*", "提取MOD数据的路径"): "Extract MOD Path",
        
        # properties.py - WciExportItem
        ("*", "导出项名称"): "Export Item Name",
        ("*", "索引总数"): "Total Indices",
        ("*", "索引起始位置"): "Index Start Position",
        ("*", "基础顶点索引位置,形态键使用"): "Base vertex index position, used by shape keys",
        ("*", "顶点起始位置"): "Vertex Start Position",
        ("*", "顶点总数"): "Total Vertices",
        ("*", "导出项类型"): "Export Item Type",
        
        # properties.py - WciExportList
        ("*", "导出项列表"): "Export Item List",
        ("*", "当前导出项索引"): "Current Export Item Index",
        
        # shapekey/properties.py - WciShapeKeyProperties
        ("*", "导出WCI形态键"): "Export WCI Shape Keys",
        ("*", "标记该对象是否导出WCI形态键"): "Mark whether this object exports WCI shape keys",
        ("*",f"为当前激活的形态键添加{WCI_BASE_CONST.WCI_SHAPEKEY_PREFIX}前缀"): f"Add {WCI_BASE_CONST.WCI_SHAPEKEY_PREFIX} shapekey prefix to the active shapekey",
        ("Operator","重建形态键"): "Rebuild shapekey",
        ("*","从两个顶点拓扑完全一致但是顶点位置不同的网格中重建形态键"): "Rebuild shapekey from two meshes with same topology but different vertex positions",
        
        # shapekey/operators.py - WciRenameWciShapekeyOperator
        ("Operator", "设置WCI形态键"): "set shapekey as wcis shapkey",
        
        # motion/properties.py - WciMotionProperties
        ("*", "开始帧"): "Start Frame",
        ("*", "帧动画开始帧"): "Animation start frame",
        ("*", "结束帧"): "End Frame",
        ("*", "帧动画结束帧"): "Animation end frame",
        ("*", "该对象是否导出帧动画"): "Mark this mesh as frame animation mesh",

        # motion/operators.py - WciSetMotionFrameOperator
        ("*", "场景帧范围"): "scene frame range",
        
        # key_bindings/properties.py - KeyBindingItem
        ("*", "名称"): "Name",
        ("*", "绑定项名称"): "Binding Item Name",
        ("*", "按键绑定"): "Key Binding",
        ("*", "Ctrl"): "Ctrl",
        ("*", "Ctrl 键"): "Ctrl Key",
        ("*", "ShiFt"): "ShiFt",
        ("*", "Shift 键"): "Shift Key",
        ("*", "Alt"): " Alt ",
        ("*", "Alt 键"): "Alt Key",
        ("*", "Or"): "Or",
        ("*", "使用 OR 逻辑连接各个变量（默认 AND）"): "Use OR logic to connect variables (default AND)",
        ("*", "按键"): "3dmigoto key",
        ("*", "键盘按键，符合3migoto keyboard定义"): "Keyboard key, conforms to 3Dmigoto keyboard definition",
        ("*", "切换值"): "Toggle Value",
        ("*", "切换值列表 ,分隔"): "Toggle value list, comma-separated",
        ("*", "切换控制集合"): "Toggle Control Collection",
        ("*", "默认初始值"): "Default Initial Value",
        
        # key_bindings/properties.py - KeyBindingList
        ("*", "按键绑定列表"): "Key Binding List",
        ("*", "按键绑定项列表"): "Key Binding Item List",
        ("*", "活动索引"): "Active Index",
        ("*", "当前选中的绑定项索引"): "Currently selected binding item index",
        
        # key_bindings/properties.py - KeySummaryItem
        ("*", "规格化按键"): "Normalized Key",
        ("*", "符合3dmigoto定义的按键名称"): "Key name conforming to 3Dmigoto definition",
        ("*", "默认值"): "Default Value",
        ("*", "所有对象该按键的默认值（统一设置）"): "Default value for this key across all objects (unified setting)",
        ("*", "条件集合"): "Condition Collection",
        ("*", "关联的场景集合名称"): "Associated scene collection name",
        ("*", "网格对象:"): "object:",
        
        # ==================== 报告消息 (使用 "*" 上下文) ====================
        ("*", "已改名：骨骼{}个,顶点组{}个"): "Renamed: {} bones, {} vertex groups",
        ("*", "已重命名：骨骼{}个,顶点组{}个"): "Renamed: {} bones, {} vertex groups",
        ("*", "已复制"): "Copied",
        ("*", "请先安装blender_dds_addon插件再点击导出!"): "Please install the blender_dds_addon addon before exporting!",
        ("*", "{}图像纹理图像为空!"): "{} image texture is empty!",
        ("*", "未找{}到图像纹理!"): "Could not find image texture for {}!",
        ("*", "未找到{}原理化BSDF节点,请检查材质!"): "Principled BSDF node not found for {}, check material!",
        ("*", "{}材质未启用!"): "Material for {} is not enabled!",
        ("*", "请检查{}材质插槽是否存在!"): "Please check if material slot for {} exists!",
        ("*", "命名贴图导出完毕!"): "Named texture export completed!",
        ("*", "路径不存在{}!"): "Path {} does not exist!",
        ("*", "顶点不一致！"): "Vertex count mismatch!",
        ("*", "顶点权重复制完毕!"): "Vertex weights copied!",
        ("*", "集合{}关联{}已添加！"): "Collection {} associated with {} has been added!",
        ("*", "{}非导出路径！"): "{} is not an export path!",
        ("*", "没有ib信息！"): "No IB information!",
        ("*", "请先选择游戏"): "Please select a game first",
        ("*", "请先选择帧转储文件路径"): "Please select a frame dump path first",
        ("*", "请先选择工程路径"): "Please select an extraction path first",
        ("*", "贴图尺寸不合规！"): "Texture size is invalid!",
        ("*", "没有找到对应的缓冲区文件！"): "No corresponding buffer files found!",
        ("*", "{}导入成功！"): "{} imported successfully!",
        ("*", "请选择有效的工程路径！"): "Please select a valid extraction path!",
        ("*", "不存在analysis文件！"): "analysis.json file does not exist!",
        ("*", "请选择工程路径！"): "Please select a project path!",
        ("*", "没有可导出对象！"): "No objects to export!",
        ("*", "顶点组冲突，合并失败！"): "Vertex group conflict, merge failed!",
        ("*", "网格合并完毕！"): "Mesh merge completed!",
        ("*", "分离成功"): "Separation successful",
        ("*", "分离完毕，未找到需要拆分的数据！"): "Separation completed, no data to split found!",
        ("*", "没有选中的集合"): "No selected collection",
        ("*", "无法移动集合 '{}'，因为新集合是其子集，会导致循环引用"): "Cannot move collection '{}' because the new collection is a subset of it, causing a circular reference",
        ("*", "已将 {} 个集合打包到 '{}'"): "Packed {} collections into '{}'",
    }
