# 技术文档

## 🔬 算法原理

### 电磁场控制方程

求解器基于频域Maxwell方程的标量电位形式：

```
∇ · (ε∇φ) + jωσφ = ρ
```

其中：
- φ: 标量电位（复数）
- ε: 介电常数
- σ: 电导率
- ω: 角频率 (2π × 50Hz)
- ρ: 电荷密度

### 有限元离散化

#### 1. 实部-虚部分离

将复数电位分解为实部和虚部：
φ = φ_real + j·φ_imag

得到耦合的实数方程组：
```
∇ · (ε∇φ_real) - ωσφ_imag = ρ_real
∇ · (ε∇φ_imag) + ωσφ_real = ρ_imag
```

#### 2. 弱形式

对于实部：
```
∫_Ω ε∇φ_real·∇v dΩ - ω∫_Ω σφ_imag·v dΩ = ∫_Ω ρ_real·v dΩ
```

对于虚部：
```
∫_Ω ε∇φ_imag·∇v dΩ + ω∫_Ω σφ_real·v dΩ = ∫_Ω ρ_imag·v dΩ
```

#### 3. 二阶连续Galerkin元素

使用CG2（二阶连续Galerkin）有限元：
- 提供二阶精度
- 适合电磁场的光滑性要求
- 在导体边界处保持连续性

## 🔧 数值稳定性技术

### 1. 两阶段求解策略

#### 第一阶段：简化预热
```
simplified_sigma = original_sigma * 0.1
# 求解简化问题获得初值
```

#### 第二阶段：完整求解
```
# 使用第一阶段结果作为初值
# 求解完整的高对比度问题
```

**优势**：
- 提高高对比度材料的收敛性
- 减少迭代次数
- 避免初值敏感性问题

### 2. 材料属性缩放

```
# 介电常数放大
scaled_epsilon = epsilon * 1e8

# 电导率缩小
scaled_sigma = sigma * 1e-5

# 频率缩小
scaled_omega = omega * 1e-2
```

**目的**：
- 改善系数矩阵条件数
- 避免极端数值范围
- 提高直接求解器性能

### 3. 平滑边界过渡

```
def smooth_transition(x, center, width):
    return 0.5 + 0.5 * tanh((width - abs(x - center))/width*8)
```

**应用**：
- 消除导体-绝缘体界面的数值震荡
- 提供C¹连续的材料分布
- 避免人工不连续性

## 🎯 边界条件处理

### 1. Dirichlet边界条件

在导体表面施加固定电位：
```
φ|_Γ_conductor = V_specified
```

**实现**：
```
# A相导体: 120kV ∠0°
V_PhaseA = 120e3 * exp(j * 0°)
bc_real = DirichletBC(V_real, V_PhaseA.real, boundary_id)
bc_imag = DirichletBC(V_imag, V_PhaseA.imag, boundary_id)
```

### 2. Robin边界条件

在远场边界使用Robin条件：
```
α·φ + β·(∇φ·n) = 0
```

**物理意义**：
- 模拟无限远处的衰减
- 避免人工反射
- 适合开放域问题

**参数选择**：
- α = 1.0：电位衰减权重
- β = 0.5：梯度衰减权重（可调）

## 📊 空间材料识别

### 基于坐标的区域划分

```
# 塔架区域识别
tower_region = conditional(
    smooth_transition(abs(x - tower_x_center), tower_width/2, transition_width) *
    smooth_transition(abs(x - tower_y_center), tower_width/2, transition_width) > 0.5,
    1.0, 0.0
)

# 导线区域识别  
wire_region = conditional(
    smooth_transition(sqrt((x - wire_x)**2 + (x - wire_y)**2), 
                      wire_radius, transition_width) > 0.5,
    1.0, 0.0
)
```

**优势**：
- 无需复杂的CAD几何导入
- 支持点云数据直接处理
- 可调的过渡区宽度

### 材料属性分配

| 材料 | 电导率 (S/m) | 相对介电常数 |
|------|-------------|-------------|
| 铝导线 | 35,000 | 1.0 |
| 钢塔架 | 5,800 | 1.0 |
| 陶瓷绝缘子 | 1×10⁻¹² | 7.5 |
| 空气 | 0 | 1.0006 |

## ⚙️ 求解器配置

### 直接求解器（推荐）

```
solver_parameters = {
    'ksp_type': 'preonly',
    'pc_type': 'lu',
    'pc_factor_mat_solver_type': 'mumps',
    'mat_mumps_icntl_24': 1,      # 提高稳定性
    'mat_mumps_icntl_14': 300,    # 增加工作内存
    'ksp_rtol': 1e-6
}
```

**适用场景**：
- 高对比度材料问题
- 中等规模网格（= x_min) & 
            (coordinates[:, 0] = y_min) & 
            (coordinates[:, 1] <= y_max))
```

#### 空气区域过滤
```
air_mask = (sigma < 1e-8)  # 识别低电导率区域
```

## 🔍 验证方法

### 1. 物理一致性检查

- **导体内部低场强**：导体内部电场应接近零
- **边界连续性**：电位在界面连续
- **远场衰减**：电场在远处按1/r²衰减

### 2. 数值收敛性

- **网格收敛**：细化网格验证解的收敛性
- **迭代收敛**：监控求解器残差下降
- **能量守恒**：检查功率平衡

### 3. 对比验证

- **解析解对比**：简单几何的解析解验证
- **商业软件对比**：复杂几何的基准对比
- **实验数据对比**：测量数据的定量验证

## 📊 性能优化

### 内存管理

```
# 使用合适的函数空间阶数
V_real = FunctionSpace(mesh, "CG", 2)  # 二阶精度

# 分块处理大型数据
for block in data_blocks:
    process_block(block)
```

### 并行计算

```
# Firedrake自动并行
# 使用MPI运行：
# mpirun -n 4 python tower_em_solver.py
```

### 数据压缩

```
# NPZ格式自动压缩
np.savez_compressed(filename, **data)
```

## 🔬 扩展方向

### 1. 非线性材料

- 磁滞回线建模
- 饱和效应处理
- 温度依赖性

### 2. 时域分析

- 瞬态响应分析
- 雷电冲击模拟
- 开关暂态计算

### 3. 多物理场耦合

- 电-热耦合
- 电-力耦合
- 流体-电磁耦合

### 4. 自适应网格

- 基于误差指示器的网格细化
- 各向异性网格适应
- 动态负载平衡

---

## 📚 参考文献

1. **有限元方法**：
   - Zienkiewicz, O.C. & Taylor, R.L. "The Finite Element Method"

2. **计算电磁学**：
   - Jin, J. "The Finite Element Method in Electromagnetics"

3. **Firedrake文档**：
   - https://firedrakeproject.org/

4. **电力系统电磁分析**：
   - IEEE Standards for electromagnetic field computation
```