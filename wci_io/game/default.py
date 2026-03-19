from ..constants import WCI_PATTERN_NAME,ReplaceType,FOLDER_NAME

pattern_dcit={
        WCI_PATTERN_NAME.ADD_PRESENT:[
            {
                "section":"[Present]",
                "re":".*?(\${var} = {pre_value}).*?",
                "context":'${var} = {pre_value}\n',
                "type":ReplaceType.NON_APPEND,
            }
        ],
        WCI_PATTERN_NAME.ADD_PRESENT_POST:[
            {
                "section":"[Present]",
                "re":".*?(post \${var} = {pre_value}).*?",
                "context":'post ${var} = {pre_value}\n',
                "type":ReplaceType.NON_APPEND,
            }
        ],
        WCI_PATTERN_NAME.ADD_PRESENT_INIT:[
            {
                "section":"[Present]",            
                "re":".*?(post \$active = 0\n).*?",
                "context":'post $active = 0\n',
                "type":ReplaceType.NON_APPEND,
            }
        ],
        WCI_PATTERN_NAME.ADD_CONSTANTS_KEY:[
            {
                "section":"[Constants]",            
                "re":".*?(global \${var} =).*?",
                "context":'global ${var} = {defaultvalue}\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_CONSTANTS_PERSIST_KEY:[
            {
                "section":"[Constants]",
                "re":".*?(global persist \${var} =).*?",
                "context":'global persist ${var} = {defaultvalue}\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_CONSTANTS_INIT:[
            {
                "section":"[Constants]",
                "re":".*?(global \$active = 0\n).*?",
                "context":'global $active = 0\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[Constants]",
                "re":".*?(global \$creditinfo = 1\n).*?",
                "context":'global $creditinfo = 1\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_TEX_RESOURCE:[
            {
                "section":"[{resource}]",
                "re":'.*?(filename = '+f'{FOLDER_NAME.TEXTURE}' + '/{file}).*?',
                "context":'filename = '+f'{FOLDER_NAME.TEXTURE}' + '/{file}\n',
                "type":ReplaceType.NON_APPEND,
            },  
        ],
        WCI_PATTERN_NAME.ADD_TEXOVERRIDE_HASH:[
            {
                "section":"[TextureOverride_{hash}_{texname}]",
                "re":"^.*?(hash = {hash}\n).*?$",
                "context":'hash = {hash}\n' +
                          'this = {resource}\n',
                "type":ReplaceType.NON_APPEND,
            }, 
        ],
        WCI_PATTERN_NAME.ADD_RAW:[
        {
            "section":"{section}",
            "re":".*?({raw_data}}).*?",
            "context":'{raw_data}\n',
            "type":ReplaceType.NON_APPEND,
        },
        ],
        WCI_PATTERN_NAME.ADD_CHECK_TEX:[
            {
                "section":"[CommandListSkinTexture]",
                "re":"^.*?(checktextureoverride = {slot}).*?$",
                "context":'checktextureoverride = {slot}\n',
                "type":ReplaceType.NON_INSERT,
            },
        ],
        WCI_PATTERN_NAME.ADD_IB_SKIP:[
            {
                "section":"[TextureOverride_{ib_alias}_IB]",
                "re":"^(hash = {ib_hash}\nhandling = skip\n)$",
                "context":'hash = {ib_hash}\n' +
                          'handling = skip\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_IB:[        
            {
                "section":"[TextureOverride_{ib_alias}_Component{sub_alias}]",
                "re":"^(hash = {ib_hash}\nmatch_first_index = {match_first_index}\nmatch_index_count = {match_index_count}\nhandling = skip\n).*?$",
                "context":'hash = {ib_hash}\n' +
                          'match_first_index = {match_first_index}\n' +
                          'match_index_count = {match_index_count}\n' +
                          'handling = skip\n' +
                          'run = CommandListSkinTexture\n' +
                          'ib = Resource_{ib_alias}_Component{sub_alias}\n' +
                          'drawindexed = auto\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[Resource_{ib_alias}_Component{sub_alias}]",
                "re":".*?(filename = "+f"{FOLDER_NAME.BUFFER}"+"/{file}).*?",
                "context":'type = Buffer\n' +
                          'format = {format}\n' +
                          'filename = '+f"{FOLDER_NAME.BUFFER}"+'/{file}\n',
                "type":ReplaceType.NON_APPEND,
            }
        ],
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_BUF:[  
            {
                "section":"[TextureOverride_{ib_alias}_{buf_name}]",
                "re":"^(hash = {hash}\n{buf} = Resource_{ib_alias}_{buf_name}).*?$",
                "context":'hash = {hash}\n' +
                          '{buf} = Resource_{ib_alias}_{buf_name}\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[Resource_{ib_alias}_{buf_name}]",
                "re":".*?(filename = "+f"{FOLDER_NAME.BUFFER}"+"/{file}).*?",
                "context":'type = Buffer\n' +
                          'stride = {stride}\n' +
                          'filename = '+f'{FOLDER_NAME.BUFFER}' + '/{file}\n',
                "type":ReplaceType.NON_APPEND,
            }     
        ],
        WCI_PATTERN_NAME.ADD_TEXTUREOVERRIDE_DRAW:[        
            {
                "section":"[TextureOverride_{ib_alias}_{hash}_Draw]",
                "re":"^(hash = {hash}\n).*?$",
                "context":'hash = {hash}\n' +
                          'override_byte_stride = {stride}\n' +
                          'override_vertex_count = {vertex_count}\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_DRAWINDEXED:[        
            {
                "section":"[TextureOverride_{ib_alias}_Component{sub_alias}]",
                "re":"^.*?(drawindexed = auto).*?$",
                "context":'{raw_draw}\n',
                "type":ReplaceType.REPLACE,
            },
        ],        
        WCI_PATTERN_NAME.ADD_DRAWINDEXED_LOD:[        
            {
                "section":"{section}",
                "re":"^.*?(drawindexed = auto).*?$",
                "context":'{raw_draw}\n',
                "type":ReplaceType.REPLACE,
            },
        ], 
        WCI_PATTERN_NAME.ADD_FRAME_INIT:[
            {
                "section":"[Present]",
                "re":".*?(if \$n < \(\$max_frame - \$min_frame\)\n).*?",
                "context":'local $steps = 2 * ($max_frame - $min_frame)\n'+
                          'local $t = time * $fps * $speed\n'+
                          'local $n = ($t % $steps) // 1\n'+
                          'if $n < ($max_frame - $min_frame)\n'+
                          '    $frame = $min_frame + $n\n'+
                          'else\n'+
                          '    $frame = $max_frame - ($n - ($max_frame - $min_frame))\n'+
                          'endif\n',
                "type":ReplaceType.NON_APPEND
            },
        ],
        WCI_PATTERN_NAME.ADD_GLOW_INIT:[
            {
                "section":"[ResourceEngineRGB]",
                "re":"",
                "context":"",
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[Constants]",
                "re":".*?(ResourceEngineRGB = copy Resource\\\RabbitFX\\\FXBuffer).*?",
                "context":'ResourceEngineRGB = copy Resource\\RabbitFX\\FXBuffer\n',
                "type":ReplaceType.NON_INSERT,
            },
            {
                "section":"[Present]",
                "re":".*?(\$glow_frame = \(\( time % \$speed \) \* \(\$glow_fps \/ \$speed \)\)//1\nif \$glow_frame \> \$glow_fps \/\/ 2\n\t\$glow_frame = \$glow_fps \- \$glow_frame\nendif\n).*?",
                "context":'$glow_frame = (( time % $speed ) * ($glow_fps / $speed ))//1\n' +
                          'if $glow_frame > $glow_fps // 2\n' +
                          '\t$glow_frame = $glow_fps - $glow_frame\n' +
                          'endif\n',
                "type":ReplaceType.NON_APPEND
            },
        ],
        WCI_PATTERN_NAME.ADD_ACTIVE_FLAG:[
            {
                "section":"[Constants]",
                "re":".*?(global \$active.*?\n).*?",
                "context":"global $active = 0\n",
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[Present]",
                "re":".*?(post \$active = 0\n).*?",
                "context":"post $active = 0\n",
                "type":ReplaceType.NON_APPEND,                    
            },
            {
                "section":"[TextureOverride_{ib_alias}_Component",
                "re":".*?(\${var} = 1\n).*?",
                "context":'${var} = 1\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_CONTROL_ACTIVE_IB:[
            {
                "section":"[TextureOverride_{ib_alias}",
                "re":"^(.*)$",
                "context":"    ",
                "type":ReplaceType.LINE_INSERT,
            },
            {
                "section":"[TextureOverride_{ib_alias}",
                "re":"^(.*)$",
                "context":'if ${key} == 1\n',
                "type":ReplaceType.INSERT_REPLACE,
            },
            {
                "section":"[TextureOverride_{ib_alias}",
                "re":"^(.*)$",
                "context":'endif\n',
                "type":ReplaceType.APPEND_REPLACE,
            }
        ],
        WCI_PATTERN_NAME.ADD_CROSS_CONST:[
            {
                "section":"[Resource_{src_ib_alias}_{name}]",
                "re":"",
                "context":"",
                "type":ReplaceType.APPEND_REPLACE
            },
            {
                "section":"[Resource_{des_ib_alias}_{name}]",
                "re":"",
                "context":"",
                "type":ReplaceType.APPEND_REPLACE
            },
            {
                "section":"[TextureOverride_{src_ib_alias}_IB]",
                "re":".*?(Resource_{src_ib_alias}_{name} = copy vs-{name}).*?",
                "context":'Resource_{src_ib_alias}_{name} = copy vs-{name}\n',
                "type":ReplaceType.NON_APPEND
            },
            {
                "section":"[TextureOverride_{des_ib_alias}_IB]",
                "re":".*?(Resource_{des_ib_alias}_{name} = copy vs-{name}).*?",
                "context":'Resource_{des_ib_alias}_{name} = copy vs-{name}\n',
                "type":ReplaceType.NON_APPEND
            },
        ],
        WCI_PATTERN_NAME.ADD_SHADER_FIX:[
            {
                "section":"[CustomShaders_{hash}]",
                "re":"{shader_type} = .*?{filename}.*?",
                "context":'{shader_type} = '+f'{FOLDER_NAME.RES}' + '/{filename}\n' +
                          'handling = skip\n' +
                          '{draw_type}draw = from_caller\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[ShaderOverride_{hash}]",
                "re":".*?hash = {hash}.*?",
                "context":'hash = {hash}\n' +
                          'allow_duplicate_hash = overrule\n' +
                          '$shadervar = 1\n' +
                          'if $active == 1\n' +
                          '\trun = CustomShaders_{hash}\n' +
                          'endif\n',
                "type":ReplaceType.NON_APPEND,
            }
        ],
        WCI_PATTERN_NAME.ADD_VS_CHECK:[
            {
                "section":"[ShaderOverride_{vs}]",
                "re":"hash = {vs}.*?",
                "context":'hash = {vs}\n' +
                          'allow_duplicate_hash = overrule\n'+
                          'if $costume_mods\n' +
                          '    checktextureoverride = ib\n' +
                          'endif\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_FILTER:[
            {
                "section":"[{section_type}_{hash}]",
                "re":"(hash = {hash}\n).*?",
                "context":'hash = {hash}\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[{section_type}_{hash}]",
                "re":"(filter_index).*?",
                "context":'filter_index = {filter_index}\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_VAR_FILTER:[
            {
                "section":"[{section_type}_{hash}]",
                "re":"(hash = {hash}\n).*?",
                "context":'hash = {hash}\nallow_duplicate_hash = overrule\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[{section_type}_{hash}]",
                "re":"(\${var} = {value}).*?",
                "context":'${var} = {value}\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_BMSR_FILTER:[
            {
                "section":"[TextureOverride_{ib_alias}_Component{sub_alias}]",
                "re":"^(.*)$",
                "context":"    ",
                "type":ReplaceType.LINE_INSERT,
            },
            {
                "section":"[TextureOverride_{ib_alias}_Component{sub_alias}]",
                "re":"(if \${var} == 1 && \$active == 1\n).*?",
                "context":'if ${var} == 1 && $active == 1\n',
                "type":ReplaceType.NON_INSERT,
            },
            {
                "section":"[TextureOverride_{ib_alias}_Component{sub_alias}]",
                "re":".*?\n(endif)\n$",
                "context":'endif\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
        WCI_PATTERN_NAME.ADD_CUSTOMSHADER_SHAPEKEY:[
            {
                "section":"[CommandList_Shapekey_Compute_{ib_alias}]",
                "re":".*?    {out_slot} = copy Resource_{ib_alias}_{new_suf_name}.*?",
                "context":"if $costume_mods\n"+
                          "    {out_slot} = copy Resource_{ib_alias}_{new_suf_name}\n"+
                          "    Resource_{ib_alias}_{new_suf_name} = copy ref {out_slot}\n"+
                          "    x88 = 0\n"+
                          "    y88 = 0\n"+
                          "    z88 = 0\n"+
                          "    w88 = 0\n"+
                          "    {out_slot} = null\n"+
                          "    cs-t50 = null\n"+
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
                          "cs = "+f"{FOLDER_NAME.RES}" + "/Shapekey{shapekey_type}.hlsl\n"+
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
        WCI_PATTERN_NAME.ADD_COMMANDLIST_SHAPEKEY:[
            {
                "section":"[CommandList_Shapekey_{ib_alias}_Component{sub_alias}_{item_name}_{shapekey_name}]",
                "re":".*?cs-t50 = copy Resource_{ib_alias}_Position.*?",
                "context":'cs-t50 = copy Resource_{ib_alias}_{suf_name}\n' +
                          'x88 = {weight_var}\n' +
                          'y88 = {vertex_count}\n' +
                          'z88 = {base_vertex_index}\n' +
                          'w88 = {shapekey_vertex_index}\n' +
                          'run = CustomShader_Shapekey{shapekey_type}_{thread_group_count}\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[CommandList_Shapekey_Compute_{ib_alias}]",
                "re":".*?(    {out_slot} = copy Resource_{ib_alias}_{new_suf_name}).*?",
                "context":'\n' +
                          '    run = CommandList_Shapekey_{ib_alias}_Component{sub_alias}_{item_name}_{shapekey_name}',
                "type":ReplaceType.APPEND_REPLACE,
            },
            {
                "section":"[CommandListComputeShapekeys]",
                "re":".*?(run = CommandList_Shapekey_Compute_{ib_alias}\n).*?",
                "context":'run = CommandList_Shapekey_Compute_{ib_alias}\n',
                "type":ReplaceType.NON_APPEND,
            },

        ],
        WCI_PATTERN_NAME.ADD_SHAPEKEY_UI:[
            {
                "section":"[Present]",
                "re":".*?(    run = CommandListComputeShapekeys\n).*?",
                "context":'    $currentSlider = {number_id}\n'+
                          '    run = CommandListInterpolateSlider{number_id}\n'+
                          '    run = CommandListComputeShapekeys\n',
                "type":ReplaceType.REPLACE,
            },
            {
                "section":"[CommandListResetMenuPos]",
                "re":".*?(run = CommandListResetSlider{number_id}\n).*?",
                "context":'run = CommandListResetSlider{number_id}\n',
                "type":ReplaceType.NON_APPEND,
            },
            {
                "section":"[CommandListDrawAllSliders]",
                "re":".*?(run = CommandListDrawFullSlider{number_id}\n).*?",
                "context":'; 绘制滑块{number_id}\n'+
                          '$slider_base_x = $z0\n'+
                          '$slider_base_y = w87 + {base_y} / $wh\n'+   
                          '; 图标左上角 Y\n'+
                          'run = CommandListDrawFullSlider{number_id}\n'+
                          'w87 = $slider_base_y + $wo\n',
                "type":ReplaceType.NON_APPEND,
            },
        ],
}