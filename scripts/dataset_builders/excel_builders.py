"""
Excel Dataset Builders for AutoVend Enterprise Benchmark.
Generates 16 high-quality, realistic automotive Excel workbooks across leading OEMs.
"""

import logging
from pathlib import Path
from typing import List

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

logger = logging.getLogger("enterprise_dataset_gen.excel")


def _style_header(ws, row_idx: int, bg_color: str = "1F497D", text_color: str = "FFFFFF"):
    fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
    font = Font(name="Arial", size=11, bold=True, color=text_color)
    align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for cell in ws[row_idx]:
        if cell.value is not None:
            cell.fill = fill
            cell.font = font
            cell.alignment = align


def _auto_column_widths(ws, min_width: int = 18):
    for col in ws.columns:
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 4, min_width)


# 1. Porsche Taycan Turbo GT Track Telemetry
def generate_porsche_taycan_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Porsche_Taycan_Turbo_GT_Track_Telemetry.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Weissach赛道遥测数据"
    ws1.append(["Porsche Taycan Turbo GT (Weissach Package) 纽博格林北环官方赛道遥测矩阵"])
    ws1.merge_cells("A1:H1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="8B0000", end_color="8B0000", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers1 = ["遥测采样点", "赛道距离 (m)", "车速 (km/h)", "Attack Mode状态", "电驱总功率 (kW)", "电池温度 (℃)", "碳陶刹车盘温度 (℃)", "侧向加速度 (g)"]
    ws1.append(headers1)
    _style_header(ws1, 2, "A52A2A")

    telemetry_rows = [
        ("T01-发车直道", 200, 245.5, "已激活 (Attack Mode)", 815, 38.5, 420.0, 0.15),
        ("T02-一号高速弯", 650, 192.3, "已激活 (Attack Mode)", 760, 39.2, 580.0, 1.45),
        ("T03-连续S弯", 1200, 142.0, "待命 (Overboost)", 520, 40.1, 650.5, 1.62),
        ("T04-看台大直道", 2400, 305.2, "已激活 (Attack Mode)", 815, 41.8, 380.0, 0.08),
        ("T05-重刹发卡弯", 2850, 88.5, "能量回收制动 (-350kW)", -350, 42.6, 760.0, 1.85),
        ("T06-起伏路面盲弯", 3600, 178.4, "待命 (Overboost)", 610, 43.2, 590.2, 1.38),
        ("T07-超长冲刺直道", 5800, 320.0, "已激活 (Attack Mode)", 815, 44.5, 410.0, 0.05),
    ]
    for r in telemetry_rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    ws2 = wb.create_sheet(title="纽北圈速与空气动力学")
    ws2.append(["赛道测试项目", "官方认证成绩", "对标竞品成绩", "空气动力学设定", "技术说明"])
    _style_header(ws2, 1, "8B0000")
    aero_rows = [
        ("纽博格林北环单圈用时", "7分07秒55", "7分25秒23 (Model S Plaid)", "固定式碳纤维大尾翼", "量产四门纯电最速记录"),
        ("拉古纳塞卡赛道用时", "1分27秒87", "1分28秒20 (Plaid Track)", "前唇分流板进气叶片打开", "刷新非官方电动车圈速"),
        ("200km/h整车下压力", "220 kg", "95 kg", "底盘全封闭扩散器", "攻角调整至最高下压力档"),
        ("PCCB碳陶制动盘规格", "前 420mm / 后 410mm", "前 410mm / 后 400mm", "10活塞一体化锻造铝定钳", "抗热衰退极限达 1200℃"),
    ]
    for r in aero_rows:
        ws2.append(r)
    _auto_column_widths(ws2)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 2. BMW i7 xDrive60 Executive Lease Schedule
def generate_bmw_i7_excel(out_dir: Path) -> Path:
    file_path = out_dir / "BMW_i7_xDrive60_Executive_Lease_Schedule.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "企业尊享租赁与摊销计划"
    ws1.append(["宝马 (中国) 官方金融 i7 xDrive60 旗舰豪华轿车 36/48/60期 融资租赁测算明细"])
    ws1.merge_cells("A1:F1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["测算核心指标", "36期 (3年方案)", "48期 (4年方案)", "60期 (5年方案)", "残值保障约定", "核算公式说明"]
    ws1.append(headers)
    _style_header(ws1, 2, "1B4F72")

    items = [
        ("车辆厂商指导价 (元)", 1459000, 1459000, 1459000, "含增值税售价", "官方统一零售价"),
        ("客户首付比例", 0.20, 0.20, 0.25, "企业增值税可抵扣", "首付门槛"),
        ("首付金额 (元)", "=B3*B4", "=C3*C4", "=D3*D4", "签约时支付", "指导价 × 首付比例"),
        ("约定残值兜底比例", 0.50, 0.42, 0.35, "BMW官方二手车保值承诺", "3年50%兜底"),
        ("期满残值尾款 (元)", "=B3*B6", "=C3*C6", "=D3*D6", "可展期/一次性结清/返还车辆", "指导价 × 残值率"),
        ("融资本金 (元)", "=B3-B5", "=C3-C5", "=D3-D5", "计息总基数", "指导价 - 首付款"),
        ("年化租赁综合费率", 0.0349, 0.0369, 0.0389, "大客户协议专享利率", "基准年利率"),
        ("每月净租金 (元)", "=ROUND((B8-B7+B8*B9*(36/12))/36, 2)", "=ROUND((C8-C7+C8*C9*(48/12))/48, 2)", "=ROUND((D8-D7+D8*D9*(60/12))/60, 2)", "按月对公转账", "租金分摊公式"),
    ]
    for r in items:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 3. Mercedes EQS 580 Hyperscreen Supplier BOM
def generate_mercedes_eqs_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Mercedes_EQS_580_Hyperscreen_Supplier_BOM.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Hyperscreen超联屏BOM"
    ws1.append(["梅赛德斯-奔驰 EQS 580 4MATIC MBUX Hyperscreen 三联屏零部件供应商BOM清单"])
    ws1.merge_cells("A1:G1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws1.append(["零件料号", "部件名称", "规格参数", "Tier-1供应商代码", "供应商全称", "单车用量", "安全等级认证"])
    _style_header(ws1, 2, "34495E")

    bom_rows = [
        ("A297-820-0100", "曲面玻璃盖板总成", "1410mm 一体化 3D 弯曲玻璃, 硅酸铝防刮涂层", "V00891", "AGC 旭硝子汽车玻璃", 1, "ECE R43 防爆"),
        ("A297-820-0210", "驾驶员仪表显示屏", "12.3 英寸 LCD, 2400×900 分辨率, 1000nits", "V00422", "LG Display 韩国", 1, "ISO 26262 ASIL-B"),
        ("A297-820-0320", "中央OLED触控大屏", "17.7 英寸 OLED, 3088×1728 分辨率, 触觉反馈", "V00422", "LG Display 韩国", 1, "ISO 26262 ASIL-B"),
        ("A297-820-0430", "副驾驶娱乐OLED屏", "12.3 英寸 OLED, 2400×900, 智能防窥遮蔽", "V00422", "LG Display 韩国", 1, "ISO 26262 ASIL-B"),
        ("A297-540-1080", "MBUX核心车机主机", "Nvidia 8核CPU + 24GB RAM + 328GB/s带宽", "V00109", "Harman 哈曼国际", 1, "ISO 26262 ASIL-D"),
        ("A297-820-0990", "执行器触觉振动马达", "8个驱动执行器, 提供12种微震动触觉反馈", "V00511", "Johnson Electric 德昌电机", 8, "AEC-Q200"),
    ]
    for r in bom_rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 4. Audi RS e-tron GT Charging Curve Matrix
def generate_audi_etron_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Audi_RS_etron_GT_Charging_Curve_Matrix.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "800V高压超充遥测"
    ws1.append(["奥迪 RS e-tron GT 800V 高压电气架构直流快充特性曲线与电芯热管理矩阵"])
    ws1.merge_cells("A1:G1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="780000", end_color="780000", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["电池SOC (%)", "充电功率 (kW)", "端电压 (V)", "充电电流 (A)", "最高电芯温度 (℃)", "冷却液流量 (L/min)", "电芯温差 ΔT (℃)"]
    ws1.append(headers)
    _style_header(ws1, 2, "9A031E")

    curve_data = [
        (5, 150.0, 720.0, 208.3, 25.0, 15.0, 1.2),
        (10, 268.5, 745.0, 360.4, 28.5, 25.0, 1.5),
        (20, 270.0, 760.0, 355.3, 33.0, 32.0, 1.8),
        (30, 270.0, 775.0, 348.4, 37.5, 35.0, 2.1),
        (40, 260.0, 788.0, 329.9, 41.0, 35.0, 2.3),
        (50, 210.0, 800.0, 262.5, 43.5, 35.0, 2.0),
        (60, 175.0, 810.0, 216.0, 44.0, 35.0, 1.7),
        (70, 130.0, 818.0, 158.9, 42.5, 30.0, 1.4),
        (80, 80.0, 825.0, 96.9, 40.0, 25.0, 1.1),
    ]
    for r in curve_data:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 5. Tesla Model 3 Highland Trim Comparison
def generate_tesla_model3_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Tesla_Model_3_Highland_Trim_Comparison.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "焕新版配置全系对比"
    ws1.append(["特斯拉 Model 3 焕新版 (Highland) 后驱版 / 长续航全轮驱动 / 高性能全轮驱动 对比矩阵"])
    ws1.merge_cells("A1:E1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="CC0000", end_color="CC0000", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["对比技术维度", "后轮驱动版 (RWD)", "长续航全驱版 (Long Range)", "高性能全驱版 (Performance)", "核心差异说明"]
    ws1.append(headers)
    _style_header(ws1, 2, "E60000")

    specs = [
        ("官方指导售价 (元)", "245,900", "285,900", "335,900", "全国统一零售价"),
        ("驱动形式与电机", "后置单电机 (永磁同步)", "前后双电机 (前感应+后永磁)", "全新第四代高性能双电机", "动力总成差异"),
        ("最大综合功率/扭矩", "194 kW / 340 N·m", "331 kW / 559 N·m", "343 kW / 623 N·m", "零百弹射加速基础"),
        ("0-100 km/h 加速时间", "6.1 秒", "4.4 秒", "3.1 秒", "赛道级弹射起步"),
        ("电池电芯类型与化学体系", "宁德时代 磷酸铁锂 (LFP)", "LG新能源 三元锂 (NMC)", "LG新能源 高能量密度三元锂", "不同电芯耐寒特性"),
        ("标称电池包容量 (kWh)", "60.0 kWh", "78.4 kWh", "78.4 kWh", "续航基础保障"),
        ("CLTC 综合续航里程", "606 km", "713 km", "623 km", "国标综合工况"),
        ("悬架系统与减振器", "全新调校舒适型减振器", "全新调校舒适型减振器", "全新自适应阻尼悬架 (CDC)", "软硬件动态可变阻尼"),
    ]
    for r in specs:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 6. NIO ET9 SkyRide Chassis BOM
def generate_nio_et9_excel(out_dir: Path) -> Path:
    file_path = out_dir / "NIO_ET9_SkyRide_Chassis_BOM.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "SkyRide天行底盘BOM"
    ws1.append(["蔚来 ET9 SkyRide 天行智能底盘系统核心零部件 BOM 清单 (全线控+全主动悬架)"])
    ws1.merge_cells("A1:G1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="005B96", end_color="005B96", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["部件分类", "零件名称与规格", "核心技术指标", "供应商代码", "供应商名称", "单车数量", "供电电压架构"]
    ws1.append(headers)
    _style_header(ws1, 2, "03396C")

    et9_bom = [
        ("全主动悬架", "天行集成式液压全主动减振器", "每个减振器配备独立高压液压泵, 1微秒响应", "V10992", "蔚来全栈自研 + Multimatic", 4, "48V 主动悬架高压母线"),
        ("线控转向", "线控转向方向盘转向管柱执行器", "取消机械中间轴, 可变转向比 6:1 至 14:1", "V00881", "ZF 采埃孚转向系统", 1, "双 12V 冗余供电"),
        ("后轮转向", "后轮主动转向角度执行机构", "后轮最大转向角达 8.3 度, 转弯直径 10.9 米", "V00881", "ZF 采埃孚转向系统", 1, "48V 供电"),
        ("线控制动", "EMB 纯机械电子线控制动卡钳", "无刹车油液压管路, 电机直接夹紧刹车盘", "V00455", "Brembo 布雷博 / 蔚来自研", 4, "双回路独立蓄电池供电"),
    ]
    for r in et9_bom:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 7. Li L9 Ultra Dealer Maintenance Rate Card
def generate_li_l9_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Li_L9_Ultra_Dealer_Maintenance_Rate_Card.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "官方维保工时与配件价格表"
    ws1.append(["理想汽车官方售后服务中心 L9 Ultra 10万公里常规保养规范及配件全国统一工时费率表"])
    ws1.merge_cells("A1:G1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="2E4053", end_color="2E4053", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["保养项目分类", "配件料号与名称", "建议更换周期", "配件统一零售价 (元)", "标准工时 (工时)", "工时单价 (元/工时)", "单项合计 (元)"]
    ws1.append(headers)
    _style_header(ws1, 2, "34495E")

    maint_rows = [
        ("增程发动机机油", "专用全合成机油 0W-20 (4L)", "10,000 km / 12个月", 398, 0.8, 150, "=D3+E3*F3"),
        ("增程发动机机滤", "高效机油滤清器滤芯", "10,000 km / 12个月", 65, 0.2, 150, "=D4+E4*F4"),
        ("空调滤清器", "CN95 级高效抗病毒空调滤芯", "10,000 km / 12个月", 138, 0.3, 150, "=D5+E5*F5"),
        ("空气滤清器", "发动机进气空气滤芯", "20,000 km / 24个月", 115, 0.2, 150, "=D6+E6*F6"),
        ("火花塞总成", "铱铂金专用长寿命火花塞 (4只)", "40,000 km", 420, 0.8, 150, "=D7+E7*F7"),
        ("制动液更换", "DOT 4 高沸点制动液 (1L)", "40,000 km / 24个月", 98, 1.2, 150, "=D8+E8*F8"),
        ("电池冷却液", "高绝缘有机型低电导率冷却液 (8L)", "80,000 km / 48个月", 480, 1.5, 150, "=D9+E9*F9"),
    ]
    for r in maint_rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 8. Zeekr 009 Grand Executive Four-Seat Specs
def generate_zeekr_009_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Zeekr_009_Grand_Executive_Four_Seat_Specs.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "光辉四座旗舰豪华规格"
    ws1.append(["极氪 009 光辉 (Grand) 四座行政旗舰 MPV 核心技术参数与奢华座舱配置清单"])
    ws1.merge_cells("A1:E1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="B8860B", end_color="B8860B", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["系统配置类别", "技术参数项目", "极氪 009 光辉版配置指标", "供应商或材质说明", "豪华舒适属性"]
    ws1.append(headers)
    _style_header(ws1, 2, "DAA520")

    rows = [
        ("三电动力总成", "前后双碳化硅电驱总成", "峰值功率 580 kW (788 PS) / 810 N·m", "威睿电动 800V 高压碳化硅", "零百加速 3.9 秒最速 MPV"),
        ("动力电池包", "108 kWh 麒麟三元锂电池", "最大充电倍率 5C, 11.5分钟 10%-80%", "宁德时代高能量密度电芯", "CLTC 综合续航 702 km"),
        ("座舱隐私屏风", "43 英寸云端智慧 4K 超清大屏", "防眩光护眼涂层, 独立车机互联", "京东方定制车规大屏", "一键升降完全物理隔断"),
        ("后排行政座椅", "超柔苯胺全粒面头层真皮座椅", "24向电动调节, 16点气压指压按摩", "澳大利亚顶级天然牧场真皮", "带腿托及独立石墨烯加热"),
        ("智能调光车窗", "LC 固态光幕调光玻璃", "10 档光线明暗调节, 最暗透光率 < 0.5%", "京东方调光光幕技术", "秒级黑化彻底保障隐私"),
    ]
    for r in rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 9. Fangchengbao Bao5 DMO Offroad Matrix
def generate_fangchengbao_bao5_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Fangchengbao_Bao5_DMO_Offroad_Matrix.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "DMO超级混动越野参数"
    ws1.append(["方程豹 豹5 DMO 超级混动越野平台机械参数与极限越野几何通过性指标"])
    ws1.merge_cells("A1:E1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="117864", end_color="117864", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["机械与越野系统", "关键参数项目", "标准版参数指标", "云辇-P版参数指标", "技术实现原理解析"]
    ws1.append(headers)
    _style_header(ws1, 2, "16A085")

    rows = [
        ("越野几何参数", "接近角 / 离去角", "35° / 32°", "39° / 35°", "云辇液压底盘升降提升通过性"),
        ("越野几何参数", "最小离地间隙 (空载)", "220 mm", "310 mm", "底盘离地提升90mm避免托底"),
        ("涉水性能指标", "最大安全涉水深度", "700 mm", "790 mm", "IP68电驱电控及进气口后置"),
        ("动力与差速锁", "前后机械牙嵌式差速锁", "标配中央电控虚拟差速锁+前后桥锁", "标配三把差速锁", "轮间打滑10毫秒锁止"),
        ("极限脱困能力", "豹式掉头 (原地自转掉头)", "转弯半径压缩至 3.4 米", "转弯半径压缩至 3.4 米", "前后轮反转+内侧后轮电控锁止"),
    ]
    for r in rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 10. Luxeed S7 Battery Degradation Telemetry
def generate_luxeed_s7_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Luxeed_S7_Battery_Degradation_Telemetry.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "10万公里循环老化实测"
    ws1.append(["智界 S7 华为 DriveONE 巨鲸 800V 高压电池包 10万公里加速老化测试遥测表"])
    ws1.merge_cells("A1:G1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="1B2631", end_color="1B2631", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["累计里程 (km)", "等效充放电循环 (Cycles)", "电池健康度 SOH (%)", "直流内阻 DCIR (mΩ)", "可用容量 (kWh)", "库伦充放电效率 (%)", "电芯最大压差 (mV)"]
    ws1.append(headers)
    _style_header(ws1, 2, "283747")

    data = [
        (0, 0, 100.0, 32.5, 82.0, 99.8, 8),
        (20000, 52, 98.4, 33.1, 80.7, 99.7, 9),
        (40000, 105, 96.9, 33.8, 79.5, 99.6, 11),
        (60000, 158, 95.5, 34.6, 78.3, 99.5, 12),
        (80000, 212, 94.2, 35.4, 77.2, 99.5, 14),
        (100000, 268, 93.0, 36.2, 76.3, 99.4, 15),
    ]
    for r in data:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 11. Stelato S9 Executive Interior BOM
def generate_stelato_s9_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Stelato_S9_Executive_Interior_BOM.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "享界S9行政座舱BOM"
    ws1.append(["享界 S9 (Stelato S9) 寰宇行政座舱核心零部件与奢华材质 BOM 汇总表"])
    ws1.merge_cells("A1:F1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="4A235A", end_color="4A235A", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["座舱功能分区", "零部件料号及名称", "规格特性与材质", "供应商全称", "单车配置用量", "舒适性亮点"]
    ws1.append(headers)
    _style_header(ws1, 2, "5B2C6F")

    rows = [
        ("后排尊享席", "零重力行政级真皮座椅", "12向电动调节, 108°躯干大角零重力展开", "延锋安道拓 (Yanfeng)", 1, "首创轿跑后排零重力设计"),
        ("视听娱乐", "32英寸后排车规级升降投影幕布", "车规级激光投影机, 100% P3 广色域", "光峰科技 (Appotronics)", 1, "全封闭遮光电动帘联动"),
        ("空间声学", "HUAWEI SOUND 卓越系列音响", "25单元专业声学布局, 2080W独立功放", "华为技术有限公司", 1, "施罗德散布声学舱"),
        ("座舱遮阳", "全车双层隔热隔音隔紫外线玻璃", "红外线阻隔率 99%, 紫外线隔绝 99.9%", "福耀玻璃 (Fuyao)", 1, "全系双层夹胶声学玻璃"),
    ]
    for r in rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 12. Avatr 11 Chassis CDC Damper Matrix
def generate_avatr_11_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Avatr_11_Chassis_CDC_Damper_Matrix.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "CDC减振阻尼系数标定"
    ws1.append(["阿维塔 11 智能电控动态减振器 (CDC) 不同驾驶模式阻尼力与活塞速度特性表"])
    ws1.merge_cells("A1:G1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="1F618D", end_color="1F618D", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["活塞运动速度 (m/s)", "舒适模式复原力 (N)", "舒适模式压缩力 (N)", "标准模式复原力 (N)", "运动模式复原力 (N)", "赛道模式复原力 (N)", "电磁阀电流 (mA)"]
    ws1.append(headers)
    _style_header(ws1, 2, "2980B9")

    matrix_rows = [
        (0.05, 180, 120, 260, 380, 520, 1600),
        (0.10, 320, 210, 480, 720, 950, 1400),
        (0.30, 850, 480, 1250, 1820, 2350, 1000),
        (0.52, 1450, 780, 2100, 2950, 3800, 600),
        (1.00, 2300, 1200, 3200, 4400, 5600, 200),
    ]
    for r in matrix_rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 13. IM L6 VMC Digital Chassis BOM
def generate_im_l6_excel(out_dir: Path) -> Path:
    file_path = out_dir / "IM_L6_VMC_Digital_Chassis_BOM.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "灵蜥数字底盘核心BOM"
    ws1.append(["智己 IM L6 灵蜥数字底盘与线控四轮转向 (VMC) 核心元器件规格表"])
    ws1.merge_cells("A1:F1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="0E6655", end_color="0E6655", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["系统子模块", "零部件名称", "关键性能技术参数", "供应商", "控制总线与协议", "特有功能支持"]
    ws1.append(headers)
    _style_header(ws1, 2, "117A65")

    rows = [
        ("中央协调控制器", "VMC 智慧运动控制器", "集成前后桥横摆/俯仰/侧倾联合算法, 算力 1200 DMIPS", "上汽联合研发", "CAN-FD / 车载以太网", "三轴六自由度协同控制"),
        ("后轮转向系统", "大陆智能后轮转向执行器", "双向最大偏转角 ±6°, 响应速度 60°/s", "Continental 大陆集团", "FlexRay 双通道冗余", "全场景蟹行平移与泊车"),
        ("半固态电池", "第一代光年超快充固态电池", "容量 133 kWh, 能量密度 300 Wh/kg, 准900V", "清陶能源 (QingTao)", "专用 BMS 高精度采样", "CLTC 续航突破 1000 km"),
        ("数字转向机", "高集成双齿轮电动助力转向", "齿条最大输出力 12 kN, 齿条行程 160 mm", "Bosch 博世", "双霍尔角度传感器", "极速转弯半径仅 4.99 米"),
    ]
    for r in rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 14. GAC Hyper SSR Supercar Dyno Matrix
def generate_gac_hyper_ssr_excel(out_dir: Path) -> Path:
    file_path = out_dir / "GAC_Hyper_SSR_Supercar_Dyno_Matrix.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "SSR马力机测功图谱"
    ws1.append(["广汽埃安 昊铂 Hyper SSR 纯电超跑 1225匹马力机全负荷轮上动力测试表"])
    ws1.merge_cells("A1:G1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="922B21", end_color="922B21", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["电机转速 (rpm)", "一挡轮端扭矩 (N·m)", "二挡轮端扭矩 (N·m)", "轮上净功率 (kW)", "综合马力 (HP)", "逆变器直流电压 (V)", "母线电流 (A)"]
    ws1.append(headers)
    _style_header(ws1, 2, "B03A2E")

    dyno_rows = [
        (2000, 12000, 4210, 251, 341, 890, 310),
        (5000, 12000, 4210, 628, 854, 880, 750),
        (7500, 11460, 4020, 901, 1225, 865, 1100),
        (10000, 8590, 3015, 901, 1225, 860, 1105),
        (15000, 5730, 2010, 901, 1225, 855, 1110),
        (20000, 4290, 1508, 900, 1224, 850, 1112),
    ]
    for r in dyno_rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 15. Tank 700 Hi4-T Offroad Gear Ratios
def generate_tank_700_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Tank_700_Hi4-T_Offroad_Gear_Ratios.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Hi4-T混动传动齿比矩阵"
    ws1.append(["长城汽车 坦克 700 Hi4-T 3.0T V6 9HAT 混动变速器与分动箱减速比规格表"])
    ws1.merge_cells("A1:F1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="7D6608", end_color="7D6608", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["挡位序号", "机械齿轮传动比", "分动箱低速4L传动比", "轮端总减速比", "最大承受输入扭矩 (N·m)", "工况适配说明"]
    ws1.append(headers)
    _style_header(ws1, 2, "9A7D0A")

    gear_rows = [
        ("1 挡 (大速比起步)", 5.288, 2.64, 13.96, 850, "极限大坡度攀爬与脱困"),
        ("2 挡", 3.259, 2.64, 8.60, 850, "低速重载脱困"),
        ("3 挡", 2.189, 2.64, 5.78, 850, "泥泞/雪地中低速行驶"),
        ("4 挡", 1.602, 2.64, 4.23, 850, "城市工况常规提速"),
        ("5 挡", 1.258, 2.64, 3.32, 850, "郊区快速巡航"),
        ("6 挡 (直接挡)", 1.000, 1.00, 1.00, 850, "高速直驱工况"),
        ("7 挡 (超速挡1)", 0.812, 1.00, 0.81, 850, "高速经济巡航"),
        ("8 挡 (超速挡2)", 0.671, 1.00, 0.67, 850, "超低油耗巡航"),
        ("9 挡 (超速挡3)", 0.589, 1.00, 0.59, 850, "120km/h发动机转速仅1500rpm"),
        ("倒挡 (Reverse)", 4.800, 2.64, 12.67, 850, "极限倒车脱困"),
    ]
    for r in gear_rows:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 16. Chery Exeed Sterra ES Aerodynamics Matrix
def generate_chery_exeed_excel(out_dir: Path) -> Path:
    file_path = out_dir / "Chery_Exeed_Sterra_ES_Aerodynamics_Matrix.xlsx"
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "风洞风阻与升力特性表"
    ws1.append(["奇瑞星途 星纪元 ES (Sterra ES) 2026款风洞空气动力学实测系数表 (0.205超低Cd)"])
    ws1.merge_cells("A1:G1")
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="145A32", end_color="145A32", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["测试车速 (km/h)", "AGS主动进气格栅状态", "电动尾翼升起挡位", "风阻系数 Cd", "前轴升力系数 Clf", "后轴升力系数 Clr", "折合续航提升 (km)"]
    ws1.append(headers)
    _style_header(ws1, 2, "196F3D")

    aero_data = [
        (80, "完全闭合", "0 挡 (收回平齐)", 0.205, -0.015, -0.020, 28),
        (100, "完全闭合", "1 挡 (低风阻迎角5°)", 0.208, -0.022, -0.045, 32),
        (120, "完全闭合", "2 挡 (极速下压力迎角11°)", 0.218, -0.035, -0.098, 25),
        (120, "打开 30%", "2 挡 (极速下压力迎角11°)", 0.225, -0.030, -0.092, 18),
        (140, "完全打开", "2 挡 (极速下压力迎角11°)", 0.238, -0.025, -0.088, 10),
    ]
    for r in aero_data:
        ws1.append(r)
    _auto_column_widths(ws1)

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_all_new_excel_datasets(out_dir: Path) -> List[Path]:
    """Generate all 16 new Excel benchmark datasets."""
    generators = [
        generate_porsche_taycan_excel,
        generate_bmw_i7_excel,
        generate_mercedes_eqs_excel,
        generate_audi_etron_excel,
        generate_tesla_model3_excel,
        generate_nio_et9_excel,
        generate_li_l9_excel,
        generate_zeekr_009_excel,
        generate_fangchengbao_bao5_excel,
        generate_luxeed_s7_excel,
        generate_stelato_s9_excel,
        generate_avatr_11_excel,
        generate_im_l6_excel,
        generate_gac_hyper_ssr_excel,
        generate_tank_700_excel,
        generate_chery_exeed_excel,
    ]
    results = []
    for g in generators:
        results.append(g(out_dir))
    return results
