#!/usr/bin/env python3
"""
网格生成辅助工具

用于生成简化的输电塔网格，便于测试和验证。
"""

import numpy as np
import argparse
from pathlib import Path

def generate_simple_tower_geo(output_file="simple_tower.geo", 
                             tower_height=50.0, 
                             tower_width=10.0,
                             wire_height=45.0,
                             domain_size=100.0):
    """生成简化输电塔的Gmsh几何文件"""
    
    print(f"📐 生成简化输电塔几何文件")
    print(f"   塔高: {tower_height} m")
    print(f"   塔宽: {tower_width} m") 
    print(f"   导线高度: {wire_height} m")
    print(f"   计算域: {domain_size} m")
    
    # Gmsh几何代码
    geo_content = f"""
// 简化输电塔几何 - 自动生成
// 参数设置
tower_height = {tower_height};
tower_width = {tower_width};
wire_height = {wire_height};
domain_size = {domain_size};
wire_radius = 0.1;

// 特征尺寸
lc_fine = 0.5;    // 导体附近
lc_medium = 2.0;  // 塔体附近
lc_coarse = 5.0;  // 远场

// 创建计算域 (Box)
Point(1) = {{-domain_size/2, -domain_size/2, -domain_size/4, lc_coarse}};
Point(2) = {{domain_size/2, -domain_size/2, -domain_size/4, lc_coarse}};
Point(3) = {{domain_size/2, domain_size/2, -domain_size/4, lc_coarse}};
Point(4) = {{-domain_size/2, domain_size/2, -domain_size/4, lc_coarse}};
Point(5) = {{-domain_size/2, -domain_size/2, domain_size, lc_coarse}};
Point(6) = {{domain_size/2, -domain_size/2, domain_size, lc_coarse}};
Point(7) = {{domain_size/2, domain_size/2, domain_size, lc_coarse}};
Point(8) = {{-domain_size/2, domain_size/2, domain_size, lc_coarse}};

// Box边界
Line(1) = {{1, 2}};
Line(2) = {{2, 3}};
Line(3) = {{3, 4}};
Line(4) = {{4, 1}};
Line(5) = {{5, 6}};
Line(6) = {{6, 7}};
Line(7) = {{7, 8}};
Line(8) = {{8, 5}};
Line(9) = {{1, 5}};
Line(10) = {{2, 6}};
Line(11) = {{3, 7}};
Line(12) = {{4, 8}};

// 塔腿点
Point(100) = {{-tower_width/2, -tower_width/2, 0, lc_medium}};
Point(101) = {{tower_width/2, -tower_width/2, 0, lc_medium}};
Point(102) = {{tower_width/2, tower_width/2, 0, lc_medium}};
Point(103) = {{-tower_width/2, tower_width/2, 0, lc_medium}};

// 塔顶点
Point(104) = {{0, 0, tower_height, lc_medium}};

// 塔身边
Line(100) = {{100, 101}};
Line(101) = {{101, 102}};
Line(102) = {{102, 103}};
Line(103) = {{103, 100}};
Line(104) = {{100, 104}};
Line(105) = {{101, 104}};
Line(106) = {{102, 104}};
Line(107) = {{103, 104}};

// 导线点
Point(200) = {{-tower_width, 0, wire_height, lc_fine}};  // A相
Point(201) = {{0, 0, wire_height, lc_fine}};             // B相
Point(202) = {{tower_width, 0, wire_height, lc_fine}};   // C相

// 绝缘子连接点
Point(210) = {{-tower_width/3, 0, tower_height*0.9, lc_medium}};
Point(211) = {{0, 0, tower_height*0.9, lc_medium}};
Point(212) = {{tower_width/3, 0, tower_height*0.9, lc_medium}};

// 绝缘子
Line(200) = {{210, 200}};
Line(201) = {{211, 201}};
Line(202) = {{212, 202}};

// 塔身到绝缘子
Line(210) = {{104, 210}};
Line(211) = {{104, 211}};
Line(212) = {{104, 212}};

// 物理区域标记
Physical Point("PhaseA") = {{200}};
Physical Point("PhaseB") = {{201}};
Physical Point("PhaseC") = {{202}};

Physical Line("Tower_Edge") = {{104, 105, 106, 107}};
Physical Line("Insulator_A") = {{200}};
Physical Line("Insulator_B") = {{201}};
Physical Line("Insulator_C") = {{202}};

// 边界面
Line Loop(1) = {{1, 2, 3, 4}};
Plane Surface(1) = {{1}};
Line Loop(2) = {{5, 6, 7, 8}};
Plane Surface(2) = {{2}};
Line Loop(3) = {{1, 10, -5, -9}};
Plane Surface(3) = {{3}};
Line Loop(4) = {{2, 11, -6, -10}};
Plane Surface(4) = {{4}};
Line Loop(5) = {{3, 12, -7, -11}};
Plane Surface(5) = {{5}};
Line Loop(6) = {{4, 9, -8, -12}};
Plane Surface(6) = {{6}};

// 体积
Surface Loop(1) = {{1, 2, 3, 4, 5, 6}};
Volume(1) = {{1}};

// 物理区域
Physical Surface("Box_Boundary") = {{1, 2, 3, 4, 5, 6}};
Physical Volume("Air") = {{1}};

// 网格设置
Mesh.CharacteristicLengthMin = 0.1;
Mesh.CharacteristicLengthMax = 10.0;
Mesh.ElementOrder = 2;
Mesh.Algorithm = 6;  // Frontal-Delaunay for 2D
Mesh.Algorithm3D = 1; // Delaunay for 3D
"""
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(geo_content)
    
    print(f"✅ 几何文件已生成: {output_file}")
    print(f"💡 使用方法:")
    print(f"   gmsh {output_file} -3 -format msh -o simple_tower.msh")

def generate_test_data():
    """生成测试用的虚拟电磁场数据"""
    
    print(f"🧪 生成测试数据...")
    
    # 创建测试网格点
    x = np.linspace(-50, 50, 50)
    y = np.linspace(-50, 50, 50) 
    z = np.linspace(0, 80, 40)
    
    X, Y, Z = np.meshgrid(x, y, z)
    coordinates = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    
    # 模拟电场分布
    # 在导体附近场强较高
    r_tower = np.sqrt(X**2 + Y**2)
    r_wire_a = np.sqrt((X + 10)**2 + Y**2 + (Z - 45)**2)
    r_wire_b = np.sqrt(X**2 + Y**2 + (Z - 45)**2)
    r_wire_c = np.sqrt((X - 10)**2 + Y**2 + (Z - 45)**2)
    
    # 基础场 + 导体增强
    E_base = 1e3 * np.exp(-r_tower/20)
    E_wire = 1e6 * (np.exp(-r_wire_a/2) + np.exp(-r_wire_b/2) + np.exp(-r_wire_c/2))
    E_mag = (E_base + E_wire).ravel()
    
    # 添加噪声
    E_mag += np.random.normal(0, E_mag.max()*0.01, E_mag.shape)
    E_mag = np.abs(E_mag)  # 确保为正值
    
    # 创建其他场量
    phi_real = np.random.normal(0, 1e5, len(coordinates))
    phi_imag = np.random.normal(0, 1e3, len(coordinates))
    
    # 创建向量场
    E_real = np.random.normal(0, E_mag[:, None]/3, (len(coordinates), 3))
    E_imag = np.random.normal(0, E_mag[:, None]/10, (len(coordinates), 3))
    
    # 材料属性
    epsilon = np.full(len(coordinates), 8.854e-12)
    sigma = np.full(len(coordinates), 0.0)
    
    # 保存测试数据
    output_file = "test_em_data.npz"
    np.savez(output_file,
             coordinates=coordinates,
             phi_real=phi_real,
             phi_imag=phi_imag,
             E_real=E_real,
             E_imag=E_imag,
             E_mag=E_mag,
             epsilon=epsilon,
             sigma=sigma,
             freq=50.0,
             metadata={
                 'test_data': True,
                 'generator': 'mesh_generator.py',
                 'description': 'Synthetic EM field data for testing'
             })
    
    print(f"✅ 测试数据已生成: {output_file}")
    print(f"   数据点数: {len(coordinates):,}")
    print(f"   电场范围: {E_mag.min():.2e} - {E_mag.max():.2e} V/m")

def main():
    """主函数"""
    
    parser = argparse.ArgumentParser(description="网格生成辅助工具")
    parser.add_argument("--geo", action="store_true", help="生成Gmsh几何文件")
    parser.add_argument("--test-data", action="store_true", help="生成测试数据")
    parser.add_argument("--output", default="simple_tower.geo", help="输出文件名")
    parser.add_argument("--height", type=float, default=50.0, help="塔高 (m)")
    parser.add_argument("--width", type=float, default=10.0, help="塔宽 (m)")
    parser.add_argument("--domain", type=float, default=100.0, help="计算域尺寸 (m)")
    
    args = parser.parse_args()
    
    print("🛠️  网格生成辅助工具")
    print("=" * 30)
    
    if args.geo:
        generate_simple_tower_geo(
            output_file=args.output,
            tower_height=args.height,
            tower_width=args.width,
            domain_size=args.domain
        )
    
    if args.test_data:
        generate_test_data()
    
    if not args.geo and not args.test_data:
        print("请指定操作: --geo 或 --test-data")
        parser.print_help()

if __name__ == "__main__":
    main()
