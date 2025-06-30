#!/usr/bin/env python3
"""
批量电磁场分析示例

演示如何批量处理多种工况，生成用于AI训练的数据集。
"""

import sys
import os
import numpy as np
from pathlib import Path
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

try:
    from tower_em_solver import solve_tower_electric_field
except ImportError as e:
    print(f"错误：无法导入求解器模块: {e}")
    sys.exit(1)

def run_single_case(case_params):
    """运行单个案例"""
    case_name, params = case_params
    
    print(f"🔄 开始处理案例: {case_name}")
    
    try:
        # 创建案例专用目录
        case_dir = f"./batch_results/{case_name}"
        os.makedirs(case_dir, exist_ok=True)
        
        # 运行仿真
        success = solve_tower_electric_field(
            output_dir=case_dir,
            npz_filename=f"case_{case_name}",
            **params
        )
        
        if success:
            print(f"✅ 案例 {case_name} 完成")
            return case_name, True, None
        else:
            print(f"❌ 案例 {case_name} 失败")
            return case_name, False, "求解器返回失败"
            
    except Exception as e:
        print(f"❌ 案例 {case_name} 出错: {e}")
        return case_name, False, str(e)

def main():
    """批量分析主函数"""
    
    print("🔋 电力塔电磁场批量分析")
    print("=" * 50)
    
    # 定义不同的分析案例
    cases = {
        # 不同电导率水平
        "low_conductivity": {
            "max_conductivity": 1000,
            "robin_coeff": 0.5
        },
        "medium_conductivity": {
            "max_conductivity": 15000,
            "robin_coeff": 0.5
        },
        "high_conductivity": {
            "max_conductivity": 35000,
            "robin_coeff": 0.5
        },
        
        # 不同边界条件
        "weak_boundary": {
            "max_conductivity": 35000,
            "robin_coeff": 0.1
        },
        "strong_boundary": {
            "max_conductivity": 35000,
            "robin_coeff": 1.0
        },
        
        # 组合参数
        "extreme_case": {
            "max_conductivity": 50000,
            "robin_coeff": 0.8
        }
    }
    
    print(f"📋 计划运行 {len(cases)} 个案例:")
    for case_name, params in cases.items():
        print(f"   - {case_name}: {params}")
    
    # 创建批量结果目录
    os.makedirs("./batch_results", exist_ok=True)
    
    # 选择执行模式
    use_parallel = True  # 设置为False使用串行执行
    
    if use_parallel:
        # 并行执行（如果系统支持）
        print(f"\n🚀 使用并行模式执行（{multiprocessing.cpu_count()} 核心）")
        run_parallel(cases)
    else:
        # 串行执行
        print(f"\n🔄 使用串行模式执行")
        run_serial(cases)
    
    # 分析批量结果
    analyze_batch_results()

def run_parallel(cases):
    """并行执行案例"""
    
    # 限制并行进程数以避免内存问题
    max_workers = min(multiprocessing.cpu_count(), 3)
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_case = {
            executor.submit(run_single_case, (case_name, params)): case_name
            for case_name, params in cases.items()
        }
        
        # 收集结果
        results = []
        for future in future_to_case:
            try:
                result = future.result(timeout=3600)  # 1小时超时
                results.append(result)
            except Exception as e:
                case_name = future_to_case[future]
                print(f"❌ 案例 {case_name} 超时或异常: {e}")
                results.append((case_name, False, str(e)))
    
    print_batch_summary(results)

def run_serial(cases):
    """串行执行案例"""
    
    results = []
    total_start = time.time()
    
    for i, (case_name, params) in enumerate(cases.items(), 1):
        print(f"\n📍 进度: {i}/{len(cases)} - 案例: {case_name}")
        
        case_start = time.time()
        result = run_single_case((case_name, params))
        case_time = time.time() - case_start
        
        results.append(result)
        print(f"⏱️  案例耗时: {case_time:.1f} 秒")
    
    total_time = time.time() - total_start
    print(f"\n⏱️  总耗时: {total_time:.1f} 秒")
    
    print_batch_summary(results)

def print_batch_summary(results):
    """打印批量运行总结"""
    
    print(f"\n📊 批量分析总结")
    print("=" * 40)
    
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    print(f"✅ 成功: {len(successful)} 个")
    print(f"❌ 失败: {len(failed)} 个")
    print(f"📈 成功率: {len(successful)/len(results)*100:.1f}%")
    
    if successful:
        print(f"\n✅ 成功案例:")
        for case_name, _, _ in successful:
            print(f"   - {case_name}")
    
    if failed:
        print(f"\n❌ 失败案例:")
        for case_name, _, error in failed:
            print(f"   - {case_name}: {error}")

def analyze_batch_results():
    """分析批量结果"""
    
    print(f"\n📈 批量结果分析")
    print("-" * 30)
    
    batch_dir = Path("./batch_results")
    if not batch_dir.exists():
        print("❌ 批量结果目录不存在")
        return
    
    # 查找所有NPZ文件
    npz_files = list(batch_dir.glob("**/*.npz"))
    
    if not npz_files:
        print("❌ 未找到NPZ结果文件")
        return
    
    print(f"📁 找到 {len(npz_files)} 个结果文件")
    
    # 统计分析
    total_points = 0
    field_ranges = []
    
    for npz_file in npz_files:
        try:
            data = np.load(npz_file, allow_pickle=True)
            coordinates = data['coordinates']
            E_mag = data['E_mag']
            
            total_points += len(coordinates)
            field_ranges.append((E_mag.min(), E_mag.max(), E_mag.mean()))
            
            print(f"   📄 {npz_file.name}: {len(coordinates):,} 点")
            
        except Exception as e:
            print(f"   ❌ {npz_file.name}: 读取失败 - {e}")
    
    print(f"\n📊 汇总统计:")
    print(f"   🗂️  总数据点: {total_points:,}")
    print(f"   📈 电场强度范围:")
    
    if field_ranges:
        all_mins = [r[0] for r in field_ranges]
        all_maxs = [r[1] for r in field_ranges]
        all_means = [r[2] for r in field_ranges]
        
        print(f"      最小值: {min(all_mins):.2e} V/m")
        print(f"      最大值: {max(all_maxs):.2e} V/m")
        print(f"      平均值: {np.mean(all_means):.2e} V/m")
    
    print(f"\n💡 数据用途建议:")
    print(f"   🤖 AI训练: 可用于电磁场预测模型")
    print(f"   📊 统计分析: 不同工况下的场分布特征")
    print(f"   🔍 异常检测: 基于场分布模式的故障识别")

if __name__ == "__main__":
    print("⚠️  批量分析需要较长时间和大量计算资源")
    
    response = input("是否继续? (y/N): ")
    if response.lower() in ['y', 'yes']:
        main()
    else:
        print("已取消批量分析")
