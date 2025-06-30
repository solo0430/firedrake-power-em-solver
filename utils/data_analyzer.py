#!/usr/bin/env python3
"""
电磁场数据分析工具

用于分析tower_em_solver生成的NPZ数据文件。
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse
import sys

def load_em_data(npz_file):
    """加载电磁场数据"""
    
    try:
        data = np.load(npz_file, allow_pickle=True)
        print(f"✅ 成功加载: {npz_file}")
        return data
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return None

def analyze_field_distribution(E_mag, title="电场强度分布"):
    """分析电场强度分布"""
    
    print(f"\n📊 {title}")
    print("=" * 40)
    
    # 基本统计
    print(f"数据点数: {len(E_mag):,}")
    print(f"最小值: {E_mag.min():.2e} V/m")
    print(f"最大值: {E_mag.max():.2e} V/m")
    print(f"平均值: {E_mag.mean():.2e} V/m")
    print(f"中位数: {np.median(E_mag):.2e} V/m")
    print(f"标准差: {E_mag.std():.2e} V/m")
    
    # 数量级分布
    print(f"\n📈 数量级分布:")
    for exp in range(-10, 12):
        lower = 10**exp
        upper = 10**(exp+1)
        count = np.sum((E_mag >= lower) & (E_mag < upper))
        if count > 0:
            percentage = count / len(E_mag) * 100
            print(f"  1e{exp:2d} - 1e{exp+1:2d}: {count:8d} 点 ({percentage:5.2f}%)")
    
    # 百分位数
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    print(f"\n📊 百分位数分布:")
    for p in percentiles:
        value = np.percentile(E_mag, p)
        print(f"  {p:2d}%: {value:.2e} V/m")

def analyze_spatial_distribution(coordinates, E_mag):
    """分析空间分布特征"""
    
    print(f"\n🗺️  空间分布分析")
    print("=" * 30)
    
    # 空间范围
    x_range = [coordinates[:, 0].min(), coordinates[:, 0].max()]
    y_range = [coordinates[:, 1].min(), coordinates[:, 1].max()]
    z_range = [coordinates[:, 2].min(), coordinates[:, 2].max()]
    
    print(f"空间范围:")
    print(f"  X: [{x_range[0]:.1f}, {x_range[1]:.1f}] m (跨度: {x_range[1]-x_range[0]:.1f} m)")
    print(f"  Y: [{y_range[0]:.1f}, {y_range[1]:.1f}] m (跨度: {y_range[1]-y_range[0]:.1f} m)")
    print(f"  Z: [{z_range[0]:.1f}, {z_range[1]:.1f}] m (跨度: {z_range[1]-z_range[0]:.1f} m)")
    
    # 高场强区域分析
    high_field_threshold = np.percentile(E_mag, 95)
    high_field_mask = E_mag > high_field_threshold
    high_field_coords = coordinates[high_field_mask]
    
    if len(high_field_coords) > 0:
        print(f"\n⚡ 高场强区域分析 (>{high_field_threshold:.2e} V/m):")
        print(f"  点数: {len(high_field_coords)} ({len(high_field_coords)/len(coordinates)*100:.1f}%)")
        print(f"  X范围: [{high_field_coords[:, 0].min():.1f}, {high_field_coords[:, 0].max():.1f}] m")
        print(f"  Y范围: [{high_field_coords[:, 1].min():.1f}, {high_field_coords[:, 1].max():.1f}] m")
        print(f"  Z范围: [{high_field_coords[:, 2].min():.1f}, {high_field_coords[:, 2].max():.1f}] m")

def plot_field_analysis(coordinates, E_mag, output_dir="./analysis_plots"):
    """生成分析图表"""
    
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    
    print(f"\n📈 生成分析图表...")
    
    # 创建输出目录
    Path(output_dir).mkdir(exist_ok=True)
    
    # 1. 电场强度直方图
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    log_E = np.log10(E_mag[E_mag > 0])
    plt.hist(log_E, bins=50, alpha=0.7, edgecolor='black')
    plt.xlabel('log₁₀(电场强度) [V/m]')
    plt.ylabel('频次')
    plt.title('电场强度分布 (对数坐标)')
    plt.grid(True, alpha=0.3)
    
    # 2. 空间分布（XY平面）
    plt.subplot(2, 2, 2)
    # 使用对数色标显示场强
    log_E_all = np.log10(E_mag + 1e-12)  # 避免log(0)
    scatter = plt.scatter(coordinates[:, 0], coordinates[:, 1], 
                         c=log_E_all, s=0.1, alpha=0.6, cmap='viridis')
    plt.colorbar(scatter, label='log₁₀(电场强度) [V/m]')
    plt.xlabel('X [m]')
    plt.ylabel('Y [m]')
    plt.title('XY平面电场分布')
    plt.axis('equal')
    
    # 3. 高度分布
    plt.subplot(2, 2, 3)
    z_coords = coordinates[:, 2]
    plt.scatter(z_coords, E_mag, s=0.1, alpha=0.6)
    plt.xlabel('Z (高度) [m]')
    plt.ylabel('电场强度 [V/m]')
    plt.title('电场强度vs高度')
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    
    # 4. 累积分布函数
    plt.subplot(2, 2, 4)
    sorted_E = np.sort(E_mag)
    cum_prob = np.arange(1, len(sorted_E) + 1) / len(sorted_E)
    plt.semilogx(sorted_E, cum_prob)
    plt.xlabel('电场强度 [V/m]')
    plt.ylabel('累积概率')
    plt.title('电场强度累积分布')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_file = Path(output_dir) / "field_analysis.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"📊 图表已保存: {plot_file}")
    
    # 3D散点图（采样显示）
    if len(coordinates) > 10000:
        # 采样显示，避免图形过于复杂
        sample_size = 10000
        indices = np.random.choice(len(coordinates), sample_size, replace=False)
        coords_sample = coordinates[indices]
        E_sample = E_mag[indices]
    else:
        coords_sample = coordinates
        E_sample = E_mag
    
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    log_E_sample = np.log10(E_sample + 1e-12)
    scatter = ax.scatter(coords_sample[:, 0], coords_sample[:, 1], coords_sample[:, 2],
                        c=log_E_sample, s=0.5, alpha=0.6, cmap='plasma')
    
    ax.set_xlabel('X [m]')
    ax.set_ylabel('Y [m]')
    ax.set_zlabel('Z [m]')
    ax.set_title(f'3D电场分布 (采样 {len(coords_sample):,} 点)')
    
    cbar = plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=20)
    cbar.set_label('log₁₀(电场强度) [V/m]')
    
    plot_3d_file = Path(output_dir) / "field_3d_distribution.png"
    plt.savefig(plot_3d_file, dpi=300, bbox_inches='tight')
    print(f"📊 3D图表已保存: {plot_3d_file}")
    
    plt.show()

def compare_cases(npz_files):
    """比较多个案例"""
    
    print(f"\n📊 多案例对比分析")
    print("=" * 30)
    
    cases_data = []
    case_names = []
    
    for npz_file in npz_files:
        data = load_em_data(npz_file)
        if data is not None:
            cases_data.append(data)
            case_names.append(Path(npz_file).stem)
    
    if len(cases_data) < 2:
        print("❌ 需要至少2个有效案例进行对比")
        return
    
    print(f"📋 对比 {len(cases_data)} 个案例:")
    
    # 创建对比表格
    print(f"\n{'案例名称':<20} {'数据点数':<10} {'最小值':<12} {'最大值':<12} {'平均值':<12}")
    print("-" * 70)
    
    for i, (case_name, data) in enumerate(zip(case_names, cases_data)):
        E_mag = data['E_mag']
        print(f"{case_name:<20} {len(E_mag):<10,} {E_mag.min():<12.2e} {E_mag.max():<12.2e} {E_mag.mean():<12.2e}")
    
    # 生成对比图表
    plt.figure(figsize=(15, 10))
    
    # 1. 电场强度分布对比
    plt.subplot(2, 2, 1)
    for case_name, data in zip(case_names, cases_data):
        E_mag = data['E_mag']
        log_E = np.log10(E_mag[E_mag > 0])
        plt.hist(log_E, bins=50, alpha=0.5, label=case_name, density=True)
    plt.xlabel('log₁₀(电场强度) [V/m]')
    plt.ylabel('概率密度')
    plt.title('电场强度分布对比')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 2. 累积分布对比
    plt.subplot(2, 2, 2)
    for case_name, data in zip(case_names, cases_data):
        E_mag = data['E_mag']
        sorted_E = np.sort(E_mag)
        cum_prob = np.arange(1, len(sorted_E) + 1) / len(sorted_E)
        plt.semilogx(sorted_E, cum_prob, label=case_name, linewidth=2)
    plt.xlabel('电场强度 [V/m]')
    plt.ylabel('累积概率')
    plt.title('累积分布对比')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 3. 统计量对比
    plt.subplot(2, 2, 3)
    stats = ['最小值', '平均值', '中位数', '95%分位', '最大值']
    x_pos = np.arange(len(stats))
    
    for i, (case_name, data) in enumerate(zip(case_names, cases_data)):
        E_mag = data['E_mag']
        values = [
            E_mag.min(),
            E_mag.mean(),
            np.median(E_mag),
            np.percentile(E_mag, 95),
            E_mag.max()
        ]
        plt.semilogy(x_pos + i*0.1, values, 'o-', label=case_name, markersize=8)
    
    plt.xticks(x_pos, stats)
    plt.ylabel('电场强度 [V/m]')
    plt.title('统计量对比')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 4. 数据点数对比
    plt.subplot(2, 2, 4)
    point_counts = [len(data['E_mag']) for data in cases_data]
    bars = plt.bar(case_names, point_counts)
    plt.ylabel('数据点数')
    plt.title('数据点数对比')
    plt.xticks(rotation=45)
    
    # 在柱子上显示数值
    for bar, count in zip(bars, point_counts):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{count:,}', ha='center', va='bottom')
    
    plt.tight_layout()
    
    compare_file = "./comparison_analysis.png"
    plt.savefig(compare_file, dpi=300, bbox_inches='tight')
    print(f"📊 对比图表已保存: {compare_file}")
    
    plt.show()

def main():
    """主函数"""
    
    parser = argparse.ArgumentParser(description="电磁场数据分析工具")
    parser.add_argument("files", nargs="+", help="NPZ数据文件路径")
    parser.add_argument("--plot", action="store_true", help="生成分析图表")
    parser.add_argument("--compare", action="store_true", help="多案例对比")
    parser.add_argument("--output", default="./analysis_plots", help="图表输出目录")
    
    args = parser.parse_args()
    
    print("📊 电磁场数据分析工具")
    print("=" * 40)
    
    # 验证文件存在
    valid_files = []
    for file_path in args.files:
        if Path(file_path).exists():
            valid_files.append(file_path)
        else:
            print(f"❌ 文件不存在: {file_path}")
    
    if not valid_files:
        print("❌ 没有有效的输入文件")
        return
    
    if len(valid_files) == 1 and not args.compare:
        # 单文件分析
        data = load_em_data(valid_files[0])
        if data is None:
            return
        
        # 提取数据
        coordinates = data['coordinates']
        E_mag = data['E_mag']
        
        # 分析
        analyze_field_distribution(E_mag)
        analyze_spatial_distribution(coordinates, E_mag)
        
        # 打印元数据
        if 'metadata' in data:
            metadata = data['metadata'].item()
            print(f"\n📋 元数据信息:")
            for key, value in metadata.items():
                if key != 'box_filter_info':
                    print(f"  {key}: {value}")
        
        # 生成图表
        if args.plot:
            plot_field_analysis(coordinates, E_mag, args.output)
    
    elif len(valid_files) > 1 or args.compare:
        # 多文件对比
        compare_cases(valid_files)
    
    print(f"\n✅ 分析完成")

if __name__ == "__main__":
    main()
