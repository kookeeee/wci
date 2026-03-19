from typing import Dict,List,Any,Tuple
from copy import deepcopy
from ..constants import Game,WCI_PATTERN_NAME,ReplaceType,FOLDER_NAME
from .game_dict import register_buffer, register_pattern
from ..game import default
game = Game.HSR
name = "崩坏：星穹铁道"

@register_buffer(game, name)
def get_buffers():
    buffer_dict={
        "ib": {
            "suf": ".ib",
            "z-normal": False,
            "slots": [
                {
                    "ps-t1": {"name": "LightMap"},
                    "ps-t2": {"name": "DiffuseMap"},
                },
                {
                    "ps-t2": {"name": "DiffuseMap"},
                    "ps-t3": {"name": "LightMap"},
                },
            ],
        },
        "cs-t0": {
            "suf": "-Position.buf",
            "draw": "vb0",
            "fmts": [
                {
                    "metadata": {
                        "stride": 40,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 0,
                                "SemanticName": "POSITION",
                                "SemanticIndex": 0,
                                "Format": "R32G32B32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "POSITION",
                            },
                            {
                                "index": 1,
                                "SemanticName": "NORMAL",
                                "SemanticIndex": 1,
                                "Format": "R32G32B32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 12,
                                "AliasSemanticName": "NORMAL",
                            },
                            {
                                "index": 2,
                                "SemanticName": "TANGENT",
                                "SemanticIndex": 2,
                                "Format": "R32G32B32A32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 24,
                                "AliasSemanticName": "TANGENT",
                            },
                        ],
                        "semantics": ["POSITION", "NORMAL","TANGENT"],
                    },
                    "suf": "-Position.buf",
                }
            ],
        },
        "cs-t2": {
            "suf": "-Position.buf",
            "draw": "vb0",
            "fmts": [
                {
                    "metadata": {
                        "stride": 40,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 0,
                                "SemanticName": "POSITION",
                                "SemanticIndex": 0,
                                "Format": "R32G32B32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "POSITION",
                            },
                            {
                                "index": 1,
                                "SemanticName": "NORMAL",
                                "SemanticIndex": 1,
                                "Format": "R32G32B32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 12,
                                "AliasSemanticName": "NORMAL",
                            },
                            {
                                "index": 2,
                                "SemanticName": "TANGENT",
                                "SemanticIndex": 2,
                                "Format": "R32G32B32A32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 24,
                                "AliasSemanticName": "TANGENT",
                            },
                        ],
                        "semantics": ["POSITION", "NORMAL","TANGENT"],
                    },
                    "suf": "-Position.buf",
                }
            ],
        },
        "cs-t3": {
            "suf": "-Position.buf",
            "draw": "vb0",
            "fmts": [
                {
                    "metadata": {
                        "stride": 40,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 0,
                                "SemanticName": "POSITION",
                                "SemanticIndex": 0,
                                "Format": "R32G32B32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "POSITION",
                            },
                            {
                                "index": 1,
                                "SemanticName": "NORMAL",
                                "SemanticIndex": 1,
                                "Format": "R32G32B32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 12,
                                "AliasSemanticName": "NORMAL",
                            },
                            {
                                "index": 2,
                                "SemanticName": "TANGENT",
                                "SemanticIndex": 2,
                                "Format": "R32G32B32A32_FLOAT",
                                "InputSlot": "0",
                                "AlignedByteOffset": 24,
                                "AliasSemanticName": "TANGENT",
                            },
                        ],
                        "semantics": ["POSITION", "NORMAL","TANGENT"],
                    },
                    "suf": "-Position.buf",
                }
            ],
        },
        "cs-t1": {
            "suf": "-Blend.buf",
            "fmts": [
                {
                    "metadata": {
                        "stride": 32,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 6,
                                "SemanticName": "BLENDWEIGHTS",
                                "SemanticIndex": 0,
                                "Format": "R32G32B32A32_FLOAT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "BLENDWEIGHTS",
                            },
                            {
                                "index": 7,
                                "SemanticName": "BLENDINDICES",
                                "SemanticIndex": 0,
                                "Format": "R32G32B32A32_SINT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 16,
                                "AliasSemanticName": "BLENDINDICES",
                            },
                        ],
                        "semantics": ["BLENDWEIGHTS", "BLENDINDICES"],
                    },
                    "suf": "-Blend.buf",
                },
                {
                    "metadata": {
                        "stride": 16,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 6,
                                "SemanticName": "BLENDWEIGHTS",
                                "SemanticIndex": 0,
                                "Format": "R32G32_FLOAT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "BLENDWEIGHTS1",
                            },
                            {
                                "index": 7,
                                "SemanticName": "BLENDINDICES",
                                "SemanticIndex": 0,
                                "Format": "R32G32_UINT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 8,
                                "AliasSemanticName": "BLENDINDICES1",
                            },
                        ],
                        "semantics": ["BLENDWEIGHTS", "BLENDINDICES"],
                    },
                    "suf": "-Blend.buf",
                }
            ],
        },
        "cs-t7": {
            "suf": "-Blend.buf",
            "fmts": [
                {
                    "metadata": {
                        "stride": 32,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 6,
                                "SemanticName": "BLENDWEIGHTS",
                                "SemanticIndex": 6,
                                "Format": "R32G32B32A32_FLOAT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "BLENDWEIGHTS",
                            },
                            {
                                "index": 7,
                                "SemanticName": "BLENDINDICES",
                                "SemanticIndex": 7,
                                "Format": "R32G32B32A32_SINT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 16,
                                "AliasSemanticName": "BLENDINDICES",
                            },
                        ],
                        "semantics": ["BLENDWEIGHTS", "BLENDINDICES"],
                    },
                    "suf": "-Blend.buf",
                },
                {
                    "metadata": {
                        "stride": 16,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 6,
                                "SemanticName": "BLENDWEIGHTS",
                                "SemanticIndex": 6,
                                "Format": "R32G32_FLOAT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "BLENDWEIGHTS1",
                            },
                            {
                                "index": 7,
                                "SemanticName": "BLENDINDICES",
                                "SemanticIndex": 7,
                                "Format": "R32G32_UINT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 8,
                                "AliasSemanticName": "BLENDINDICES1",
                            },
                        ],
                        "semantics": ["BLENDWEIGHTS", "BLENDINDICES"],
                    },
                    "suf": "-Blend.buf",
                }
            ],
        },
        "cs-t8": {
            "suf": "-Blend.buf",
            "fmts": [
                {
                    "metadata": {
                        "stride": 32,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 6,
                                "SemanticName": "BLENDWEIGHTS",
                                "SemanticIndex": 6,
                                "Format": "R32G32B32A32_FLOAT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "BLENDWEIGHTS",
                            },
                            {
                                "index": 7,
                                "SemanticName": "BLENDINDICES",
                                "SemanticIndex": 7,
                                "Format": "R32G32B32A32_SINT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 16,
                                "AliasSemanticName": "BLENDINDICES",
                            },
                        ],
                        "semantics": ["BLENDWEIGHTS", "BLENDINDICES"],
                    },
                    "suf": "-Blend.buf",
                },
                {
                    "metadata": {
                        "stride": 16,
                        "topology": "pointlist",
                        "elements": [
                            {
                                "index": 6,
                                "SemanticName": "BLENDWEIGHTS",
                                "SemanticIndex": 6,
                                "Format": "R32G32_FLOAT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 0,
                                "AliasSemanticName": "BLENDWEIGHTS1",
                            },
                            {
                                "index": 7,
                                "SemanticName": "BLENDINDICES",
                                "SemanticIndex": 7,
                                "Format": "R32G32_UINT",
                                "InputSlot": "2",
                                "AlignedByteOffset": 8,
                                "AliasSemanticName": "BLENDINDICES1",
                            },
                        ],
                        "semantics": ["BLENDWEIGHTS", "BLENDINDICES"],
                    },
                    "suf": "-Blend.buf",
                }
            ],
        },                        
        "vb1": {"suf": "-Texcoord.buf", "fmts": []},   
        "vb0": {"suf": "-Position.buf", "fmts": []},     
    }
    return buffer_dict

@register_pattern(game, name)
def get_patterns():
    pattern_dict:Dict[str,List[Any]]={}
    pattern_dict.update(deepcopy(default.pattern_dcit))
    pattern_dict.update({
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_BLEND:[  
            {
                "section":"[TextureOverride_{ib_alias}_{blend_buf_name}]",
                "re":"^(hash = {blend_hash}\n{blend_buf} = Resource_{ib_alias}_{blend_buf_name}\n).*?$",
                "context":'hash = {blend_hash}\n' +
                          'handling = skip\n' +
                          'if DRAW_TYPE == 1\n' +
                          '    vb0 = Resource_{ib_alias}_{position_buf_name}\n' +
                          '    vb2 = Resource_{ib_alias}_{blend_buf_name}\n' +
                          '    draw = {vertex_count}, 0\n' +
                          'elif DRAW_TYPE == 8\n' +
                          '    $\\SRMI\\vertex_count = {vertex_count}\n' +
                          '    Resource\\SRMI\\PositionBuffer = Resource_{ib_alias}_{position_buf_name}CS\n' +
                          '    Resource\\SRMI\\BlendBuffer = Resource_{ib_alias}_{blend_buf_name}CS\n' +
                          'endif\n',
                "type":ReplaceType.REPLACE,
            }, 
            {
                "section":"[Resource_{ib_alias}_{position_buf_name}CS]",
                "re":".*?(filename = "+f"{FOLDER_NAME.BUFFER}"+"/{position_file}).*?",
                "context":'type = StructuredBuffer\n' +
                          'stride = {position_stride}\n' +
                          'filename = '+f"{FOLDER_NAME.BUFFER}"+'/{position_file}\n',
                "type":ReplaceType.REPLACE,
            }, 
            {
                "section":"[TextureOverride_{ib_alias}_{position_buf_name}]",
                "re":"^(hash = {hash}\n{position_buf} = Resource_{ib_alias}_{position_buf_name}).*?$",
                "context":'\n',
                "type":ReplaceType.REPLACE,
            },
            {
                "section":"[Resource_{ib_alias}_{blend_buf_name}CS]",
                "re":".*?(filename = "+f"{FOLDER_NAME.BUFFER}"+"/{blend_file}).*?",
                "context":'type = StructuredBuffer\n' +
                          'stride = {blend_stride}\n' +
                          'filename = '+f"{FOLDER_NAME.BUFFER}"+'/{blend_file}\n',
                "type":ReplaceType.REPLACE,
            }, 
        ],
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_DRAW:[        
            {
                "section":"[TextureOverride_{ib_alias}_{hash}_Draw]",
                "re":"^(hash = {hash}\n).*?$",
                "context":'hash = {hash}\n' +
                          'override_byte_stride = {stride}\n' +
                          'override_vertex_count = {vertex_count}\n' +
                          'uav_byte_stride = 4\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_CUSTOMSHADER_SHAPEKEY:[
            {
                "section":"[Resource_{ib_alias}_tmp{suf_name}]",
                "re":".*?",
                "context":"",
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[CommandList_Shapekey_Compute_{ib_alias}]",
                "re":".*?    {out_slot} = copy Resource_{ib_alias}_{new_suf_name}.*?",
                "context":"if $costume_mods\n"+
                          "    {out_slot} = copy Resource_{ib_alias}_{new_suf_name}\n"+
                          "    Resource_{ib_alias}_{new_suf_name} = copy ref {out_slot}\n"+
                          "    Resource_{ib_alias}_tmp{suf_name} = copy {out_slot}\n"+
                          "    x88 = 0\n"+
                          "    y88 = 0\n"+
                          "    z88 = 0\n"+
                          "    w88 = 0\n"+
                          "    {out_slot} = null\n"+
                          "    cs-t50 = null\n"+
                          "    Resource_{ib_alias}_{new_suf_name}CS = copy Resource_{ib_alias}_tmp{suf_name}\n"+
                          "endif\n",
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[CustomShader_Shapekey{shapekey_type}_{thread_group_count}]",
                "re":".*?vs = null.*?",
                "context":";**** SHAPE KEY SHADER ****\n"+
                          ";Contributors: Cybertron, SinsOfSeven, DiXiao\n"+
                          "vs = null\n"+
                          "hs = null\n"+
                          "ds = null\n"+
                          "gs = null\n"+
                          "ps = null\n"+
                          "cs = "+f"{FOLDER_NAME.RES}"+"/Shapekey{shapekey_type}.hlsl\n"+
                          "run = BuiltInCommandListUnbindAllRenderTargets\n"+
                          "dispatch =  {thread_group_count}, 1, 1\n",
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[TextureOverride_{ib_alias}",
                "re":".*?(Resource_{ib_alias}_{suf_name}).*?",
                "context":"Resource_{ib_alias}_{new_suf_name}",
                "type":ReplaceType.MULTI_REPLACE,
            }
        ],        
    })
    return pattern_dict
