import os
import json

from .ex_config import ExConfig
from ..wci_resources import WciResourceManager
from ...constants import WCI_PATTERN_NAME



#增加透明

def add_transpancy(ex_config:ExConfig,mod_manager:WciResourceManager):
    def get_customShader(draw,color):
        return f"""blend = ADD BLEND_FACTOR INV_BLEND_FACTOR
blend_factor[0] = {color[0]}
blend_factor[1] = {color[1]}
blend_factor[2] = {color[2]}
blend_factor[3] = {color[3]}
handling = skip
{draw}
"""
    for obj_name in ex_config.wci_transparency:
        trans_info=ex_config.wci_transparency[obj_name]
        index,drawPack = mod_manager.get_drawpack_by_obj_name(obj_name)
        if drawPack:
            cs_name="CustomShaderTransparency"+mod_manager.get_number_id("trans_"+obj_name,type_key="transpancy")
            #drawindexed = 0,0,0只有这种
            cs_raw_data=get_customShader(drawPack.draws[0],[trans_info["r"],trans_info["g"],trans_info["b"],trans_info["a"]])
            data_dict={
                "section":f"[{cs_name}]",
                "raw_data":cs_raw_data,
            }
            drawPack.draws=["run = "+cs_name]
            mod_manager.update_drawPack(drawPack)
            mod_manager.merge_to_sections(WCI_PATTERN_NAME.ADD_RAW,data_dict)
    return mod_manager