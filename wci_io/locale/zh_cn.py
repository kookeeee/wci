import  bpy
from typing import Dict, Tuple, Any

locale_key = "zh_CN" if bpy.app.version < (4, 0) else "zh_HANS"

from .en_us import translation_dictionary as en_us_dict


#中译英转换英译中
def translation_dictionary() -> Dict[Tuple[str, str], str]:
    zh_cn_dict:Dict[Tuple[str, str], str]={}
    for key,us_val in en_us_dict().items():
        context,zh_val=key
        zh_cn_dict[(context,us_val)] = zh_val
    return zh_cn_dict
