// =========================================================
// 纯净版：record_bones_cs.hlsl (数据存储器)
// =========================================================
StructuredBuffer<uint4> OriginalT0 : register(t0);
StructuredBuffer<uint4> DumpedCB1  : register(t1);


Texture1D<float4> IniParams : register(t120);

// 参数索引
#define PARAM_INDEX 86
#define target_offset (uint)IniParams[PARAM_INDEX].x * 1024


RWStructuredBuffer<uint4> SnapshotT0_UAV : register(u1);

[numthreads(64, 1, 1)] 
void main(uint3 tid : SV_DispatchThreadID) {
    uint id = tid.x;
    //最多只有192根骨骼吗？
    if (id >= 768) return;
    
    uint offset_current = DumpedCB1[5].x;
    uint offset_prev    = DumpedCB1[5].y;
    
    uint cur_idx  = (offset_current + id) % 600000;
    uint prev_idx = (offset_prev + id) % 600000;
    
    // 🌟【究极简化】：永远只往基础位置写数据！
    SnapshotT0_UAV[target_offset + id]          = OriginalT0[cur_idx];
    SnapshotT0_UAV[target_offset + 100000 + id] = OriginalT0[prev_idx]; 
}