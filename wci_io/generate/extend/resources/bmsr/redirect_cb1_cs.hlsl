// =========================================================
// 纯净版：redirect_cb1_cs.hlsl (指针篡改器)
// =========================================================
StructuredBuffer<uint4> DumpedCB1  : register(t0);

Texture1D<float4> IniParams : register(t120);

// 参数索引
#define PARAM_INDEX 86

#define target_offset (uint)IniParams[PARAM_INDEX].x * 1024

RWStructuredBuffer<uint4> RedirectCB1_UAV : register(u0); 

[numthreads(1024, 1, 1)] 
void main(uint3 tid : SV_DispatchThreadID) {
    uint id = tid.x;
    if (id >= 4096) return; 

    uint4 cb_data = DumpedCB1[id];
    if (id == 5) {
        cb_data.x = target_offset;               
        cb_data.y = target_offset + 100000;      
    }
    RedirectCB1_UAV[id] = cb_data; 
}