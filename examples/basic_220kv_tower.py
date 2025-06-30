#!/usr/bin/env python3
"""
基本220kV输电塔电磁场分析示例

这个示例展示了如何使用tower_em_solver进行基本的电磁场分析。
"""

import sys
import os
import numpy as np
from pathlib import Path

# 添加父目录到路径以导入求解器
sys.path.append(str(Path(__file__).parent.parent))

try:
    from tower_em_solver import solve_tower_electric_field
except ImportError as e:
    print(f"错误：无法导入求解器模块: {e}")
    print("请确保已安装Firedrake并激活虚拟环境")
    sys.exit(1)

def main():
    """运行基本的220kV输电塔电磁场分析"""
    
    print("🔋 开始220kV输电塔电磁场分析示例")
    print("=" * 50)
    
    # 设置输出目录
    output_dir = "./example_results"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📁 输出目录: {output_dir}")
    print(f"⚡ 电压等级: 220kV")
    print(f"🔧 求解器: Firedrake + 二阶有限元")
    
    try:
        # 运行求解器
        success = solve_tower_electric_field(
            output_dir=output_dir,
            npz_filename="basic_220kv_example",
            max_conductivity=35000,  # 限制最大电导率(S/m)
            robin_coeff=0.5         # Robin边界条件系数
        )
        
        if success:
            print("\n✅ 仿真成功完成！")
            
            # 分析结果
            result_files = list(Path(output_dir).glob("basic_220kv_example_*.npz"))
            if result_files:
                latest_result = max(result_files, key=os.path.getctime)
                print(f"📊 结果文件: {latest_result}")
                
                # 加载和分析数据
                analyze_results(latest_result)
            else:
                print("⚠️  未找到结果文件")
                
        else:
            print("❌ 仿真失败")
            return False
            
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def analyze_results(npz_file):
    """分析仿真结果"""
    
    print(f"\n📈 分析结果文件: {npz_file}")
    print("-" * 40)
    
    try:
        # 加载数据
        data = np.load(npz_file, allow_pickle=True)
        
        # 基本统计
        coordinates = data['coordinates']
        E_mag = data['E_mag']
        phi_real = data['phi_real']
        phi_imag = data['phi_imag']
        
        print(f"📍 数据点数量: {len(coordinates):,}")
        print(f"📏 空间范围:")
        print(f"   X: [{coordinates[:, 0].min():.1f}, {coordinates[:, 0].max():.1f}] m")
        print(f"   Y: [{coordinates[:, 1].min():.1f}, {coordinates[:, 1].max():.1f}] m") 
        print(f"   Z: [{coordinates[:, 2].min():.1f}, {coordinates[:, 2].max():.1f}] m")
        
        print(f"\n⚡ 电场强度统计:")
        print(f"   最小值: {E_mag.min():.2e} V/m")
        print(f"   最大值: {E_mag.max():.2e} V/m")
        print(f"   平均值: {E_mag.mean():.2e} V/m")
        print(f"   中位数: {np.median(E_mag):.2e} V/m")
        
        print(f"\n🔌 电位统计:")
        print(f"   实部范围: [{phi_real.min():.2e}, {phi_real.max():.2e}] V")
        print(f"   虚部范围: [{phi_imag.min():.2e}, {phi_imag.max():.2e}] V")
        
        # 数量级分布分析
        print(f"\n📊 电场强度数量级分布:")
        for exp in range(-10, 12):
            lower = 10**exp
            upper = 10**(exp+1)
            count = np.sum((E_mag >= lower) & (E_mag < upper))
            if count > 0:
                percentage = count / len(E_mag) * 100
                print(f"   1e{exp:2d} - 1e{exp+1:2d}: {count:8d} 点 ({percentage:5.2f}%)")
        
        # 检查元数据
        if 'metadata' in data:
            metadata = data['metadata'].item()
            if 'computation_time' in metadata:
                print(f"\n⏱️  计算时间: {metadata['computation_time']:.2f} 秒")
            if 'box_filter_info' in metadata:
                box_info = metadata['box_filter_info']
                print(f"📦 数据过滤: {box_info['box_air_points']}/{box_info['total_points']} ({box_info['percentage']:.1f}%)")
        
        print(f"\n✅ 数据分析完成")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🎉 示例运行完成！")
        print(f"💡 下一步可以尝试:")
        print(f"   - 修改电导率参数：max_conductivity")
        print(f"   - 调整边界条件：robin_coeff")
        print(f"   - 查看批量分析示例：batch_analysis.py")
    else:
        print(f"\n💔 示例运行失败")
        print(f"🔧 故障排除建议:")
        print(f"   - 检查Firedrake环境是否正确安装")
        print(f"   - 确认网格文件路径是否正确")
        print(f"   - 查看详细错误日志")
