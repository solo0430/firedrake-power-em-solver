# 快速开始指南

## 📋 环境要求

### 系统要求
- Linux 或 macOS (推荐 Ubuntu 20.04+)
- Python 3.8+
- 至少 8GB RAM
- 10GB 可用磁盘空间

### 必需软件
- Git
- Python 3.8+
- curl

## 🛠️ 安装步骤

### 1. 安装 Firedrake

```
# 下载安装脚本
curl -O https://raw.githubusercontent.com/firedrakeproject/firedrake/master/scripts/firedrake-install

# 运行安装（约30-60分钟）
python3 firedrake-install --disable-ssh

# 激活环境
source firedrake/bin/activate
```

**注意**: Firedrake 安装可能需要较长时间，请确保网络连接稳定。

### 2. 克隆项目

```
git clone https://github.com/solo0430/firedrake-power-em-solver.git
cd firedrake-power-em-solver
```

### 3. 安装依赖

```
# 在 Firedrake 环境中安装额外依赖
pip install -r requirements.txt
```

## 🚀 第一次运行

### 基本示例

```
# 激活 Firedrake 环境
source firedrake/bin/activate

# 运行基本示例
cd examples
python basic_220kv_tower.py
```

### 预期输出

```
🔋 开始220kV输电塔电磁场分析示例
==================================================
📁 输出目录: ./example_results
⚡ 电压等级: 220kV
🔧 求解器: Firedrake + 二阶有限元

开始输电塔电场分析 - Firedrake求解器 (仅NPZ输出版)
导入网格文件：/path/to/mesh.msh
...
✅ 仿真成功完成！
📊 结果文件: ./example_results/basic_220kv_example_*.npz
```

## 📊 分析结果

### 使用数据分析工具

```
# 分析单个结果文件
python utils/data_analyzer.py example_results/basic_220kv_example_*.npz

# 生成图表
python utils/data_analyzer.py example_results/basic_220kv_example_*.npz --plot
```

### 手动加载数据

```
import numpy as np

# 加载结果
data = np.load("example_results/basic_220kv_example_20250320_021712.npz")

# 查看数据结构
print("可用数据字段:", data.files)
print("数据点数量:", len(data['coordinates']))
print("电场强度范围:", data['E_mag'].min(), "到", data['E_mag'].max(), "V/m")
```

## 🔧 自定义参数

### 修改求解参数

```
from tower_em_solver import solve_tower_electric_field

# 自定义参数运行
success = solve_tower_electric_field(
    output_dir="./my_results",
    npz_filename="custom_analysis",
    max_conductivity=50000,  # 提高电导率限制
    robin_coeff=0.8         # 调整边界条件
)
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `output_dir` | `"./results"` | 结果输出目录 |
| `npz_filename` | `"tower_electric_field"` | 输出文件名前缀 |
| `max_conductivity` | `35000` | 最大电导率限制 (S/m) |
| `robin_coeff` | `0.5` | Robin边界条件系数 |

## 📈 批量分析

### 运行多个工况

```
# 运行批量分析示例
python examples/batch_analysis.py
```

这将生成多个不同参数的分析结果，便于对比研究。

## ⚠️ 常见问题

### 1. Firedrake 安装失败

**问题**: 安装过程中出现编译错误

**解决方案**:
- 确保有足够的磁盘空间 (10GB+)
- 检查网络连接稳定性
- 尝试使用 `--disable-ssh` 参数

### 2. 网格文件未找到

**问题**: `错误：找不到网格文件`

**解决方案**:
- 检查 `tower_em_solver.py` 中的 `mesh_file` 路径
- 使用 `utils/mesh_generator.py` 生成测试网格
- 确保网格文件格式为 Gmsh .msh 格式

### 3. 内存不足

**问题**: 大型网格计算时内存溢出

**解决方案**:
- 减小网格尺寸
- 降低 `max_conductivity` 参数
- 使用更高配置的计算节点

### 4. 求解收敛失败

**问题**: 求解器报告收敛失败

**解决方案**:
- 调整 `robin_coeff` 参数 (尝试 0.1-1.0)
- 检查边界条件设置
- 验证网格质量

## 📚 下一步

1. **阅读技术文档**: [technical_notes.md](technical_notes.md)
2. **查看批量分析**: [batch_analysis.py](../examples/batch_analysis.py)
3. **使用数据分析工具**: [data_analyzer.py](../utils/data_analyzer.py)
4. **生成自定义网格**: [mesh_generator.py](../utils/mesh_generator.py)

## 💬 获取帮助

- **GitHub Issues**: 报告问题和请求功能
- **技术讨论**: GitHub Discussions
- **邮件联系**: solo0430@example.com
```