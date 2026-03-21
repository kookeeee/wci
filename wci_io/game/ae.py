from typing import Dict,List,Any,Tuple
from ..constants import Game,WCI_PATTERN_NAME,ReplaceType,FOLDER_NAME
from copy import deepcopy
from .game_dict import register_buffer, register_pattern
from ..game import default
game = Game.AE
name = "终末地"


@register_buffer(game, name)
def get_buffers():
    buffer_dict={
        "ib": {
            "suf": ".ib",
            "z-normal": True,
            "write":"bin",
            "slots": [
                {
                    "ps-t20": {"name": "DiffuseMap"},
                    "ps-t21": {"name": "LightMap"},
                    "ps-t22": {"name": "NormalMap"},
                    "ps-t23": {"name": "GlowMap"},
                },
                {
                    "ps-t20": {"name": "DiffuseMap"},
                    "ps-t21": {"name": "LightMap"},
                    "ps-t22": {"name": "NormalMap"},
                },
                {
                    "ps-t19": {"name": "DiffuseMap"},
                    "ps-t20": {"name": "LightMap"},
                    "ps-t21": {"name": "NormalMap"},
                },
                {
                    "ps-t19": {"name": "DiffuseMap"},
                    "ps-t20": {"name": "LightMap"},
                    "ps-t21": {"name": "NormalMap"},
                    "ps-t22": {"name": "GlowMap"},
                },
                {
                    "ps-t18": {"name": "DiffuseMap"},
                    "ps-t19": {"name": "LightMap"},
                    "ps-t20": {"name": "NormalMap"},
                    "ps-t21": {"name": "GlowMap"},
                },
                {
                    "ps-t18": {"name": "DiffuseMap"},
                    "ps-t19": {"name": "LightMap"},
                    "ps-t20": {"name": "NormalMap"},
                },
                {
                    "ps-t17": {"name": "DiffuseMap"},
                    "ps-t18": {"name": "LightMap"},
                    "ps-t19": {"name": "NormalMap"},
                    "ps-t20": {"name": "GlowMap"},
                },  
                {
                    "ps-t17": {"name": "DiffuseMap"},
                    "ps-t18": {"name": "LightMap"},
                    "ps-t19": {"name": "NormalMap"},
                },  
                {
                    "ps-t16": {"name": "DiffuseMap"},
                    "ps-t17": {"name": "LightMap"},
                    "ps-t18": {"name": "NormalMap"},
                    "ps-t19": {"name": "GlowMap"},
                },  
                {
                    "ps-t16": {"name": "DiffuseMap"},
                    "ps-t17": {"name": "LightMap"},
                    "ps-t18": {"name": "NormalMap"},
                },    
                {
                    "ps-t15": {"name": "DiffuseMap"},
                    "ps-t16": {"name": "LightMap"},
                    "ps-t17": {"name": "NormalMap"},
                    "ps-t18": {"name": "GlowMap"},
                },  
                {
                    "ps-t15": {"name": "DiffuseMap"},
                    "ps-t16": {"name": "LightMap"},
                    "ps-t17": {"name": "NormalMap"},
                },                    
                {
                    "ps-t14": {"name": "DiffuseMap"},
                    "ps-t15": {"name": "LightMap"},
                    "ps-t16": {"name": "NormalMap"},
                    "ps-t17": {"name": "GlowMap"},
                },
                {
                    "ps-t14": {"name": "DiffuseMap"},
                    "ps-t15": {"name": "LightMap"},
                    "ps-t16": {"name": "NormalMap"},
                },
                {
                    "ps-t13": {"name": "DiffuseMap"},
                    "ps-t14": {"name": "LightMap"},
                    "ps-t15": {"name": "NormalMap"},
                    "ps-t16": {"name": "GlowMap"},
                },
                {
                    "ps-t13": {"name": "DiffuseMap"},
                    "ps-t14": {"name": "LightMap"},
                    "ps-t15": {"name": "NormalMap"},
                },
                {
                    "ps-t12": {"name": "DiffuseMap"},
                    "ps-t13": {"name": "LightMap"},
                    "ps-t14": {"name": "NormalMap"},
                    "ps-t15": {"name": "GlowMap"},
                },
                {
                    "ps-t12": {"name": "DiffuseMap"},
                    "ps-t13": {"name": "LightMap"},
                    "ps-t14": {"name": "NormalMap"},
                },
                {
                    "ps-t11": {"name": "DiffuseMap"},
                    "ps-t12": {"name": "LightMap"},
                    "ps-t13": {"name": "NormalMap"},
                    "ps-t14": {"name": "GlowMap"},
                },
                {
                    "ps-t11": {"name": "DiffuseMap"},
                    "ps-t12": {"name": "LightMap"},
                    "ps-t13": {"name": "NormalMap"},
                },
                {
                    "ps-t10": {"name": "DiffuseMap"},
                    "ps-t11": {"name": "LightMap"},
                    "ps-t12": {"name": "NormalMap"},
                    "ps-t13": {"name": "GlowMap"},
                },
                {
                    "ps-t10": {"name": "DiffuseMap"},
                    "ps-t11": {"name": "LightMap"},
                    "ps-t12": {"name": "NormalMap"},
                },
                {
                    "ps-t0": {"name": "DiffuseMap"},
                    "ps-t1": {"name": "NormalMap"},
                    "ps-t2": {"name": "LightMap"},
                    "ps-t3": {"name": "GlowMap"},
                },
                {
                    "ps-t0": {"name": "DiffuseMap"},
                    "ps-t1": {"name": "NormalMap"},
                    "ps-t2": {"name": "LightMap"},
                },
                {
                    "ps-t0": {"name": "DiffuseMap"},
                    "ps-t1": {"name": "NormalMap"},
                },
                {
                    "ps-t18": {"name": "DiffuseMap"},
                    "ps-t19": {"name": "NormalMap"},
                    "ps-t20": {"name": "GlowMap"},
                },  
            ],
        },
        "vb0": {"suf": "-Position.buf", "draw": "vb0", "write":"bin","fmts": []},
        "vb1": {"suf": "-Texcoord.buf", "draw": "vb1", "write":"bin","fmts": []},
        "vb2": {"suf": "-Blend.buf", "draw": "vb2", "write":"bin","fmts": []},
    }
    return buffer_dict

@register_pattern(game, name)
def get_patterns():
    pattern_dict:Dict[str,List[Any]]={}
    pattern_dict.update(deepcopy(default.pattern_dcit))
    pattern_dict.update({
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_BLEND:[  
            {
                "section":"[TextureOverride_{ib_alias}_Component{sub_alias}]",
                "re":"^(hash = {ib_hash}\nmatch_first_index = {match_first_index}\nmatch_index_count = {match_index_count}\nhandling = skip\nrun = CommandListSkinTexture\n).*?$",
                "context":'run = CommandList\EFMIv1\OverrideTextures\n' +
                          '{position_buf} = Resource_{ib_alias}_{position_buf_name}\n' +
                          '{texcoord_buf} = Resource_{ib_alias}_{texcoord_buf_name}\n' +
                          '{blend_buf} =Resource_{ib_alias}_{blend_buf_name}\n' +
                          'vb3 =  Resource_{ib_alias}_{position_buf_name}\n',
                "type":ReplaceType.APPEND_REPLACE,
            },      
        ],
        WCI_PATTERN_NAME.ADD_IB_SKIP:[
        ],
        WCI_PATTERN_NAME.ADD_CROSS_IB:[
            {
                "section":"[ShaderRegexEnableTextureOverrides]",
                "re":".*?(shader_model = vs_5_0).*?",
                "context":'shader_model = vs_5_0\n' +
                          'if $costume_mods\n' +
                          '    checktextureoverride = vs-cb0\n' +
                          '    checktextureoverride = vs-cb1\n' +
                          '    checktextureoverride = vs-cb2\n' +
                          'endif\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_DRAW:[        
           
        ],
        WCI_PATTERN_NAME.ADD_XXMI_MOD_LOAD:[
            {
                "section":"[Constants]",
                "re":".*?(lobal \$required_efmi_version = 1.00).*?",
                "context":'global $required_efmi_version = 1.00\n'+
                          'global $object_guid = {index_count}\n'+
                          'global $mesh_vertex_count = 0\n'+
                          'global $mod_id = -1000\n'+
                          'global $mod_enabled = 0\n'+
                          'global $object_detected = 0\n'+
                          'global $lod_detected = 0\n',
                        #  'if !$costume_mods\n'+
                        #  '  global $costume_mods = $mod_enabled\n'+
                        #  'endif\n'
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[Present]",
                "re":".*?(if $object_detected\n).*?",
                "context":#'$costume_mods = $mod_id\n'+
                          'if $object_detected\n'+
                          '    if $mod_enabled\n'+
                          '        post $object_detected = 0\n'+
                          '    else\n'+
                          '        if $mod_id == -1000\n'+
                          '            run = CommandListRegisterMod\n'+
                          '        endif\n'+
                          '    endif\n'+
                          'endif\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[CommandListRegisterMod]",
                "re":".*?(\$\\EFMIv1\\required_version = \$required_efmi_version).*?",
                "context":'$\EFMIv1\\required_version = $required_efmi_version\n'+
                           '$\EFMIv1\object_guid = $object_guid\n'+
                           'run = CommandList\EFMIv1\RegisterMod\n'+
                           '$mod_id = $\EFMIv1\mod_id\n'+
                           'if $mod_id >= 0\n'+
                           '    $mod_enabled = 1\n'+
                           'endif\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_BUF:[
            {
                "section":"[Resource_{ib_alias}_{buf_name}]",
                "re":".*?(filename = "+f"{FOLDER_NAME.BUFFER}"+"/{file}).*?",
                "context":'type = Buffer\n' +
                          'stride = {stride}\n' +
                          'filename = '+f'{FOLDER_NAME.BUFFER}' + '/{file}\n',
                "type":ReplaceType.NON_APPEND,
            }     
        ],        
    })
    #pattern_dict
    return pattern_dict