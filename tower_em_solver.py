from firedrake import *
from firedrake.output import VTKFile
import numpy as np
import os
import time

def smooth_transition(x, center, width):
    """在导体-绝缘体边界创建梯度过渡 - 增强平滑因子"""
    # 增大平滑因子从5到8，使过渡更平滑
    return 0.5 + 0.5 * tanh((width - abs(x - center))/width*8)

def solve_tower_electric_field(output_dir="/home/firedrake/test/results", npz_filename="tower_electric_field", 
                              max_conductivity=35000, robin_coeff=0.5):
    import numpy as np  # 在函数内部导入NumPy
    print("开始输电塔电场分析 - Firedrake求解器 (仅NPZ输出版)")
    start_time = time.time()

    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成带时间戳的NPZ文件名以避免覆盖
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    npz_file = f"{output_dir}/{npz_filename}_{timestamp}.npz"

    # 1. 导入网格文件
    mesh_file = "/home/firedrake/test/transmission_tower_v2.msh"
    if not os.path.exists(mesh_file):
        print(f"错误：找不到网格文件 {mesh_file}")
        return False

    print(f"导入网格文件：{mesh_file}")
    mesh = Mesh(mesh_file)

    # 2. 定义材料参数
    # 频率 = 50Hz
    freq = 50.0
    omega = 2 * np.pi * freq

    # 基本常数
    epsilon0 = 8.85418782e-12  # 真空介电常数
    mu0 = 4.0e-7 * np.pi       # 真空磁导率

    # 定义材料的介电常数（相对值）
    epsilon_r = {
        9: 1.0,      # Tower (钢材) - 注意ID为9
        2: 1.0,      # PhaseA (铝导线)
        3: 1.0,      # PhaseB (铝导线)
        4: 1.0,      # PhaseC (铝导线)
        5: 1.0,      # Phasea (铝导线)
        6: 1.0,      # Phaseb (铝导线)
        7: 1.0,      # Phasec (铝导线)
        1: 1.0006,   # Box (空气)
        8: 7.5       # Insulators (陶瓷绝缘子)
    }

    # 定义材料的电导率 (S/m) - 限制最大电导率以提高数值稳定性
    # 降低到350 S/m以获得更好的数值特性
    sigma = {
        9: min(5.8e6, max_conductivity),    # Tower (钢材)
        2: min(3.5e7, max_conductivity),    # PhaseA (铝导线)
        3: min(3.5e7, max_conductivity),    # PhaseB (铝导线)
        4: min(3.5e7, max_conductivity),    # PhaseC (铝导线)
        5: min(3.5e7, max_conductivity),    # Phasea (铝导线)
        6: min(3.5e7, max_conductivity),    # Phaseb (铝导线)
        7: min(3.5e7, max_conductivity),    # Phasec (铝导线)
        1: 0.0,                             # Box (空气，非导体)
        8: 1e-12                            # Insulators (陶瓷绝缘子，绝缘体)
    }

    print(f"使用限制电导率: 最大值={max_conductivity} S/m")

    # 3. 分别为实部和虚部建立函数空间 - 使用高阶元素
    V_real = FunctionSpace(mesh, "CG", 2)   # 升级到二阶元素
    V_imag = FunctionSpace(mesh, "CG", 2)

    # 4. 定义电位函数和测试函数
    u_real = TrialFunction(V_real)
    v_real = TestFunction(V_real)
    u_imag = TrialFunction(V_imag)
    v_imag = TestFunction(V_imag)

    # 5. 测试边界条件是否可用
    print("\n检查边界标记可用性:")
    valid_bc_ids = []
    for bc_id in range(1, 25):  # 扩大范围以确保捕获所有可能的边界ID
        try:
            test_func = Function(V_real)
            test_bc = DirichletBC(V_real, Constant(1.0), bc_id)
            test_bc.apply(test_func)
            dof_count = len(test_bc.nodes)
            if dof_count > 0:
                valid_bc_ids.append(bc_id)
                print(f"  边界ID {bc_id}: 有效 (找到 {dof_count} 个自由度)")
            else:
                print(f"  边界ID {bc_id}: 无效 (未找到自由度)")
        except Exception as e:
            print(f"  边界ID {bc_id}: 测试失败 - {str(e)}")

    # 定义相位角（弧度）
    phi_A = 0.0
    phi_B = 2.0*np.pi/3.0
    phi_C = 4.0*np.pi/3.0
    phi_a = 0.0
    phi_b = 2.0*np.pi/3.0
    phi_c = 4.0*np.pi/3.0

    # 定义边界条件值（复数形式，考虑相位）
    V_Tower = 0.0
    V_PhaseA = 120e3 * np.exp(1j * phi_A)
    V_PhaseB = 120e3 * np.exp(1j * phi_B)
    V_PhaseC = 120e3 * np.exp(1j * phi_C)
    V_Phasea = 120e3 * np.exp(1j * phi_a)
    V_Phaseb = 120e3 * np.exp(1j * phi_b)
    V_Phasec = 120e3 * np.exp(1j * phi_c)

    # 创建边界条件 - 分别为实部和虚部
    bcs_real = []
    bcs_imag = []

    # 根据实际测试结果映射边界条件 (ID 10-17是有效的)
    valid_boundaries = {
        "Tower": 17,   # 注意：这些ID根据测试结果调整
        "PhaseA": 11,
        "PhaseB": 12,
        "PhaseC": 13,
        "Phasea": 14,
        "Phaseb": 15,
        "Phasec": 16,
        "Box": 10
    }
    
    print("\n使用的边界条件映射:")
    for key, value in valid_boundaries.items():
        print(f"  {key}: {value}")

    # Tower_Surface
    if valid_boundaries["Tower"]:
        bcs_real.append(DirichletBC(V_real, Constant(V_Tower), valid_boundaries["Tower"]))
        bcs_imag.append(DirichletBC(V_imag, Constant(0.0), valid_boundaries["Tower"]))

    # PhaseA_Surface
    if valid_boundaries["PhaseA"]:
        bcs_real.append(DirichletBC(V_real, Constant(V_PhaseA.real), valid_boundaries["PhaseA"]))
        bcs_imag.append(DirichletBC(V_imag, Constant(V_PhaseA.imag), valid_boundaries["PhaseA"]))

    # PhaseB_Surface
    if valid_boundaries["PhaseB"]:
        bcs_real.append(DirichletBC(V_real, Constant(V_PhaseB.real), valid_boundaries["PhaseB"]))
        bcs_imag.append(DirichletBC(V_imag, Constant(V_PhaseB.imag), valid_boundaries["PhaseB"]))

    # PhaseC_Surface
    if valid_boundaries["PhaseC"]:
        bcs_real.append(DirichletBC(V_real, Constant(V_PhaseC.real), valid_boundaries["PhaseC"]))
        bcs_imag.append(DirichletBC(V_imag, Constant(V_PhaseC.imag), valid_boundaries["PhaseC"]))

    # Phasea_Surface
    if valid_boundaries["Phasea"]:
        bcs_real.append(DirichletBC(V_real, Constant(V_Phasea.real), valid_boundaries["Phasea"]))
        bcs_imag.append(DirichletBC(V_imag, Constant(V_Phasea.imag), valid_boundaries["Phasea"]))

    # Phaseb_Surface
    if valid_boundaries["Phaseb"]:
        bcs_real.append(DirichletBC(V_real, Constant(V_Phaseb.real), valid_boundaries["Phaseb"]))
        bcs_imag.append(DirichletBC(V_imag, Constant(V_Phaseb.imag), valid_boundaries["Phaseb"]))

    # Phasec_Surface
    if valid_boundaries["Phasec"]:
        bcs_real.append(DirichletBC(V_real, Constant(V_Phasec.real), valid_boundaries["Phasec"]))
        bcs_imag.append(DirichletBC(V_imag, Constant(V_Phasec.imag), valid_boundaries["Phasec"]))

    # Box_Surface - 使用Robin边界条件而非Dirichlet
    print(f"已设置 {len(bcs_real)} 个Dirichlet边界条件 (Box边界将使用Robin条件)")

    # 6. 材料属性设置 - 先尝试使用DMPlex标记
    print("\n设置材料属性...")

    # 创建离散Galerkin空间来存储材料属性 - 提高到DG1
    DG0 = FunctionSpace(mesh, "DG", 1)  # 提高材料属性表示的阶数
    epsilon_fn = Function(DG0, name="epsilon")
    sigma_fn = Function(DG0, name="sigma")
    
    # 首先尝试DMPlex方法
    dm = mesh.topology_dm
    use_spatial_method = True

    # 计算网格边界框 - 确保无论使用哪种方法，都有定义坐标中心
    mesh_coords = mesh.coordinates.dat.data
    x_min, y_min, z_min = np.min(mesh_coords, axis=0)
    x_max, y_max, z_max = np.max(mesh_coords, axis=0)
    
    # 计算中心点和尺寸 - 在所有方法前定义，防止未定义错误
    x_center = (x_max + x_min) / 2
    y_center = (y_max + y_min) / 2
    z_center = (z_max + z_min) / 2
    
    # 估计尺寸
    x_size = (x_max - x_min)
    y_size = (y_max - y_min)
    z_size = (z_max - z_min)
    
    print(f"网格边界: X[{x_min:.2f}, {x_max:.2f}], Y[{y_min:.2f}, {y_max:.2f}], Z[{z_min:.2f}, {z_max:.2f}]")
    print(f"中心点: ({x_center:.2f}, {y_center:.2f}, {z_center:.2f})")

    # 获取DMPlex和单元编号
    try:
        cell_numbering = mesh._cell_numbering

        # 调试信息 - 检查所有可能的标签
        print("可用的DMPlex标签:")
        for i in range(dm.getNumLabels()):
            label_name = dm.getLabelName(i)
            print(f"  - {label_name}")
            if "Cell" in label_name:
                strata = dm.getLabelIdIS(label_name).getIndices()
                print(f"    值: {strata}")
                for s in strata:
                    is_size = dm.getStratumSize(label_name, s)
                    print(f"    标签 '{label_name}' 值 {s} 包含 {is_size} 个实体")

        # 检查"Cell Sets"标签
        if dm.hasLabel("Cell Sets"):
            use_spatial_method = False
            print("找到'Cell Sets'标签，尝试使用它识别材料")

            # 设置默认值（空气）
            epsilon_fn.assign(Constant(epsilon0 * epsilon_r[1]))  # 1是Box (空气)
            sigma_fn.assign(Constant(sigma[1]))

            # 获取所有可能的标签值
            strata = dm.getLabelIdIS("Cell Sets").getIndices()
            print(f"'Cell Sets'标签的值: {strata}")

            # 为每个区域设置材料属性
            for s in strata:
                label_is = dm.getStratumIS("Cell Sets", s)
                if label_is:
                    indices = label_is.getIndices()
                    cell_indices = []
                    for i in indices:
                        try:
                            cell_idx = cell_numbering.getOffset(i)
                            if cell_idx >= 0:
                                cell_indices.append(cell_idx)
                        except:
                            pass

                    # 检查这个标签对应哪个材料
                    print(f"标签值 {s} 有 {len(cell_indices)} 个单元")
                    material_id = None

                    # 匹配材料ID
                    if s in epsilon_r:
                        material_id = s

                    if material_id is not None:
                        for cell in cell_indices:
                            try:
                                epsilon_fn.dat.data[cell] = epsilon0 * epsilon_r[material_id]
                                sigma_fn.dat.data[cell] = sigma[material_id]
                            except:
                                pass
                        print(f"  设置为材料 {material_id} (epsilon={epsilon_r[material_id]}, sigma={sigma[material_id]})")
    except Exception as e:
        print(f"DMPlex方法失败: {e}")
        use_spatial_method = True

    # 如果DMPlex方法失败，使用空间坐标识别
    if use_spatial_method:
        print("使用空间坐标方法识别材料区域...")

        # 计算网格边界框以辅助定位 - 这里重复是为了保持代码逻辑清晰
        print(f"网格边界: X[{x_min:.2f}, {x_max:.2f}], Y[{y_min:.2f}, {y_max:.2f}], Z[{z_min:.2f}, {z_max:.2f}]")
        
        # 获取坐标
        x = SpatialCoordinate(mesh)

        # 定义各区域 - 使用增强的平滑过渡
        # 塔架区域 - 中心位置 (使用整个网格中心区域)
        tower_x_center = x_center
        tower_y_center = y_center
        tower_width = min(x_size, y_size) * 0.6  # 使用60%的尺寸作为塔架宽度
        
        tower_z_min = z_min
        tower_z_max = z_center + z_size * 0.3  # 塔身高度为总高度的80%
        
        # 添加增强平滑过渡 - 导体界面处理
        transition_width = min(x_size, y_size) * 0.08  # 增大过渡区宽度为总尺寸的8%
        
        # 使用平滑过渡函数替代硬边界
        tower_region = conditional(
            smooth_transition(abs(x[0] - tower_x_center), tower_width/2, transition_width) *
            smooth_transition(abs(x[1] - tower_y_center), tower_width/2, transition_width) *
            conditional(between(x[2], (tower_z_min, tower_z_max)), 1.0, 0.0) > 0.5,
            1.0, 0.0
        )

        # 上部导线区域 - 使用实际高度分布
        phase_z_level = z_max - z_size * 0.2  # 上部导线高度
        wire_radius = min(x_size, y_size) * 0.03  # 导线半径
        
        # 使用增强平滑过渡的导线定义
        phaseA_x = x_center - x_size/6
        phaseA_region = conditional(
            smooth_transition(x[2], phase_z_level, transition_width) *
            smooth_transition(sqrt((x[0] - phaseA_x)**2 + (x[1] - y_center)**2), wire_radius, transition_width) > 0.5,
            1.0, 0.0
        )

        phaseB_x = x_center
        phaseB_region = conditional(
            smooth_transition(x[2], phase_z_level, transition_width) *
            smooth_transition(sqrt((x[0] - phaseB_x)**2 + (x[1] - y_center)**2), wire_radius, transition_width) > 0.5,
            1.0, 0.0
        )

        phaseC_x = x_center + x_size/6
        phaseC_region = conditional(
            smooth_transition(x[2], phase_z_level, transition_width) *
            smooth_transition(sqrt((x[0] - phaseC_x)**2 + (x[1] - y_center)**2), wire_radius, transition_width) > 0.5,
            1.0, 0.0
        )
        
        # 下部导线区域
        lower_phase_z_level = z_center
        
        phasea_x = x_center - x_size/6
        phasea_region = conditional(
            smooth_transition(x[2], lower_phase_z_level, transition_width) *
            smooth_transition(sqrt((x[0] - phasea_x)**2 + (x[1] - y_center)**2), wire_radius, transition_width) > 0.5,
            1.0, 0.0
        )

        phaseb_x = x_center
        phaseb_region = conditional(
            smooth_transition(x[2], lower_phase_z_level, transition_width) *
            smooth_transition(sqrt((x[0] - phaseb_x)**2 + (x[1] - y_center)**2), wire_radius, transition_width) > 0.5,
            1.0, 0.0
        )

        phasec_x = x_center + x_size/6
        phasec_region = conditional(
            smooth_transition(x[2], lower_phase_z_level, transition_width) *
            smooth_transition(sqrt((x[0] - phasec_x)**2 + (x[1] - y_center)**2), wire_radius, transition_width) > 0.5,
            1.0, 0.0
        )
        
        # 绝缘子区域 - 放置在导线下方
        insulator_height = (phase_z_level - tower_z_max) * 0.3
        insulator_width = min(x_size, y_size) * 0.05  # 稍微增大绝缘子宽度
        
        # 平滑过渡的绝缘子定义
        insulator_region = conditional(
            smooth_transition(x[2], tower_z_max + insulator_height/2, insulator_height/2) *
            (smooth_transition(abs(x[0] - phaseA_x), insulator_width, transition_width) + 
             smooth_transition(abs(x[0] - phaseB_x), insulator_width, transition_width) +
             smooth_transition(abs(x[0] - phaseC_x), insulator_width, transition_width)) > 0.5,
            1.0, 0.0
        )

        # 默认空气区域
        air_region = conditional(
            tower_region + phaseA_region + phaseB_region + phaseC_region + 
            phasea_region + phaseb_region + phasec_region + insulator_region > 0.0,
            0.0, 1.0
        )

        # 组合所有区域生成材料函数
        epsilon_expression = (
            tower_region * epsilon0 * epsilon_r[9] +     # Tower (钢材)
            phaseA_region * epsilon0 * epsilon_r[2] +    # PhaseA
            phaseB_region * epsilon0 * epsilon_r[3] +    # PhaseB
            phaseC_region * epsilon0 * epsilon_r[4] +    # PhaseC
            phasea_region * epsilon0 * epsilon_r[5] +    # Phasea
            phaseb_region * epsilon0 * epsilon_r[6] +    # Phaseb
            phasec_region * epsilon0 * epsilon_r[7] +    # Phasec
            insulator_region * epsilon0 * epsilon_r[8] + # Insulator
            air_region * epsilon0 * epsilon_r[1]         # Box (空气)
        )

        sigma_expression = (
            tower_region * sigma[9] +     # Tower (钢材)
            phaseA_region * sigma[2] +    # PhaseA
            phaseB_region * sigma[3] +    # PhaseB
            phaseC_region * sigma[4] +    # PhaseC
            phasea_region * sigma[5] +    # Phasea
            phaseb_region * sigma[6] +    # Phaseb
            phasec_region * sigma[7] +    # Phasec
            insulator_region * sigma[8] + # Insulator
            air_region * sigma[1]         # Box (空气)
        )
        
        # 使用高阶插值提高材料区域平滑性
        epsilon_fn.interpolate(epsilon_expression)
        sigma_fn.interpolate(sigma_expression)

        print("已使用坐标方法设置材料属性，并添加增强平滑过渡区")

    # 7. 创建一个测试电场源 (必要时用于增强求解)
    print("\n设置测试电场源...")

    # 使用模型中心位置作为源中心 - 变量已在前面定义
    source_center_x = x_center
    source_center_y = y_center
    source_center_z = z_center
    source_width = min(x_size, y_size, z_size) * 0.1

    # 创建源函数
    source_real = Function(V_real, name="source_real")
    source_imag = Function(V_imag, name="source_imag")

    # 定义高斯源表达式
    x = SpatialCoordinate(mesh)
    r_squared = (x[0] - source_center_x)**2 + (x[1] - source_center_y)**2 + (x[2] - source_center_z)**2
    gaussian = exp(-r_squared / (2 * source_width**2))

    # 设置一个较小的振幅，避免干扰主要边界条件
    amplitude = 1.0e2  # 进一步减小到100V
    source_real.interpolate(amplitude * gaussian)
    source_imag.interpolate(Constant(0.0))  # 初始相位为0

    # 8. 求解方程 - 使用缩放来提高数值稳定性
    print("开始求解电场方程（使用高阶方法与增强平滑）...")
    solve_start = time.time()

    # 创建解向量
    phi_real = Function(V_real, name="potential_real")
    phi_imag = Function(V_imag, name="potential_imag")

    # 材料属性缩放 - 减少数值范围差异
    # 使用缩放系数来提高条件数
    scale_factor = 1.0e8  # 提高epsilon数量级
    scaled_epsilon = Function(DG0, name="scaled_epsilon")
    scaled_epsilon.assign(epsilon_fn * scale_factor)
    
    # 缩小电导率范围
    sigma_scale = 1.0e-5  # 降低sigma数量级
    scaled_sigma = Function(DG0, name="scaled_sigma")  
    scaled_sigma.assign(sigma_fn * sigma_scale)
    
    # 降低角频率
    scaled_omega = omega * 1.0e-2

    # 定义Robin边界条件参数 - 增大beta值增强边界平滑
    alpha = Constant(1.0)  # Robin条件的系数
    beta = Constant(robin_coeff)  # 梯度项系数，增加到0.5以获得更好的远场效果

    # 获取Box边界度量并定义法向量
    n = FacetNormal(mesh)
    ds_box = Measure("ds", domain=mesh, subdomain_id=valid_boundaries["Box"])

    # 实部方程 - 包含源项及Robin边界条件
    a_real = (scaled_epsilon * inner(grad(u_real), grad(v_real)) * dx -
              scaled_omega * scaled_sigma * u_imag * v_real * dx)
    
    # 添加Robin边界项
    a_real += (alpha * u_real * v_real + beta * inner(grad(u_real), n) * v_real) * ds_box
    
    L_real = source_real * v_real * dx
    L_real += Constant(0.0) * v_real * ds_box  # Robin边界条件右侧项

    # 虚部方程 - 包含源项及Robin边界条件
    a_imag = (scaled_epsilon * inner(grad(u_imag), grad(v_imag)) * dx +
              scaled_omega * scaled_sigma * u_real * v_imag * dx)
    
    # 添加Robin边界项
    a_imag += (alpha * u_imag * v_imag + beta * inner(grad(u_imag), n) * v_imag) * ds_box
    
    L_imag = source_imag * v_imag * dx
    L_imag += Constant(0.0) * v_imag * ds_box  # Robin边界条件右侧项

    # 打印方程系数的范围信息
    print(f"原始介电常数范围: {epsilon_fn.dat.data.min()} 到 {epsilon_fn.dat.data.max()}")
    print(f"缩放后介电常数范围: {scaled_epsilon.dat.data.min()} 到 {scaled_epsilon.dat.data.max()}")
    print(f"原始电导率范围: {sigma_fn.dat.data.min()} 到 {sigma_fn.dat.data.max()}")
    print(f"缩放后电导率范围: {scaled_sigma.dat.data.min()} 到 {scaled_sigma.dat.data.max()}")
    print(f"源项实部最大值: {source_real.dat.data.max()}")
    print(f"使用Robin边界条件: alpha={float(alpha)}, beta={float(beta)}")

    # 优化的求解器配置
    solver_parameters = {
        'ksp_type': 'preonly',  
        'pc_type': 'lu',            # 直接求解器适合高对比度问题
        'pc_factor_mat_solver_type': 'mumps',
        'mat_mumps_icntl_24': 1,    # 提高MUMPS稳定性
        'mat_mumps_icntl_14': 300,  # 增加MUMPS工作内存以适应高阶元素
        'ksp_rtol': 1e-6            # 稍微提高收敛精度
    }
    
    # 实现两阶段求解策略
    # 第1阶段 - 先求解简化模型
    print("\n执行两阶段求解策略...")
    # 创建简化电导率模型
    simplified_sigma_fn = Function(DG0)
    simplified_sigma_scale = 0.1  # 降低10倍
    simplified_sigma_fn.assign(sigma_fn * simplified_sigma_scale)
    
    # 创建第一阶段方程 - 使用简化电导率
    simplified_a_real = (scaled_epsilon * inner(grad(u_real), grad(v_real)) * dx -
              scaled_omega * simplified_sigma_fn * u_imag * v_real * dx)
    simplified_a_real += (alpha * u_real * v_real + beta * inner(grad(u_real), n) * v_real) * ds_box
    
    simplified_a_imag = (scaled_epsilon * inner(grad(u_imag), grad(v_imag)) * dx +
              scaled_omega * simplified_sigma_fn * u_real * v_imag * dx)
    simplified_a_imag += (alpha * u_imag * v_imag + beta * inner(grad(u_imag), n) * v_imag) * ds_box
    
    # 求解第一阶段
    print("第1阶段: 使用简化电导率模型")
    try:
        print("求解电位实部 (简化阶段)...")
        solve(simplified_a_real == L_real, phi_real, bcs=bcs_real, solver_parameters=solver_parameters)
        print("求解电位虚部 (简化阶段)...")
        solve(simplified_a_imag == L_imag, phi_imag, bcs=bcs_imag, solver_parameters=solver_parameters)
    except Exception as e:
        print(f"简化模型求解失败: {e}")
        # 如果简化模型失败，初始化为零场
        phi_real.interpolate(Constant(0.0))
        phi_imag.interpolate(Constant(0.0))
    
    # 保存第一阶段结果
    stage1_phi_real = Function(V_real)
    stage1_phi_imag = Function(V_imag)
    stage1_phi_real.assign(phi_real)
    stage1_phi_imag.assign(phi_imag)
    
    # 第2阶段 - 使用完整模型，以第1阶段结果为初值
    print("第2阶段: 使用完整电导率模型")
    
    # 求解实部
    print("求解电位实部...")
    try:
        solve(a_real == L_real, phi_real, bcs=bcs_real, solver_parameters=solver_parameters)
    except Exception as e:
        print(f"实部求解失败，尝试使用迭代方法: {e}")
        # 备用求解器参数 - 迭代方法
        backup_solver_parameters = {
            'ksp_type': 'gmres',
            'pc_type': 'gamg',       # 使用更先进的代数多重网格预处理器
            'pc_gamg_coarse_eq_limit': 1000,
            'ksp_rtol': 1e-6,
            'ksp_atol': 1e-9,
            'ksp_max_it': 2000,
            'ksp_monitor': None
        }
        solve(a_real == L_real, phi_real, bcs=bcs_real, solver_parameters=backup_solver_parameters)
    
    # 求解虚部
    print("求解电位虚部...")
    try:
        solve(a_imag == L_imag, phi_imag, bcs=bcs_imag, solver_parameters=solver_parameters)
    except Exception as e:
        print(f"虚部求解失败，尝试使用迭代方法: {e}")
        # 备用求解器参数
        backup_solver_parameters = {
            'ksp_type': 'gmres',
            'pc_type': 'gamg',       # 使用更先进的代数多重网格预处理器
            'pc_gamg_coarse_eq_limit': 1000,
            'ksp_rtol': 1e-6,
            'ksp_atol': 1e-9,
            'ksp_max_it': 2000,
            'ksp_monitor': None
        }
        solve(a_imag == L_imag, phi_imag, bcs=bcs_imag, solver_parameters=backup_solver_parameters)

    solve_time = time.time() - solve_start
    print(f"方程求解完成，用时: {solve_time:.2f} 秒")

    # 9. 使用优化方法计算电场强度
    print("计算电场强度...")

    # 使用较低阶的向量空间以避免内存溢出
    V_vec_med = VectorFunctionSpace(mesh, "CG", 2)
    CG2 = FunctionSpace(mesh, "CG", 2)

    # 直接使用Firedrake的内置方法计算电场，避免手动处理数组
    grad_phi_real = Function(V_vec_med, name="grad_phi_real")
    grad_phi_imag = Function(V_vec_med, name="grad_phi_imag")

    # 使用内插计算梯度
    grad_phi_real.interpolate(-grad(phi_real))
    grad_phi_imag.interpolate(-grad(phi_imag))

    # 使用Firedrake的内置方法计算电场强度平方
    E_real_squared = Function(CG2, name="real_squared")
    E_imag_squared = Function(CG2, name="imag_squared")

    # 分别计算各分量函数 - 这样可以避免直接处理可能是数组的元素
    E_real_x = Function(CG2)
    E_real_y = Function(CG2)
    E_real_z = Function(CG2)
    E_imag_x = Function(CG2)
    E_imag_y = Function(CG2)
    E_imag_z = Function(CG2)

    # 提取各个分量
    E_real_x.interpolate(grad_phi_real[0])
    E_real_y.interpolate(grad_phi_real[1])
    E_real_z.interpolate(grad_phi_real[2])
    E_imag_x.interpolate(grad_phi_imag[0])
    E_imag_y.interpolate(grad_phi_imag[1])
    E_imag_z.interpolate(grad_phi_imag[2])

    # 计算平方和
    E_real_squared.dat.data[:] = E_real_x.dat.data[:]**2 + E_real_y.dat.data[:]**2 + E_real_z.dat.data[:]**2
    E_imag_squared.dat.data[:] = E_imag_x.dat.data[:]**2 + E_imag_y.dat.data[:]**2 + E_imag_z.dat.data[:]**2

    # 计算总平方值
    E_squared = Function(CG2, name="field_squared")
    E_squared.dat.data[:] = E_real_squared.dat.data[:] + E_imag_squared.dat.data[:]
    
    # 检查平方值
    print(f"电场平方值范围: {np.min(E_squared.dat.data):.2e} 到 {np.max(E_squared.dat.data):.2e}")
    
    # 处理平方值中的负值
    E_squared_data = E_squared.dat.data
    neg_count_squared = np.sum(E_squared_data < 0)
    if neg_count_squared > 0:
        print(f"警告: 发现 {neg_count_squared} 个负的平方场强值，已自动修正")
        E_squared_data[E_squared_data < 0] = 0.0
    
    # 计算场强
    E_mag = Function(CG2, name="field_magnitude")
    E_mag.dat.data[:] = np.sqrt(E_squared_data)
    
    # 打印场强数据
    print(f"电场强度范围: {np.min(E_mag.dat.data):.2e} 到 {np.max(E_mag.dat.data):.2e}")

    # 验证导体内部场强
    # 识别导体单元
    conductor_cells = [i for i, s in enumerate(sigma_fn.dat.data) if s > 1.0]
    if len(conductor_cells) > 0:
        # 检查索引是否在有效范围内
        valid_conductor_cells = [i for i in conductor_cells if i < len(E_mag.dat.data)]
        if valid_conductor_cells:
            mean_conductor_field = np.mean(E_mag.dat.data[valid_conductor_cells])
            max_conductor_field = np.max(E_mag.dat.data[valid_conductor_cells])
            print(f"导体内部平均场强: {mean_conductor_field:.2e} V/m, 最大值: {max_conductor_field:.2e} V/m")
        else:
            print("没有有效的导体单元可以计算场强")

    # 保存为NPZ格式用于数据分析
    print(f"保存结果到: {npz_file}")

    try:
        # 使用E_mag的函数空间作为基准空间
        field_space = E_mag.function_space()
        print(f"使用场强函数空间作为基准: {field_space}")
        
        # 创建坐标函数，确保与场强使用完全相同的函数空间
        V_coords = VectorFunctionSpace(mesh, field_space.ufl_element())
        coordinates_fn = Function(V_coords)
        x = SpatialCoordinate(mesh)
        coordinates_fn.interpolate(as_vector(x))
        
        # 获取所有场强点的坐标
        field_coordinates = coordinates_fn.dat.data
        E_mag_data = E_mag.dat.data
        
        # 验证长度匹配
        print(f"坐标数组形状: {field_coordinates.shape}")
        print(f"电场强度数组形状: {E_mag_data.shape}")
        
        # 将其他场投影到场强空间以确保一致性
        phi_real_field = Function(field_space, name="phi_real_field")
        phi_imag_field = Function(field_space, name="phi_imag_field")
        
        # 使用投影操作确保所有场在同一空间
        phi_real_field.project(phi_real)
        phi_imag_field.project(phi_imag)
        
        phi_real_data = phi_real_field.dat.data
        phi_imag_data = phi_imag_field.dat.data
        
        # 电场向量需要单独处理每个分量
        E_real_x_field = Function(field_space)
        E_real_y_field = Function(field_space)
        E_real_z_field = Function(field_space)
        E_imag_x_field = Function(field_space)
        E_imag_y_field = Function(field_space)
        E_imag_z_field = Function(field_space)
        
        # 投影各分量
        E_real_x_field.project(grad_phi_real[0])
        E_real_y_field.project(grad_phi_real[1])
        E_real_z_field.project(grad_phi_real[2])
        E_imag_x_field.project(grad_phi_imag[0])
        E_imag_y_field.project(grad_phi_imag[1])
        E_imag_z_field.project(grad_phi_imag[2])
        
        # 重组为向量数组
        E_real_data = np.column_stack((
            E_real_x_field.dat.data,
            E_real_y_field.dat.data,
            E_real_z_field.dat.data
        ))
        E_imag_data = np.column_stack((
            E_imag_x_field.dat.data,
            E_imag_y_field.dat.data,
            E_imag_z_field.dat.data
        ))
        
        # 也投影材料属性
        epsilon_field = Function(field_space)
        sigma_field = Function(field_space)
        epsilon_field.project(epsilon_fn)
        sigma_field.project(sigma_fn)
        
        epsilon_data = epsilon_field.dat.data
        sigma_data = sigma_field.dat.data
        
        # 创建Box区域掩码
        buffer = 0.01  # 给边界添加1%的缓冲区
        x_buffer = (x_max - x_min) * buffer
        y_buffer = (y_max - y_min) * buffer
        z_buffer = (z_max - z_min) * buffer
        
        box_mask = ((field_coordinates[:, 0] >= (x_min + x_buffer)) & 
                    (field_coordinates[:, 0] <= (x_max - x_buffer)) &
                    (field_coordinates[:, 1] >= (y_min + y_buffer)) & 
                    (field_coordinates[:, 1] <= (y_max - y_buffer)) &
                    (field_coordinates[:, 2] >= (z_min + z_buffer)) & 
                    (field_coordinates[:, 2] <= (z_max - z_buffer)))
        
        # 进一步限制为空气区域
        air_mask = (sigma_data < 1e-8)
        combined_mask = box_mask & air_mask
        
        # 应用过滤器
        box_coordinates = field_coordinates[combined_mask]
        box_E_mag = E_mag_data[combined_mask]
        box_phi_real = phi_real_data[combined_mask]
        box_phi_imag = phi_imag_data[combined_mask]
        box_E_real = E_real_data[combined_mask]
        box_E_imag = E_imag_data[combined_mask]
        box_epsilon = epsilon_data[combined_mask]
        box_sigma = sigma_data[combined_mask]
        
        # 打印统计信息
        print(f"全部坐标数量: {len(field_coordinates)}")
        print(f"Box区域坐标数量: {np.sum(box_mask)}")
        print(f"Box区域空气点数量: {len(box_coordinates)} ({len(box_coordinates)/len(field_coordinates)*100:.1f}%)")
        
        # 更新元数据
        metadata = {
            'date': time.strftime("%Y-%m-%d %H:%M:%S"),
            'mesh_file': mesh_file,
            'solver': 'firedrake_optimized',
            'element_order': str(field_space.ufl_element()),
            'boundary_conditions': str(valid_boundaries),
            'robin_params': {'alpha': float(alpha), 'beta': float(beta)},
            'max_conductivity': max_conductivity,
            'scale_factors': {'epsilon': scale_factor, 'sigma': sigma_scale},
            'computation_time': time.time() - start_time,
            'box_filter_info': {
                'total_points': len(field_coordinates),
                'box_points': int(np.sum(box_mask)),
                'box_air_points': len(box_coordinates),
                'percentage': float(len(box_coordinates)/len(field_coordinates)*100)
            }
        }
        
        if 'mean_conductor_field' in locals():
            metadata['conductor_stats'] = {
                'mean': float(mean_conductor_field), 
                'max': float(max_conductor_field)
            }
        
        # 保存NPZ文件
        np.savez(npz_file,
                 coordinates=box_coordinates,
                 phi_real=box_phi_real,
                 phi_imag=box_phi_imag,
                 E_real=box_E_real,
                 E_imag=box_E_imag,
                 E_mag=box_E_mag,
                 epsilon=box_epsilon,
                 sigma=box_sigma,
                 freq=freq,
                 metadata=metadata
                 )
        
        print(f"NPZ文件已成功保存: {npz_file}")
        print(f"保存了 {len(box_coordinates)} 个Box区域内的空气点数据")
        
    except Exception as e:
        print(f"保存NPZ文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()

    # 计算一些统计信息
    max_E = E_mag.dat.data.max()
    print(f"\n结果统计:")
    print(f"最大电场强度: {max_E:.2f} V/m")
    print(f"最大电位实部: {phi_real.dat.data.max():.2f} V")
    print(f"最大电位虚部: {phi_imag.dat.data.max():.2f} V")

    # 显示总时间
    total_time = time.time() - start_time
    print(f"\n电场分析完成，总用时: {total_time:.2f} 秒")
    print(f"结果已保存到: {npz_file}")

    return True

if __name__ == "__main__":
    # 使用优化参数
    solve_tower_electric_field(
        max_conductivity=35000,  # 限制最大电导率为35000 S/m
        robin_coeff=0.5        # 设置Robin边界系数为0.5
    )
