#所有的常量定义
from typing import List, Tuple

DEFAULT_ITEM_NAME = "default"

class Game:
    ZZZ = "ZZZ"
    HI3 = "HI3"
    GI = "GI"
    AE = "AE"
    HSR = "HSR"
    NARAKA = "NARAKA"
    BOY = "BoY"
    WUWA = "WUWA"
    
class TEX_STYLE:
    SLOT="SLOT"
    HASH="HASH"
    ZZMI="ZZMI"
    RABBITFX="RABBITFX"

    @staticmethod
    def to_enum_items() -> List[Tuple[str, str, str, int]]:
        return [
            (TEX_STYLE.SLOT, 'SLOT', '槽位', 0),
            (TEX_STYLE.HASH, 'HASH', '哈希', 1),
            (TEX_STYLE.ZZMI, 'ZZMI', 'ZZMI', 2),
            (TEX_STYLE.RABBITFX, 'RabbitFX', 'RabbitFX', 3),
        ]
    
class IMAGE_SIZE:
    SIZE_128 = "128"
    SIZE_256 = "256"
    SIZE_512 = "512"
    SIZE_1024 = "1024"
    SIZE_2048 = "2048"
    SIZE_4096 = "4096"
    DEFAULT = SIZE_1024

    @staticmethod
    def to_enum_items() -> List[Tuple[str, str, str, int]]:
        return [
            (IMAGE_SIZE.SIZE_128, '128', '128', 0),
            (IMAGE_SIZE.SIZE_256, '256', '256', 1),
            (IMAGE_SIZE.SIZE_512, '512', '512', 2),
            (IMAGE_SIZE.SIZE_1024, '1024', '1024', 3),
            (IMAGE_SIZE.SIZE_2048, '2048', '2k', 4),
            (IMAGE_SIZE.SIZE_4096, '4096', '4k', 5),
        ]
    

class TEX_ENCODE:
    DEFAULT="BC7_UNORM_SRGB"
    BC7_UNORM_SRGB = "BC7_UNORM_SRGB"
    BC7_UNORM = "BC7_UNORM"

    @staticmethod
    def to_enum_items() -> List[Tuple[str, str, str, int]]:
        return [
            (TEX_ENCODE.BC7_UNORM_SRGB, 'BC7_UNORM_SRGB', '颜色', 0),
            (TEX_ENCODE.BC7_UNORM, 'BC7_UNORM', '线性', 1),
        ]


class VERTEX_ATTRIBUTES:
    NORMAL="NORMAL"
    SMOOTH_NORMAL = "SMOOTH_NORMAL"
    TANGENT="TANGENT"
    SMOOTH_TANGENT = "SMOOTH_TANGENT"

    BLENDWEIGHT="BLENDWEIGHT"
    BLENDINDICE="BLENDINDICE"

    @staticmethod
    def to_enum_items() -> List[Tuple[str, str, str, int]]:
        return [
            (VERTEX_ATTRIBUTES.NORMAL, '法线', '法线', 0),
            (VERTEX_ATTRIBUTES.SMOOTH_NORMAL, '平滑法线', '平滑法线', 1),
            (VERTEX_ATTRIBUTES.TANGENT, '切线', '切线', 2),
            (VERTEX_ATTRIBUTES.SMOOTH_TANGENT, '加权切线', '加权切线', 3),
            (VERTEX_ATTRIBUTES.BLENDWEIGHT, '权重', '权重', 4),
            (VERTEX_ATTRIBUTES.BLENDINDICE, '顶点组', '顶点组', 5),
        ]

class FILE_TYPE:
    BUF="BUF"
    TEX="TEX"

    @staticmethod
    def to_enum_items() -> List[Tuple[str, str, str, int]]:
        return [
            (FILE_TYPE.BUF, 'BUF', '缓冲区', 0),
            (FILE_TYPE.TEX, 'TEX', '贴图', 1),
        ]

class CROSS_TYPE:
    BMSR="bmsr" #Bone Matrix Snapshot Redirect
    BMSR_ALL="bmsr_all" #Bone Matrix Snapshot Redirect All
    CONST="const" #常量跨IB

    @staticmethod
    def to_enum_items() -> List[Tuple[str, str, str, int]]:
        return [
            (CROSS_TYPE.BMSR,'骨骼矩阵','bmsr',  0),
            (CROSS_TYPE.BMSR_ALL, '骨骼矩阵(全量替换)','bmsr_all', 1),
            (CROSS_TYPE.CONST, '常量跨IB','const', 2),
        ]

class EXPORT_TYPE:
    MESH = "MESH"
    FRAME_MESH="FRAME_MESH"
    SHAPEKEY_MESH="SHAPEKEY_MESH"

    @staticmethod
    def to_enum_items():
        return [('MESH','MESH','网格',0),
            ('FRAME_MESH','FRAME_MESH','帧动画网格',1),
            ('SHAPEKEY_MESH','SHAPEKEY_MESH','形态键网格',2),]    

class ReplaceType:
    NONE="none" #什么也不干
    NON_APPEND="non_append"  #无则追加
    NON_INSERT="non_insert"  #无则插入
    REPLACE="replace" #直接替换
    APPEND_REPLACE="append_replace" #以追加模式完成替换，替换字段被追加到匹配字段之后
    INSERT_REPLACE="insert_replace"  #以插入模式完成替换，替换字段被插入到匹配字段之前

    MULTI_NON_APPEND="mulit_non_append" #多个重复值追加
    MULTI_NON_INSERT="mulit_non_insert" #多个重复值插入
    MULTI_REPLACE="multi_replace" #多个重复值替换
    MULTI_APPEND_REPLACE="multi_append_replace" #多个重复值追加替换
    MULTI_INSERT_REPLACE="multi_insert_replace" #多个重复值插入替换   
    LINE_APPEND="line_append" #行追加
    LINE_INSERT="line_insert" #行插入

class SectionType:
    Undefined="Undefined"
    GlobalHead="WCI_Global_Head"
    GlobalFoot="WCI_Global_FOOT"
    Constants="Constants"
    Present="Present"
    Key="Key"
    TextureOverride="TextureOverride"
    ShaderOverride="ShaderOverride"
    CommandList="CommandList"
    CustomShader="CustomShader"
    Resource="Resource"
    ShaderRegex="ShaderRegex"

class SectionSubType:
    SubUndefined="SubUndefined"
    IB="IB"
    Blend="Blend"
    Position="Position"
    Texcoord="Texcoord"
    skip="Skip"
    VertexLimit="VertexLimit"
    Map="Map"
    Buffer="Buffer"
    File="File"
  


class WCI_BASE_CONST:
    WCI_BONE_PREFIX = "WCI_B_"
    WCI_SHAPEKEY_PREFIX = "WCI_S_"


class WCI_PATTERN_NAME:
    
    ADD_PRESENT="add_Present"
    
    ADD_PRESENT_POST="add_Present_post"
    
    ADD_PRESENT_INIT="add_Present_init"
    
    ADD_CONSTANTS_KEY="add_Constants_key"
    
    ADD_CONSTANTS_PERSIST_KEY="add_Constants_persist_key"
    
    ADD_CONSTANTS_INIT="ADD_Constants_init"
    
    ADD_RAW="ADD_RAW"

    ADD_CHECK_TEX = "ADD_CHECK_TEX"

    ADD_IB_SKIP = "ADD_IB_SKIP"
    ADD_TEXTUREOVERRIDE_BUF = "ADD_TEXTUREOVERRIDE_BUF"
    
    ADD_TEXTUREOVERRIDE_BLEND = "ADD_TEXTUREOVERRIDE_BLEND"
    
    ADD_TEXOVERRIDE_HASH = "ADD_TEXOVERRIDE_HASH"
    
    ADD_TEX_RESOURCE = "ADD_TEX_RESOURCE"
    
    ADD_TEXTUREOVERRIDE_IB = "ADD_TEXTUREOVERRIDE_IB"
    
    ADD_TEXTUREOVERRIDE_DRAW ="ADD_TEXTUREOVERRIDE_DRAW"
    
    ADD_DRAWINDEXED = "ADD_DRAWINDEXED"
    
    ADD_DRAWINDEXED_LOD = "ADD_DRAWINDEXED_LOD"


    #extend
    ADD_SHADER_FIX="add_shader_fix"

    ADD_FRAME_INIT="add_frame_init"

    ADD_GLOW_INIT="add_glow_init"
    

    ADD_ACTIVE_FLAG="add_active_flag"

    ADD_CONTROL_ACTIVE_IB="add_control_active_ib"

    ADD_CROSS_CONST = "add_cross_const"
    
    ADD_CROSS_IB = "add_cross_ib"

    ADD_VS_CHECK = "ADD_VS_CHECK"

    ADD_FILTER = "add_fliter"

    ADD_VAR_FILTER = "add_var_filter"

    ADD_BMSR_FILTER = "add_bmsr_filter"
    #shapekey
    ADD_CUSTOMSHADER_SHAPEKEY = "add_customshader_shapekey"

    ADD_COMMANDLIST_SHAPEKEY = "add_commandlist_shapekey"

    ADD_SHAPEKEY_UI = "add_shapekey_ui"

    ADD_XXMI_MOD_LOAD = "ADD_EFMI_MOD_LOAD"


# 文件夹名称常量
class FOLDER_NAME:
    """WCI 插件使用的文件夹名称"""
    SHADER_FIXES = "ShaderFixes" #着色器修复文件夹名称
    BUFFER = "Buffer" #缓冲区文件夹名称
    TEXTURE = "Texture" #贴图文件夹名称
    MOD = "mod" #mod文件夹名称
    LODS = "LoDs" #LoDs文件夹名称
    RES = "res" #资源文件夹名称
    OUTPUT = "wci" #输出文件夹名称
    
    # buf_path 下的文件夹列表
    @staticmethod
    def get_buf_folders() -> list:
        return [FOLDER_NAME.SHADER_FIXES, 
                FOLDER_NAME.BUFFER, 
                FOLDER_NAME.TEXTURE, 
                FOLDER_NAME.MOD, 
                FOLDER_NAME.LODS,
                FOLDER_NAME.RES,]
    
    # mod_path 下的文件夹列表
    @staticmethod
    def get_mod_folders() -> list:
        return [FOLDER_NAME.BUFFER, 
                FOLDER_NAME.TEXTURE,
                FOLDER_NAME.RES,
                ]
