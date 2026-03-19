from typing import Dict,List,Any,Tuple
from copy import deepcopy
from ..constants import Game,WCI_PATTERN_NAME,ReplaceType
from .game_dict import register_buffer, register_pattern
from ..game import default

game = Game.ZZZ
name = "绝区零"

@register_buffer(game, name)
def get_buffers():
    return {
    "ib": {
        "suf": ".ib",
        "z-normal": False,
        "slots": [
            {
                "ps-t3": {"name": "DiffuseMap"},
                "ps-t4": {"name": "NormalMap"},
                "ps-t5": {"name": "LightMap"},
                "ps-t6": {"name": "MaterialMap"},
            },
            {
                "ps-t0": {"name": "DiffuseMap"},
                "ps-t1": {"name": "NormalMap"},
                "ps-t2": {"name": "LightMap"},
            },
            {
                "ps-t3": {"name": "DiffuseMap"},
            },
            {
                "ps-t0": {"name": "DiffuseMap"},
            }
        ],
    },
    "vb0": {"suf": "-Position.buf", "draw": "vb0", "fmts": []},
    "vb1": {"suf": "-Texcoord.buf", "fmts": []},
    "vb2": {"suf": "-Blend.buf", "fmts": []},
}

@register_pattern(game, name)
def get_patterns():
    pattern_dict:Dict[str,List[Any]]={}
    pattern_dict.update(deepcopy(default.pattern_dcit))
    pattern_dict.update({
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_BLEND:[  
            {
                "section":"[TextureOverride_{ib_alias}_{position_buf_name}]",
                "re":"^(hash = {position_hash}\n{position_buf} = Resource_{ib_alias}_{position_buf_name}\n).*?$",
                "context":'{blend_buf} = Resource_{ib_alias}_{blend_buf_name}\n' +
                        'draw = {vertex_count}, 0\n',
                "type":ReplaceType.APPEND_REPLACE,
            },      
        ],
        WCI_PATTERN_NAME.ADD_CROSS_IB:[
            {
                "section":"[Resource_{ib_alias}_VB0]",
                "re":"",
                "context":"",
                "type":ReplaceType.APPEND_REPLACE
            },
            {
                "section":"[TextureOverride_{ib_alias}_Component{sub_alias}]",
                "re":".*?(ib = Resource_{ib_alias}_Component{sub_alias}\n).*?",
                "context":'Resource_{ib_alias}_VB0 = copy vb0\n',
                "type":ReplaceType.APPEND_REPLACE
            },
        ],
    })
    return pattern_dict