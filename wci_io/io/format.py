import struct
import bpy
import mathutils
import math
from typing import Tuple





class DXGIFormater:
    """
    DXGI格式编解码器静态类
    
    提供DirectX图形格式的编码/解码功能，支持
    """    
    # ---------- 位置编解码 ----------
    @staticmethod
    def decode_position(value, fmt, fmt_char, byte_size, var_size):
        if var_size==4:
            x,y,z,w=struct.unpack(fmt_char, value)
            if w==0:
                nx,ny,nz=(0,0,0)
            elif w==1:
                nx,ny,nz=x,y,z
            else:
                nx,ny,nz=(x/w,y/w,z/w)
            return x,y,z
        else:
            return struct.unpack(fmt_char, value)
        
    @staticmethod
    def encode_position(position, fmt, fmt_char, byte_size, var_size):
        return struct.pack(fmt_char, *position)
    
    # ---------- 法线编解码 ----------
    @staticmethod
    def decode_normal(value, fmt, fmt_char, byte_size, var_size,z_normal=False):
        """
        解码法线数据
        
        Args:
            value: 
            fmt (str): 格式字符串
            z_normal (bool): 是否使用Z压缩法线
            
        Returns:
            tuple: (nx, ny, nz) 法线向量
        """
        if var_size==1:
            #处理Z压缩法线
            value = struct.unpack('<I', value)[0]
            nx,ny,nz= DXGIFormater.decode_normal_uint32(value)
            
        else:
            value = struct.unpack(fmt_char,value)[:3]
            value = DXGIFormater.norm_to_float(value,fmt)
            nx,ny,nz = value[0:3]
        return (nx,ny,nz)
    

    @staticmethod
    def decode_normal_uint32(raw_val):
        """解码AEMI八面体法线编码（10-10-10-2打包格式）"""
        
        # AEMI八面体法线编码（10-10-10打包）
        mask_10bit = 0x3FF
        

        # 提取最后一位符号位
        bit31 = (raw_val >> 31) & 0x1  # 切线手性
        # 提取10位分量
        x_raw = raw_val & mask_10bit
        y_raw = (raw_val >> 10) & mask_10bit
        z_raw = (raw_val >> 20) & mask_10bit
        
        # 10位有符号整数转换
        x_int = x_raw if x_raw < 512 else x_raw - 1024
        y_int = y_raw if y_raw < 512 else y_raw - 1024
        z_int = z_raw if z_raw < 512 else z_raw - 1024
        
        # 归一化到大约[-1, 1]
        scale = 0.00195694715
        x = x_int * scale
        y = y_int * scale
        oz = z_int * scale  # 原始z值
        
        # 重建Z分量
        z = 1.0 - abs(x) - abs(y)
        # 八面体映射包装
        if z < 0:
            sign_x = 1.0 if x_int >= 0 else -1.0
            sign_y = 1.0 if y_int >= 0 else -1.0
            wrapped_x = (1.0 - abs(y)) * sign_x
            wrapped_y = (1.0 - abs(x)) * sign_y
            nx = wrapped_x
            ny = wrapped_y
        else:
            nx = x
            ny = y
        
        nz = z
        
        # 归一化向量
        norm = (nx*nx + ny*ny + nz*nz) ** 0.5
        if norm == 0:
            norm = 1.0  # 避免除以零
        
        nx /= norm
        ny /= norm
        nz /= norm
        return (nx,ny,nz)
        
    @staticmethod
    def encode_normal(normal, tangent,bitangent_sign,fmt, fmt_char, byte_size, var_size, z_normal=False):
        """
        编码法线数据
        
        Args:
            normal (tuple): (nx, ny, nz) 法线向量
            fmt (str): 格式字符串
            z_normal (bool): 是否使用Z压缩法线s
            切线空间法线向量的第三个分量,是z
            
        Returns:
            bytes: 编码后的字节串
        """
        if var_size==1:
            # Z压缩法线编码
            uint_normal=DXGIFormater.encode_normal_uint32(normal,tangent,bitangent_sign)
            return struct.pack('<I',uint_normal)
        else:
            value = DXGIFormater.float_to_norm(normal,fmt)
            return struct.pack(fmt_char, *value[:var_size])

    @staticmethod
    def tangent_angle_encode(normal, tangent):
        """
        将切线编码为相对于法线的旋转角度（10 位）
        输入：归一化法线、归一化切线（垂直于法线）
        返回：角度索引 -512 ,511
        """
        # 参考向量，避免与法线平行
        if abs(normal.z) < 0.999:
            ref = mathutils.Vector((0.0, 0.0, 1.0))
        else:
            ref = mathutils.Vector((0.0, 1.0, 0.0))

        # 投影 ref 到切平面
        r = ref - ref.dot(normal) * normal
        if r.length_squared < 1e-8:
            # 备选参考
            ref = mathutils.Vector((1.0, 0.0, 0.0))
            r = ref - ref.dot(normal) * normal
        r.normalize()

        # 第二个基向量 u = normal x r
        u_axis = normal.cross(r)
        u_axis.normalize()

        # 计算角度
        cos_theta = tangent.dot(r)
        sin_theta = tangent.dot(u_axis)
        theta = math.atan2(sin_theta, cos_theta)  # (-π, π]
        if theta < 0:
            theta += 2.0 * math.pi

        # 量化到 10 位
        idx = int(theta / (2.0 * math.pi) * 1023.0 + 0.5)
        return max(0, min(1023, idx)) -512


    @staticmethod
    def encode_normal_uint32(raw_normal,tangent,bitangent_sign):
        nx, ny, nz = raw_normal
        
        # 避免除以零
        l1_norm = abs(nx) + abs(ny) + abs(nz)
        if l1_norm == 0:
            l1_norm = 1.0
            
        nx /= l1_norm
        ny /= l1_norm
        nz /= l1_norm
        
        # 2. 处理 z < 0 的情况（八面体包裹）
        if nz < 0:
            sign_x = 1.0 if nx >= 0 else -1.0
            sign_y = 1.0 if ny >= 0 else -1.0
            
            tx = (1.0 - abs(ny)) * sign_x
            ty = (1.0 - abs(nx)) * sign_y
            
            nx = tx
            ny = ty
        
        # 3. 量化到 [-511, 511]
        scale = 511.0
        
        xq = int(round(nx * scale))
        yq = int(round(ny * scale))
        # 限制在10位有符号范围内 [-512, 511]
        xq = max(-512, min(511, xq))
        yq = max(-512, min(511, yq))
        # 4. 转换为10位无符号表示（通过 & 0x3FF处理二进制补码）
        xu = xq & 0x3FF
        yu = yq & 0x3FF
        # Blender切线手性与游戏相反，需要反转切线方向
        #tangent_reversed = mathutils.Vector((-tangent.x, -tangent.y, -tangent.z))
        zu = DXGIFormater.tangent_angle_encode(raw_normal, tangent) & 0x3FF
        
        # 位打包：Y左移10位，X在低位
        packed = xu | (yu << 10) | (zu<<20)
        
        # 设置第30位为1，以便在shader中启用解压缩
        packed |= 0x40000000

        # 手性标志保持不变（反转切线不需要翻转手性）
        if bitangent_sign == -1:
           packed |= 0x80000000
        return packed
    
    # ---------- 切线编解码 ----------
    
    @staticmethod
    def decode_tangent(value,  fmt, fmt_char, byte_size, var_size):
        """
        解码切线数据
        
        Args:
            value: 原始数据
            fmt (str): 格式字符串
            
        Returns:
            tuple: (tx, ty, tz, tw) 切线向量
        """
        value = struct.unpack(fmt_char, value)
        value = DXGIFormater.norm_to_float(value,fmt)
        return value
    
    @staticmethod
    def encode_tangent(tangent, fmt, fmt_char, byte_size, var_size):
        """
        编码切线数据
        
        Args:
            tangent (tuple): (tx, ty, tz, tw) 切线向量
            fmt (str): 格式字符串
            
        Returns:
            bytes: 编码后的字节串
        """
        value = DXGIFormater.float_to_norm(tangent,fmt)
        return struct.pack(fmt_char, *value[0:var_size])
    
    # ---------- UV坐标编解码 ----------
    
    @staticmethod
    def decode_uv(value,  fmt, fmt_char, byte_size, var_size):
        """
        解码UV坐标数据
        
        Args:
            value: 原始数据
            fmt (str): 格式字符串
            
        Returns:
            tuple: (u, v) 或 (u, v, ...) UV坐标
        """
        value =  struct.unpack(fmt_char, value)
        value = DXGIFormater.norm_to_float(value,fmt)
        if var_size==3:
            return (value[0],1-value[1]),(value[2],0)
        if var_size==4:
            return (value[0],1-value[1]),(value[2],value[3])
        else:
            return (value[0],1-value[1]),(0,0)
    
    @staticmethod
    def encode_uv(uv, fmt, fmt_char, byte_size, var_size):
        """
        编码UV坐标数据
        
        Args:
            uv (tuple): UV坐标，可能是(u, v)或(u, v, ...)
            fmt (str): 格式字符串
            
        Returns:
            bytes: 编码后的字节串
        """
        #翻转y轴
        uv[1]=1-uv[1]
        value = DXGIFormater.float_to_norm(uv,fmt)
        return struct.pack(fmt_char,*value[0:var_size])
    
    # ---------- 颜色编解码 ----------
    
    @staticmethod
    def decode_color(value,  fmt, fmt_char, byte_size, var_size):
        """
        解码颜色数据
        
        Args:
            value: 原始数据
            fmt (str): 格式字符串
            
        Returns:
            tuple: (r, g, b, a) 颜色值，范围[0.0, 1.0]
        """
        value= struct.unpack(fmt_char, value)
        value = DXGIFormater.norm_to_float(value,fmt)
        return value
    
    @staticmethod
    def encode_color(color:bpy.types.MeshLoopColor,  fmt, fmt_char, byte_size, var_size):
        """
        编码颜色数据
        
        Args:
            color (tuple): (r, g, b, a) 颜色值，范围[0.0, 1.0]
            fmt (str): 格式字符串
            
        Returns:
            bytes: 编码后的字节串
        """
        color=DXGIFormater.float_to_norm(color.color,fmt)
        return struct.pack(fmt_char,*color[0:var_size])
    
    # ---------- 混合权重编解码 ----------
    
    @staticmethod
    def decode_blend_weights(value, fmt, fmt_char, byte_size, var_size):
        """
        解码混合权重数据
        
        Args:
            value: 原始数据
            fmt (str): 格式字符串
            
        Returns:
            tuple: 权重值，范围[0.0, 1.0]
        """
        value =  struct.unpack(fmt_char, value)
        value = DXGIFormater.norm_to_float(value,fmt)
        return value
    
    @staticmethod
    def encode_blend_weights(weights, fmt, fmt_char, byte_size, var_size):
        """
        编码混合权重数据
        
        Args:
            weights (tuple): 权重值，范围[0.0, 1.0]
            fmt (str): 格式字符串
            
        Returns:
            bytes: 编码后的字节串
        """
        weights = DXGIFormater.float_to_norm(weights,fmt)
        return struct.pack(fmt_char, *weights[0:var_size])
    

    @staticmethod
    def decode_blend_indices(value, fmt, fmt_char, byte_size, var_size):
        """
        解码混合索引
        
        Args:
            value: 原始数据
            fmt (str): 格式字符串
            
        Returns:
            索引范围:范围[0,256]
        """
        return struct.unpack(fmt_char, value)
    
    @staticmethod
    def encode_blend_indices(indices, fmt, fmt_char, byte_size, var_size):
        return struct.pack(fmt_char, *indices[:var_size])

    @staticmethod  
    def normalize_vector(vector):
        """规格化向量（转换为单位向量）"""
        x, y, z = vector
        length = math.sqrt(x*x + y*y + z*z)
        if length > 0:
            return (x/length, y/length, z/length)
        else:
            return (0.0, 0.0, 1.0)  # 默认向上
        
    #取值，整数存储，浮点取值0,1或者-1，1
    @staticmethod
    def norm_to_float(value,fmt):
        nv=[]
        if "SNORM"==fmt[-5:]:
            if "8"==fmt[1]:
                for v in value:
                    nv.append(max(v / 127.0, -1.0))
            elif "16" == fmt[1:3]:
                for v in value:
                    nv.append(max(v / 32767.0, -1.0))
        elif "UNORM"==fmt[-5:]:
            if "8"==fmt[1]:
                for v in value:
                    nv.append(max(v / 255.0, 0))
            elif "16" == fmt[1:3]:
                for v in value:
                    nv.append(max(v / 65535.0, 0))
        else:
            nv=value
        return nv


        
        
    #存值 浮点 0,1或者-1，1 转换到0-255,0-65535,-127-127,-32767-32767
    #这种数据类型转换是GPU自动执行的
    @staticmethod
    def float_to_norm(value,fmt):
        nv=[]
        if "SNORM"==fmt[-5:]:
            if "8"==fmt[1]:
                for v in value:
                    nv.append(int(round(max(-1.0, min(1.0, v)) * 127.0)))
            elif "16" == fmt[1:3]:
                for v in value:
                    nv.append(int(round(max(-32767.0, min(1.0, v)) * 32767.0)))
        elif "UNORM"==fmt[-5:]:
            if "8"==fmt[1]:
                for v in value:
                    nv.append(int(round(max(0.0, min(1.0, v)) * 255.0)))
            elif "16" == fmt[1:3]:
                for v in value:
                    nv.append(int(round(max(0.0, min(1.0, v)) * 65535.0)))
        else:
            nv=value
        return nv

if __name__=="__main__":
    pass