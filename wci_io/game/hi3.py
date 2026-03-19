from typing import Dict,List,Any,Tuple
from copy import deepcopy
from ..constants import Game,WCI_PATTERN_NAME,ReplaceType
from .game_dict import register_buffer, register_pattern
from ..game import default

game = Game.HI3
name = "崩坏3"

@register_buffer(game, name)
def get_buffers():
    buffer_dict={
        "ib": {
            "suf": ".ib",
            "z-normal": False,
            "slots": [
                {
                    "ps-t0": {"name": "DiffuseMap"},
                    "ps-t1": {"name": "LightMap"},
                    "ps-t2": {"name": "NormalMap"},
                },
                {
                    "ps-t0": {"name": "DiffuseMap"},
                    "ps-t1": {"name": "LightMap"},
                },
                {
                    "ps-t0": {"name": "LightMap"},
                    "ps-t1": {"name": "DiffuseMap"},
                },
                {
                    "ps-t0": {"name": "DiffuseMap"},
                },
            ],
        },
        "vb0": {"suf": "-Position.buf", "draw": "vb0", "fmts": []},
        "vb1": {"suf": "-Texcoord.buf", "fmts": []},
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
                "context":'{position_buf} = Resource_{ib_alias}_{position_buf_name}\n' +
                          'draw = {vertex_count}, 0\n',
                "type":ReplaceType.APPEND_REPLACE,
            },      
        ],        
    })
    #pattern_dict
    return pattern_dict
