"""
Enterprise Automotive Benchmark Dataset Generator for AutoVend.
(scripts/generate_enterprise_datasets.py)

Generates a realistic, comprehensive, multi-brand automotive corpus across:
1. Excel (.xlsx):
   - BYD_Financing_Rates_2026.xlsx (3 sheets, multi-tier financing & lease rate matrices, formulas)
   - Xiaomi_SU7_Ultra_Technical_Specs.xlsx (4 sheets, trim comparison, V8s/V6s motor BOM, Bilstein chassis)
   - Huawei_Tuling_Chassis_BOM.xlsx (3 sheets, Tier-1 supplier BOM, CDC damper, warranty table)
2. Word (.docx):
   - Tesla_Model_Y_Service_Bulletin.docx (Recall SB-24-00-001, steering sensor calibration, tables, package footnotes)
   - NIO_Power_Swap_Safety_Manual.docx (SOP-HV-900 900V emergency rescue procedure, H1-H4, DANGER callouts)
3. PowerPoint (.pptx):
   - Zeekr_001_FR_Launch_Presentation.pptx (5 slides, quad-motor 1300HP, ZVC vectoring, comparison table, notes)
   - Li_Mega_vs_Denza_D9_Battlecard.pptx (4 slides, sales battlecard, 0.215 Cd vs 0.30 Cd, 5C charging, notes)
4. Images (.png, .jpg):
   - Xiaomi_V800_Motor_Infographic.png (1920x1080 technical spec infographic poster with EXIF metadata)
   - Instrument_Cluster_Warning.jpg (1280x720 diagnostic photo with TPMS/BMS alerts & EXIF metadata)
5. PDFs (.pdf):
   - Avatr_12_Full_Spec_Manual.pdf (4 pages, continuous tables across pages, borderless grids, running headers)
6. CSV / TSV / JSON / TOML / Markdown:
   - CATL_Qilin_Battery_Thermal_Test.csv (60+ rows sensor logs)
   - National_EV_Subsidy_Policy_2026.json (Subsidy policy & 10+ trim database export)
   - Zeekr_Battery_Warranty_Terms.md (Markdown warranty terms and tables)
   - Bosch_ESP_Firmware_Config.toml (TOML vehicle stability configuration)
   - Powertrain_Efficiency_Matrix.tsv (TSV motor efficiency map)
"""

import io
import json
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path

import docx
import openpyxl
import pptx
import pymupdf as fitz
from docx.enum.table import WD_TABLE_ALIGNMENT
from openpyxl.styles import Alignment, Font, PatternFill
from PIL import Image, ImageDraw, ImageFont
from pptx.dml.color import RGBColor as PPT_RGBColor
from pptx.util import Inches as PPT_Inches
from pptx.util import Pt as PPT_Pt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enterprise_dataset_gen")

PROJECT_ROOT = Path("/home/algieba/projects/hackthon/AutoVend")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.dataset_builders.data_builders import generate_all_new_data_datasets
from scripts.dataset_builders.excel_builders import generate_all_new_excel_datasets
from scripts.dataset_builders.image_builders import generate_all_new_image_datasets
from scripts.dataset_builders.pdf_builders import generate_all_new_pdf_datasets
from scripts.dataset_builders.pptx_builders import generate_all_new_pptx_datasets
from scripts.dataset_builders.word_builders import generate_all_new_word_datasets

BENCHMARK_DIR = PROJECT_ROOT / "data" / "enterprise_benchmark"
SAMPLE_SPECS_DIR = PROJECT_ROOT / "data" / "sample_specs"


# ══════════════════════════════════════════════════════════════════════════
# 1. EXCEL GENERATORS
# ══════════════════════════════════════════════════════════════════════════


def generate_byd_financing_excel(out_dir: Path) -> Path:
    """Generate multi-tier financial financing and lease calculation matrices."""
    file_path = out_dir / "BYD_Financing_Rates_2026.xlsx"
    wb = openpyxl.Workbook()

    # Sheet 1: 0息分期方案
    ws1 = wb.active
    ws1.title = "0息定额分期方案"
    ws1.merge_cells("A1:E1")
    ws1["A1"] = "比亚迪王朝/海洋系列 2026年度 0息定额消费金融方案矩阵"
    ws1["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers1 = ["适用车型与车系", "厂商指导价 (元)", "最高免息额度 (元)", "免息分期期数 (月)", "首付比例要求"]
    for col_idx, h in enumerate(headers1, 1):
        c = ws1.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    zero_interest_data = [
        ("汉 EV 荣耀版 715km 旗舰型", 249800, 100000, 24, "首付最低 35%"),
        ("唐 DM-i 荣耀版 112km 尊荣型", 199800, 80000, 24, "首付最低 30%"),
        ("海豹 EV 荣耀版 650km 四驱性能版", 219800, 90000, 24, "首付最低 30%"),
        ("宋 L EV 662km 卓越型", 229800, 100000, 24, "首付最低 35%"),
        ("腾势 D9 DM-i 980 四驱尊荣型", 389800, 150000, 36, "首付最低 40%"),
        ("仰望 U8 豪华版 (专属金融)", 1098000, 300000, 36, "首付最低 50%"),
    ]

    for r_idx, row_data in enumerate(zero_interest_data, start=3):
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            if c_idx in [2, 3]:
                cell.number_format = "¥#,##0"
            cell.alignment = Alignment(horizontal="center" if c_idx != 1 else "left", vertical="center")

    # Sheet 2: 低息长期贷款_36_60期
    ws2 = wb.create_sheet(title="低息长期贷款_36_60期")
    ws2.merge_cells("A1:F1")
    ws2["A1"] = "比亚迪全系车型 36/48/60期 阶梯低息金融贷款测算表"
    ws2["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws2["A1"].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers2 = ["贷款方案项目", "汉EV 旗舰型", "海豹EV 性能版", "腾势D9 四驱型", "仰望U8 豪华版", "计算口径说明"]
    for col_idx, h in enumerate(headers2, 1):
        c = ws2.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    loan_items = [
        ("车辆零售指导价 (元)", 249800, 219800, 389800, 1098000, "全国统一零售价"),
        ("首付比例", 0.20, 0.20, 0.30, 0.40, "按揭最低首付门槛"),
        ("首付金额 (元)", "=B3*B4", "=C3*C4", "=D3*D4", "=E3*E4", "公式: [指导价 × 首付比例]"),
        ("融资本金 (元)", "=B3-B5", "=C3-C5", "=D3-D5", "=E3-E5", "公式: [指导价 - 首付金额]"),
        ("还款期限 (月)", 36, 48, 60, 60, "合同约定期数"),
        ("年化名义利率", 0.0299, 0.0329, 0.0349, 0.0349, "央行征信评级A级专享"),
        ("月供还款预估 (元)", "=ROUND((B6*(1+B8*3))/B7, 2)", "=ROUND((C6*(1+C8*4))/C7, 2)", "=ROUND((D6*(1+D8*5))/D7, 2)", "=ROUND((E6*(1+E8*5))/E7, 2)", "公式: [(本金 × (1 + 年利率 × 年限)) ÷ 期数]"),
        ("总利息支出 (元)", "=B9*B7-B6", "=C9*C7-C6", "=D9*D7-D6", "=E9*E7-E6", "公式: [月供 × 期数 - 本金]"),
    ]

    for r_idx, (item, b_val, c_val, d_val, e_val, note) in enumerate(loan_items, start=3):
        ws2.cell(row=r_idx, column=1, value=item)
        ws2.cell(row=r_idx, column=2, value=b_val)
        ws2.cell(row=r_idx, column=3, value=c_val)
        ws2.cell(row=r_idx, column=4, value=d_val)
        ws2.cell(row=r_idx, column=5, value=e_val)
        ws2.cell(row=r_idx, column=6, value=note)

        # Apply formatting
        if r_idx in [3, 5, 6, 9, 10]:
            for col in range(2, 6):
                ws2.cell(row=r_idx, column=col).number_format = "¥#,##0.00"
        elif r_idx in [4, 8]:
            for col in range(2, 6):
                ws2.cell(row=r_idx, column=col).number_format = "0.00%"

    # Sheet 3: 残值租赁_Lease_方案
    ws3 = wb.create_sheet(title="保值回购与残值租赁_Lease")
    ws3.merge_cells("A1:E1")
    ws3["A1"] = "比亚迪高端车型官方 36个月保值回购与残值租赁 (Balloon Lease) 方案"
    ws3["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws3["A1"].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers3 = ["租赁测算项目", "腾势 D9 尊荣型", "仰望 U8 豪华版", "仰望 U9 赛道版", "业务履约约定与条款"]
    for col_idx, h in enumerate(headers3, 1):
        c = ws3.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    lease_data = [
        ("车辆官方指导价 (元)", 389800, 1098000, 1680000, "含税开票价格"),
        ("租赁保证金融资比例", 0.15, 0.20, 0.25, "期满可无息退还或抵扣尾款"),
        ("保证金金额 (元)", "=B3*B4", "=C3*C4", "=D3*D4", "公式: [指导价 × 保证金比例]"),
        ("36个月约定残值率", 0.55, 0.58, 0.52, "官方保证回购兜底价格"),
        ("到期残值尾款 (元)", "=B3*B6", "=C3*C6", "=D3*D6", "公式: [指导价 × 残值率]"),
        ("36期租金总额 (元)", "=B3-B7+B3*0.09", "=C3-C7+C3*0.09", "=D3-D7+D3*0.09", "公式: [指导价 - 残值 + 3年综合服务费]"),
        ("每月净租金 (元)", "=ROUND(B8/36, 2)", "=ROUND(C8/36, 2)", "=ROUND(D8/36, 2)", "公式: [租金总额 ÷ 36期]"),
        ("年行驶里程上限", "20,000 km", "15,000 km", "10,000 km", "超里程按 1.50元/km 结算"),
    ]

    for r_idx, (item, b_val, c_val, d_val, term) in enumerate(lease_data, start=3):
        ws3.cell(row=r_idx, column=1, value=item)
        ws3.cell(row=r_idx, column=2, value=b_val)
        ws3.cell(row=r_idx, column=3, value=c_val)
        ws3.cell(row=r_idx, column=4, value=d_val)
        ws3.cell(row=r_idx, column=5, value=term)
        if r_idx in [3, 5, 7, 8, 9]:
            for col in range(2, 5):
                ws3.cell(row=r_idx, column=col).number_format = "¥#,##0.00"
        elif r_idx in [4, 6]:
            for col in range(2, 5):
                ws3.cell(row=r_idx, column=col).number_format = "0.00%"

    for ws in [ws1, ws2, ws3]:
        for col_letter in ["A", "B", "C", "D", "E", "F"]:
            ws.column_dimensions[col_letter].width = 24

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_xiaomi_su7_ultra_excel(out_dir: Path) -> Path:
    """Generate complete Xiaomi SU7 Ultra technical specs & chassis breakdown."""
    file_path = out_dir / "Xiaomi_SU7_Ultra_Technical_Specs.xlsx"
    wb = openpyxl.Workbook()

    # Sheet 1: Ultra_量产版参数总览
    ws1 = wb.active
    ws1.title = "Ultra_量产版参数总览"
    ws1.merge_cells("A1:E1")
    ws1["A1"] = "小米 SU7 Ultra 量产版官方核心技术指标与原型车对比矩阵"
    ws1["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="800000", end_color="800000", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["系统分类", "技术参数项目", "SU7 Ultra 量产版", "SU7 Ultra 原型车 (PT)", "技术架构说明"]
    for col_idx, h in enumerate(headers, 1):
        c = ws1.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="A52A2A", end_color="A52A2A", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    # Group 1: 动力与赛道性能 (Rows 3-7 merged A3:A7)
    ws1.merge_cells("A3:A7")
    ws1["A3"] = "三电机动力总成"
    ws1["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws1["A3"].font = Font(name="Arial", bold=True)

    rows_g1 = [
        ("驱动形式与电机数量", "双 V8s + 单 V6s (三电机四驱)", "双 V8s + 单 V6s (三电机四驱)", "全栈自研高性能四驱架构"),
        ("整车最大综合马力/功率", "1548 PS / 1138 kW", "1548 PS / 1138 kW", "全球顶级超跑动力输出"),
        ("系统峰值扭矩", "1770 N·m", "1770 N·m", "起步瞬间爆发最大扭矩"),
        ("0-100 km/h 弹射加速", "1.98 秒 (不含起步时间)", "1.97 秒", "纽北官方实测量产四门车最速"),
        ("最高设计车速 (Top Speed)", "350 km/h", "350+ km/h", "电子限速解除下赛道极速"),
    ]
    for idx, (item, p1, p2, desc) in enumerate(rows_g1, start=3):
        ws1.cell(row=idx, column=2, value=item)
        ws1.cell(row=idx, column=3, value=p1)
        ws1.cell(row=idx, column=4, value=p2)
        ws1.cell(row=idx, column=5, value=desc)

    # Group 2: 纽北底盘与空气动力学 (Rows 8-12 merged A8:A12)
    ws1.merge_cells("A8:A12")
    ws1["A8"] = "底盘与空气动力学"
    ws1["A8"].alignment = Alignment(horizontal="center", vertical="center")
    ws1["A8"].font = Font(name="Arial", bold=True)

    rows_g2 = [
        ("减振器与悬挂系统", "Bilstein EVO T1 绞牙减振器", "赛用多向可调阻尼绞牙", "10挡阻尼及车身高度可调"),
        ("空气动力学下压力", "最大下压力 285 kg", "最大下压力 2145 kg", "量产版碳纤维固定大尾翼"),
        ("制动系统总成", "AP Racing 前6活塞 / 后4活塞 碳陶", "AP Racing 赛道竞技碳陶制动", "430mm前碳陶盘 最高耐受1300℃"),
        ("100-0 km/h 制动距离", "30.8 米", "25.0 米 (热熔胎)", "连续10次100-0制动无热衰减"),
        ("轮胎规格", "倍耐力 P ZERO 5 赛用配方", "倍耐力 P ZERO 赛用热熔光头胎", "前 265/35 R21, 后 305/30 R21"),
    ]
    for idx, (item, p1, p2, desc) in enumerate(rows_g2, start=8):
        ws1.cell(row=idx, column=2, value=item)
        ws1.cell(row=idx, column=3, value=p1)
        ws1.cell(row=idx, column=4, value=p2)
        ws1.cell(row=idx, column=5, value=desc)

    # Sheet 2: 三电机动力与电驱BOM
    ws2 = wb.create_sheet(title="三电机动力与电驱BOM")
    ws2.merge_cells("A1:F1")
    ws2["A1"] = "小米汽车自研超级电机 (HyperEngine V8s / V6s) 零部件级 BOM 明细"
    ws2["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws2["A1"].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers2 = ["BOM层级", "电机代号", "零部件名称", "核心规格参数", "材料与供应商", "设计寿命与质保"]
    for col_idx, h in enumerate(headers2, 1):
        c = ws2.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    bom_rows = [
        ("Level 1", "Rear-V8s-R", "后桥右侧超级电机总成", "425 kW / 578 PS, 27200 rpm", "小米自研 / 汇川联合定制", "8年或16万公里"),
        ("Level 2", "Rear-V8s-R", "960MPa特种超高强度硅钢转子", "最高机械屈服强度 960 MPa", "宝武特钢高牌号无取向硅钢", "设计转速冗余 32000 rpm"),
        ("Level 2", "Rear-V8s-R", "定转子全油冷双向散热系统", "双向立体油道, 定子温降30℃", "埃克森美孚特种绝缘传热油", "免维护终身油液"),
        ("Level 1", "Rear-V8s-L", "后桥左侧超级电机总成", "425 kW / 578 PS, 27200 rpm", "小米自研 / 汇川联合定制", "8年或16万公里"),
        ("Level 1", "Front-V6s", "前桥高性能永磁同步电机", "288 kW / 392 PS, 21000 rpm", "小米自研智能电驱", "8年或16万公里"),
        ("Level 1", "Inverter-SiC", "全栈 897V 碳化硅功率电控模块", "最高效率 99.85%, 1330kW放电", "科锐 Cree 第三代碳化硅芯片", "失效率 < 5 PPM"),
    ]
    for idx, r_data in enumerate(bom_rows, start=3):
        for c_idx, val in enumerate(r_data, start=1):
            ws2.cell(row=idx, column=c_idx, value=val)

    # Sheet 3: 纽北赛道底盘与空气动力学
    ws3 = wb.create_sheet(title="纽北赛道底盘与空气动力学")
    ws3.merge_cells("A1:D1")
    ws3["A1"] = "纽博格林北环赛道专用空气动力学与轻量化碳纤维套件清单"
    ws3["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws3["A1"].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers3 = ["碳纤维套件部位", "制造工艺与层数", "减重效果 (kg)", "下压力贡献 (kg @ 250km/h)"]
    for col_idx, h in enumerate(headers3, 1):
        c = ws3.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    aero_rows = [
        ("全碳纤维前唇与双风道气坝", "热压罐高压成型 (Autoclave 12层)", 14.5, 65.0),
        ("碳纤维侧裙与后轮扰流扩散板", "干碳抽真空导入树脂成型", 9.2, 38.0),
        ("固定式大碳纤维碳纤维尾翼", "高模量 T800 赛车级碳纤维", 12.0, 142.0),
        ("车尾主动后扩散器 (0-16°调节)", "电子伺服舵机一体化碳纤维", 8.8, 40.0),
        ("全碳纤维车顶轻量化一体盖板", "1.7 平方米超大单片干碳", 18.0, 0.0),
    ]
    for idx, r_data in enumerate(aero_rows, start=3):
        for c_idx, val in enumerate(r_data, start=1):
            ws3.cell(row=idx, column=c_idx, value=val)

    # Sheet 4: 购车权益与选装矩阵 with formulas
    ws4 = wb.create_sheet(title="购车权益与选装矩阵")
    ws4.merge_cells("A1:E1")
    ws4["A1"] = "小米 SU7 Ultra 官方售价与赛道选配包落地测算表"
    ws4["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws4["A1"].fill = PatternFill(start_color="800000", end_color="800000", fill_type="solid")
    ws4["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers4 = ["选配包类型", "选配项目描述", "官方零售价 (元)", "首发限时优惠 (元)", "净选装价 (元)"]
    for col_idx, h in enumerate(headers4, 1):
        c = ws4.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="A52A2A", end_color="A52A2A", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    opt_rows = [
        ("基础整车售价", "小米 SU7 Ultra 标配量产版", 814900, 0, "=C3-D3"),
        ("赛道竞技包", "Bilstein 绞牙避震 + 碳陶刹车盘 + 赛用刹车油", 68000, 10000, "=C4-D4"),
        ("极限碳纤维外观包", "碳纤维车顶 + 碳纤维尾翼 + 碳纤维前唇", 42000, 5000, "=C5-D5"),
        ("半热熔轮胎与锻造轮毂", "21寸赛道轻量化锻造轮毂 + 倍耐力定制胎", 26000, 3000, "=C6-D6"),
        ("座舱赛道翻毛皮内饰", "全车 Alcantara 翻毛皮包覆 + 黄色安全带", 18000, 2000, "=C7-D7"),
        ("总计全款购车裸车款", "含全部顶级赛道选装配置", "=SUM(C3:C7)", "=SUM(D3:D7)", "=SUM(E3:E7)"),
    ]
    for idx, (cat, desc, p_raw, disc, net_f) in enumerate(opt_rows, start=3):
        ws4.cell(row=idx, column=1, value=cat)
        ws4.cell(row=idx, column=2, value=desc)
        ws4.cell(row=idx, column=3, value=p_raw)
        ws4.cell(row=idx, column=4, value=disc)
        ws4.cell(row=idx, column=5, value=net_f)
        for c in range(3, 6):
            ws4.cell(row=idx, column=c).number_format = "¥#,##0"

    for ws in [ws1, ws2, ws3, ws4]:
        for col_letter in ["A", "B", "C", "D", "E", "F"]:
            ws.column_dimensions[col_letter].width = 25

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_huawei_tuling_bom_excel(out_dir: Path) -> Path:
    """Generate Tier-1 electric drive and Tuling chassis BOM table."""
    file_path = out_dir / "Huawei_Tuling_Chassis_BOM.xlsx"
    wb = openpyxl.Workbook()

    # Sheet 1: 电驱总成BOM清单
    ws1 = wb.active
    ws1.title = "电驱总成BOM清单"
    ws1.merge_cells("A1:F1")
    ws1["A1"] = "华为数字能源 DriveONE 智能高压电驱系统 Tier-1 供应链 BOM"
    ws1["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers1 = ["零件号 (Part No.)", "零件名称与规格", "Tier-1 供应商", "单车用量", "额定/峰值扭矩 (N·m)", "质保标准"]
    for col_idx, h in enumerate(headers1, 1):
        c = ws1.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="A52A2A", end_color="A52A2A", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    bom_data = [
        ("HW-ED-001-A", "前交流异步双合一电驱总成 (160kW)", "华为数字能源技术有限公司", 1, "300 N·m", "8年或16万公里"),
        ("HW-ED-002-B", "后永磁同步智能碳化硅电驱总成 (230kW)", "华为数字能源技术有限公司", 1, "396 N·m", "8年或16万公里"),
        ("HW-INV-800", "全液冷 SiC 高压逆变控制器 (800V)", "华为数字能源 / 斯达半导体", 2, "N/A", "10年或20万公里"),
        ("HW-BRK-004", "IPB 智能集成制动解耦系统 (One-box)", "博世汽车部件 (苏州) 有限公司", 1, "最大制动力矩 4500 N·m", "终身质保"),
        ("HW-STR-005", "双小齿轮电动助力转向系统 (DP-EPS)", "采埃孚恒隆转向系统有限公司", 1, "输出齿条推力 12.5 kN", "5年或10万公里"),
    ]
    for idx, r_data in enumerate(bom_data, start=3):
        for c_idx, val in enumerate(r_data, start=1):
            ws1.cell(row=idx, column=c_idx, value=val)

    # Sheet 2: 图灵底盘智能协同控制
    ws2 = wb.create_sheet(title="图灵底盘智能协同控制")
    ws2.merge_cells("A1:E1")
    ws2["A1"] = "华为途灵智能底盘 (Huawei Tuling Chassis) 多域协同控制规格表"
    ws2["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws2["A1"].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers2 = ["底盘控制子系统", "执行器硬件规格", "响应时延 (Latency)", "动态调节范围", "智能算法策略"]
    for col_idx, h in enumerate(headers2, 1):
        c = ws2.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    chassis_ctrl = [
        ("CDC 连续可变阻尼减振器", "采埃孚天合第二代内置电磁阀", "10 ms (每秒100次调节)", "阻尼力 200N - 3500N 连续无级", "路况预瞄感知前馈控制 (DATS)"),
        ("闭式双腔空气悬挂系统", "威巴克双腔空气弹簧 + 大流量压缩机", "150 ms 气腔切换", "车身高度 -30mm ~ +50mm", "高速下沉省电 / 越野自动抬升"),
        ("DATS 动态自适应扭矩系统", "华为电驱毫秒级矢量扭矩算法", "4 ms 电机扭矩调整", "前后扭矩 0:100 ~ 100:0 自由分配", "雨雪路面防滑 / 弯道车身姿态控制"),
        ("xMotion 智能车身协同控制", "图灵底盘中央超算控制器", "2 ms 域控总线通信", "六自由度姿态协同控制", "防俯冲抗点头 / 颠簸路面飞毯体验"),
    ]
    for idx, r_data in enumerate(chassis_ctrl, start=3):
        for c_idx, val in enumerate(r_data, start=1):
            ws2.cell(row=idx, column=c_idx, value=val)

    # Sheet 3: 供应商质量与维保承诺
    ws3 = wb.create_sheet(title="供应商质量与维保承诺")
    ws3.merge_cells("A1:E1")
    ws3["A1"] = "途灵底盘核心供应商质量 SLA 与召回保修考核基准"
    ws3["A1"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws3["A1"].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers3 = ["供应商名称", "供应模块", "MTBF 平均无故障时间", "失效率控制目标 (PPM)", "售后紧急响应时间"]
    for col_idx, h in enumerate(headers3, 1):
        c = ws3.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    sla_data = [
        ("华为数字能源", "DriveONE 电驱与 SiC 逆变器", "150,000 小时", "< 10 PPM", "全国 2小时内现场支持"),
        ("威巴克 Vibracoustic", "双腔空气弹簧总成", "120,000 小时", "< 25 PPM", "全国 4小时内响应"),
        ("采埃孚天合 ZF TRW", "CDC 电磁悬挂控制器", "140,000 小时", "< 15 PPM", "全国 4小时内响应"),
        ("拓普集团 TuPu Group", "前双叉臂与后五连杆全铝副车架", "200,000 小时", "< 5 PPM", "全国 8小时内备件到场"),
    ]
    for idx, r_data in enumerate(sla_data, start=3):
        for c_idx, val in enumerate(r_data, start=1):
            ws3.cell(row=idx, column=c_idx, value=val)

    for ws in [ws1, ws2, ws3]:
        for col_letter in ["A", "B", "C", "D", "E", "F"]:
            ws.column_dimensions[col_letter].width = 25

    wb.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# ══════════════════════════════════════════════════════════════════════════
# 2. WORD DOCUMENT GENERATORS
# ══════════════════════════════════════════════════════════════════════════


def generate_tesla_service_bulletin_word(out_dir: Path) -> Path:
    """Generate Tesla Model Y Recall & Service Bulletin with footnotes & legal disclaimer."""
    file_path = out_dir / "Tesla_Model_Y_Service_Bulletin.docx"
    doc = docx.Document()

    # Header and footer
    sec0 = doc.sections[0]
    sec0.header.paragraphs[0].text = "TESLA SERVICE BULLETIN • SAFETY RECALL NOTICE SB-24-00-001"
    sec0.footer.paragraphs[0].text = "Page 1 of 2 • Confidential & Proprietary Service Information"

    doc.add_paragraph("特斯拉 Model Y 转向机与扭矩传感器安全召回技术指导书", style="Title")
    doc.add_paragraph(
        "Tesla Safety Recall SB-24-00-001 | 适用车型: 特斯拉 Model Y (2022-2024款) | EPS转向助力与螺栓紧固",
        style="Subtitle",
    )

    doc.add_heading("1. 召回对象与受影响车辆 (Recall Subject & Affected Population)", level=1)
    doc.add_paragraph(
        "特斯拉汽车 (Tesla Motors) 确认部分 2022 至 2024 年款 Model Y 车辆在极端高湿与融雪盐腐蚀环境下，"
        "电动助力转向机 (EPS) 扭矩传感器线束接插件可能发生微振磨损氧化，导致转向助力受限并在仪表盘出现 UI_a020 警告。"
        "本次安全召回为所有受影响车辆免费检修线束密封并换装强化转向机固定螺栓。"
    )

    doc.add_paragraph(
        "【安全召回操作指令 (Safety Recall Mandate)】: 凡进入车间之召回批次车辆，必须首先使用诊断仪检测 EPS 扭矩传感器偏置。"
        "拆除转向机固定螺栓后严禁重复使用，必须更换全新达克罗涂层 10.9 级螺栓并按规范扭矩紧固！",
        style="Quote",
    )

    doc.add_heading("1.1 维修作业流程与关键紧固力矩标准", level=2)

    # Repair procedure table
    tbl = doc.add_table(rows=5, cols=4)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["维修步骤 (Step)", "作业流程规程 (Procedure)", "专用诊断检修工具", "标准紧固力矩规范 (Torque Spec)"]
    for c_idx, h in enumerate(headers):
        tbl.cell(0, c_idx).text = h

    step_data = [
        ("步骤 1: 故障诊断 (Diagnostic Scan)", "连接特斯拉 Toolbox 3 读取转向机故障码 EPS_f048，检测转向角传感器零位偏差与扭矩信号。", "Toolbox 3 诊断电脑 & CAN-FD 适配器", "N/A"),
        ("步骤 2: 线束检查 (Harness Check)", "拆卸前下护板，检查 12-pin EPS 扭矩传感器线束有无受潮氧化并喷涂绝缘密封胶。", "10mm 套筒与卡扣钳", "M6 护板螺栓: 9.0 ± 1.0 N·m"),
        ("步骤 3: 螺栓紧固更换 (Bolt Replacement)", "拆除并废弃原车转向机齿条固定螺栓；换装全新达克罗涂层 10.9 级高强度螺栓并执行角度扭矩拧紧。", "E-Torx E18 套筒与校准扭矩扳手", "M12×1.75 螺栓: 85 N·m + 45° 紧固力矩"),
        ("步骤 4: 转向标定与路试 (Calibration)", "执行 EPS 转向机扭矩偏置校准，进行 60km/h 道路试车验证回正力矩与动态标定。", "Toolbox 3 标定程序", "N/A"),
    ]
    for r_idx, (s, p, t, trq) in enumerate(step_data, start=1):
        tbl.cell(r_idx, 0).text = s
        tbl.cell(r_idx, 1).text = p
        tbl.cell(r_idx, 2).text = t
        tbl.cell(r_idx, 3).text = trq

    doc.add_heading("2. Warranty Claim Codes & Hazardous Scrap Disposal", level=1)
    doc.add_paragraph(
        "Service centers must register recall claims under Labor Operation Code 14013901 (Inspection & Harness Seal, 0.4 hrs) "
        "or 14013902 (Complete Steering Gear Replacement, 1.8 hrs). Replaced bolts must be condemned and marked as scrapped."
    )

    doc.add_paragraph(
        "*注1: Subject to NHTSA (US) and SAMR (China) regulatory motor vehicle safety recall compliance standards.",
        style="Normal",
    )
    doc.add_paragraph(
        "*注2: Replaced high-tensile steering fasteners must be scrapped in compliance with ISO 14001 environmental hazmat directives.",
        style="Normal",
    )

    # Save to buffer and inject OpenXML footnotes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    footnotes_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:footnote w:id="1">
    <w:p><w:r><w:t>Subject to NHTSA and SAMR regulatory recall compliance standards.</w:t></w:r></w:p>
  </w:footnote>
  <w:footnote w:id="2">
    <w:p><w:r><w:t>All replaced steering gear assembly bolts must be scrapped per hazardous waste protocols.</w:t></w:r></w:p>
  </w:footnote>
</w:footnotes>"""

    out_buf = io.BytesIO()
    with zipfile.ZipFile(buf, "r") as zin, zipfile.ZipFile(out_buf, "w") as zout:
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        zout.writestr("word/footnotes.xml", footnotes_xml)

    file_path.write_bytes(out_buf.getvalue())
    logger.info(f"Generated {file_path}")
    return file_path


def generate_nio_safety_manual_word(out_dir: Path) -> Path:
    """Generate NIO Power Swap 900V High-Voltage Safety Manual with H1-H4 headings & callouts."""
    file_path = out_dir / "NIO_Power_Swap_Safety_Manual.docx"
    doc = docx.Document()

    sec0 = doc.sections[0]
    sec0.header.paragraphs[0].text = "蔚来能源换电技术部 • 内部受控应急安全操作规范"
    sec0.footer.paragraphs[0].text = "文件编号: SOP-HV-900 • 第 1 页 共 2 页"

    doc.add_paragraph("蔚来第四代换电站高压电池应急处置与救援标准作业程序", style="Title")
    doc.add_paragraph("适用车型: NIO ET9 / ES8 / EC7 / ET7 / ES6 全系换电架构", style="Subtitle")

    doc.add_heading("1. 高压电气系统安全准则与个人防护装备 (PPE) 要求", level=1)
    doc.add_paragraph(
        "蔚来第四代换电站与 ET9 旗舰轿车全面部署全栈 900V 高压超充电气架构，直流高压母线工作电压最高可达 925V DC。"
        "所有站内专员与应急救援人员在接触换电机构或电池箱体前，必须严格穿戴符合国标认证的防电弧绝缘装备。"
    )

    doc.add_paragraph(
        "【危险警告 (DANGER)】: 换电站直流母线属于 Class 00 级超高压危险源！在断开整车高压与换电仓主电源前，"
        "严禁任何人员身体接触电池正负极快换接插件！现场作业必须由至少两名持国家特种电工操作证人员在场执行监护！",
        style="Quote",
    )

    doc.add_heading("1.1 换电机构电池自动解锁与落锁机械安全联锁", level=2)
    doc.add_paragraph(
        "第四代换电站采用全新高精度柔性电枪与 10 把自适应电芯加解锁机构。作业中若发生通信异常，"
        "联锁控制单元 (Interlock Control Unit) 将在 5 毫秒内切断 900V 继电器驱动信号，并锁定底盘机械卡扣。"
    )

    doc.add_heading("2. 动力电池热失控应急阻断与水淹救援规程", level=1)
    doc.add_paragraph(
        "当换电站仓内动力电池传感器监控到电芯热失控前兆时，应急处理流程立即由站端 AI 监控系统升级为自动消防联动状态。"
    )

    doc.add_heading("2.1 烟雾与温度预警阈值响应矩阵", level=2)

    # Response matrix table
    tbl = doc.add_table(rows=4, cols=4)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["预警等级", "传感器触发条件", "换电站自动化阻断响应", "现场专员与消防行动"]
    for c_idx, h in enumerate(headers):
        tbl.cell(0, c_idx).text = h

    matrix_data = [
        ("三级预警 (黄色关注)", "单体电芯温度 > 55℃, 气压正常", "暂停当前换电流程, 开启强制强冷风道", "监控站端遥测数据, 准备应急MSD断电"),
        ("二级预警 (橙色严重)", "单体温度 > 75℃, VOC传感器微量释放", "整车自动升起, 高压主回路毫秒级切断", "专员疏散站内车主至50米外安全区域"),
        ("一级预警 (红色紧急)", "温度 > 95℃ 或 CO/烟雾传感器连续报警", "自动水浸水箱系统开启, 自动注入冷却液", "立即拨打 119, 启动现场干粉与喷淋隔离"),
    ]
    for r_idx, (lvl, cond, auto_act, human_act) in enumerate(matrix_data, start=1):
        tbl.cell(r_idx, 0).text = lvl
        tbl.cell(r_idx, 1).text = cond
        tbl.cell(r_idx, 2).text = auto_act
        tbl.cell(r_idx, 3).text = human_act

    doc.add_heading("2.1.1 自动水浸水箱注入作业细则", level=3)
    doc.add_paragraph(
        "在红色一级预警触发后，换电站底层特种消防水箱在 30 秒内注入足量循环冷却水，"
        "淹没深度必须完全浸没电池包上盖 100mm 以上，确保持续散热阻断链式热失控。"
    )

    doc.add_heading("2.1.1.1 废液环保收集与中和处置", level=4)
    doc.add_paragraph(
        "浸没冷却后的电池废液含有微量氢氟酸与电解液分解物，严禁直接排入市政雨水管网。"
        "必须使用专用弱碱性中和吸收剂进行沉淀处理，并交由具备资质的危废处理单位清运。"
    )

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# ══════════════════════════════════════════════════════════════════════════
# 3. POWERPOINT GENERATORS
# ══════════════════════════════════════════════════════════════════════════


def generate_zeekr_001_fr_presentation(out_dir: Path) -> Path:
    """Generate Zeekr 001 FR Launch Pitch Deck with complex multi-column shapes & notes."""
    file_path = out_dir / "Zeekr_001_FR_Launch_Presentation.pptx"
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Title
    s1 = prs.slides.add_slide(blank_layout)
    tx_box = s1.shapes.add_textbox(PPT_Inches(1), PPT_Inches(1.5), PPT_Inches(8), PPT_Inches(2.5))
    tf = tx_box.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "极氪 001 FR 纯电猎装超跑 全球上市发布会"
    p1.font.size = PPT_Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = PPT_RGBColor(0x1F, 0x49, 0x7D)

    p2 = tf.add_paragraph()
    p2.text = "四电机分布式电驱 • 1300匹马力 • ZVC 矢量控制 • 车载卫星通信"
    p2.font.size = PPT_Pt(16)
    p2.font.color.rgb = PPT_RGBColor(0x59, 0x59, 0x59)

    s1.notes_slide.notes_text_frame.text = (
        "各位投资人与媒体朋友们好。今天我们隆重发布极氪001 FR。这不仅是一台拥有1300匹马力的性能怪兽，"
        "更是中国品牌首次在纯电猎装超跑领域实现对传统西方百万超跑的技术超越。"
    )

    # Slide 2: Quad Motor Architecture (Multi-column shapes)
    s2 = prs.slides.add_slide(blank_layout)
    title_box = s2.shapes.add_textbox(PPT_Inches(1), PPT_Inches(0.6), PPT_Inches(8), PPT_Inches(0.8))
    title_box.text_frame.text = "全球首发量产四电机分布式电驱架构 (Quad-Motor Electric Drive)"
    title_box.text_frame.paragraphs[0].font.size = PPT_Pt(20)
    title_box.text_frame.paragraphs[0].font.bold = True

    # Left Column (Front dual motor)
    left_box = s2.shapes.add_textbox(PPT_Inches(1), PPT_Inches(1.8), PPT_Inches(3.8), PPT_Inches(4.5))
    ltf = left_box.text_frame
    ltf.text = "前双电机平行布置总成"
    ltf.paragraphs[0].font.bold = True
    ltf.paragraphs[0].font.size = PPT_Pt(14)
    ltf.add_paragraph().text = "- 最大综合功率: 310 kW (422 PS)"
    ltf.add_paragraph().text = "- 双电机高度集成设计，同轴差速解耦"
    ltf.add_paragraph().text = "- 高强度转子碳纤维包覆技术，最高转速 21,000 rpm"
    ltf.add_paragraph().text = "- 紧凑布置不侵占前行李厢空间"

    # Right Column (Rear dual motor)
    right_box = s2.shapes.add_textbox(PPT_Inches(5.2), PPT_Inches(1.8), PPT_Inches(3.8), PPT_Inches(4.5))
    rtf = right_box.text_frame
    rtf.text = "后双电机碳纤维套筒总成"
    rtf.paragraphs[0].font.bold = True
    rtf.paragraphs[0].font.size = PPT_Pt(14)
    rtf.add_paragraph().text = "- 最大综合功率: 620 kW (843 PS)"
    rtf.add_paragraph().text = "- 行业首创高速碳纤维转子包裹套筒"
    rtf.add_paragraph().text = "- 双独立逆变电控，毫秒级独立分配单轮扭矩"
    rtf.add_paragraph().text = "- 配合全油冷散热，支持连续12次弹射不衰减"

    s2.notes_slide.notes_text_frame.text = (
        "在动力架构上，前后四电机协同输出总功率达到930kW，折合马力1300匹。"
        "得益于碳纤维转子包裹技术，电机转速突破两万转以上，保证后段加速依然源源不断。"
    )

    # Slide 3: ZVC Torque Vectoring
    s3 = prs.slides.add_slide(blank_layout)
    s3_title = s3.shapes.add_textbox(PPT_Inches(1), PPT_Inches(0.6), PPT_Inches(8), PPT_Inches(0.8))
    s3_title.text_frame.text = "ZVC 极氪扭矩矢量控制与坦克掉头系统"
    s3_title.text_frame.paragraphs[0].font.size = PPT_Pt(20)
    s3_title.text_frame.paragraphs[0].font.bold = True

    s3_content = s3.shapes.add_textbox(PPT_Inches(1), PPT_Inches(1.6), PPT_Inches(8), PPT_Inches(4.8))
    ctf = s3_content.text_frame
    ctf.text = "全场景四轮独立动力掌控技术"
    ctf.paragraphs[0].font.bold = True
    ctf.paragraphs[0].font.size = PPT_Pt(14)
    ctf.add_paragraph().text = "• 10毫秒级响应: 四电机实时监控各轮转速与滑移率，极限过弯时自动给外侧车轮输出正扭矩、内侧输出制动扭矩。"
    ctf.add_paragraph().text = "• 不挑路面的坦克掉头: 原地旋转掉头无需依赖湿滑沙石地面，在干燥柏油路面依然能够实现圆心精准自转。"
    ctf.add_paragraph().text = "• AP Racing 10活塞制动系统: 前10活塞定钳与Brembo碳陶打孔制动盘，百公里制动距离仅 33.4 米。"

    s3.notes_slide.notes_text_frame.text = (
        "ZVC系统让001 FR在赛道过弯极限横向G值达到 1.4G。坦克掉头功能展示了四电机正反转的精确控制能力。"
    )

    # Slide 4: Comparison Table
    s4 = prs.slides.add_slide(blank_layout)
    s4_title = s4.shapes.add_textbox(PPT_Inches(1), PPT_Inches(0.6), PPT_Inches(8), PPT_Inches(0.8))
    s4_title.text_frame.text = "性能旗舰参数横向对比矩阵 (Benchmark Comparison Matrix)"
    s4_title.text_frame.paragraphs[0].font.size = PPT_Pt(20)
    s4_title.text_frame.paragraphs[0].font.bold = True

    # Embedded table
    rows, cols = 5, 5
    left = PPT_Inches(0.8)
    top = PPT_Inches(1.8)
    width = PPT_Inches(8.4)
    height = PPT_Inches(3.8)
    table_shape = s4.shapes.add_table(rows, cols, left, top, width, height)
    tbl = table_shape.table

    table_data = [
        ["车型与版本", "综合马力/功率", "0-100km/h加速", "制动与底盘硬件", "官方售价 (万元)"],
        ["极氪 001 FR", "1300 PS / 930 kW", "2.02 秒", "KW绞牙避震 / 前10活塞碳陶", "76.90 万"],
        ["Tesla Model S Plaid", "1020 PS / 750 kW", "2.10 秒", "自适应空气悬架 / 普通铸铁盘", "82.89 万"],
        ["保时捷 Taycan Turbo S", "952 PS / 700 kW", "2.40 秒", "三腔空气悬架 / PCCB碳陶制动", "180.80 万"],
        ["仰望 U9", "1306 PS / 960 kW", "2.36 秒", "云辇-X全主动车身控制", "168.00 万"],
    ]

    for r_idx, row in enumerate(table_data):
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = val
            cell.text_frame.paragraphs[0].font.size = PPT_Pt(11)
            if r_idx == 0:
                cell.text_frame.paragraphs[0].font.bold = True
                cell.fill.solid()
                cell.fill.fore_color.rgb = PPT_RGBColor(0x1F, 0x49, 0x7D)
                cell.text_frame.paragraphs[0].font.color.rgb = PPT_RGBColor(0xFF, 0xFF, 0xFF)

    s4.notes_slide.notes_text_frame.text = (
        "横向对比Model S Plaid和Taycan Turbo S，极氪001 FR在马力、加速和硬件规格上全面占优，"
        "且官方售价仅为76.9万元，彰显了中国智能电动产业链的极强成本控制力与性能统治力。"
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_li_mega_battlecard_presentation(out_dir: Path) -> Path:
    """Generate Li Auto MEGA vs Denza D9 Sales Battlecard & Objection Handling Deck."""
    file_path = out_dir / "Li_Mega_vs_Denza_D9_Battlecard.pptx"
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Battlecard Cover
    s1 = prs.slides.add_slide(blank_layout)
    tx_box = s1.shapes.add_textbox(PPT_Inches(1), PPT_Inches(1.5), PPT_Inches(8), PPT_Inches(2.5))
    tf = tx_box.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "理想 MEGA 对决 腾势 D9 旗舰纯电 MPV 终端销售攻防战卡"
    p1.font.size = PPT_Pt(26)
    p1.font.bold = True
    p1.font.color.rgb = PPT_RGBColor(0x2F, 0x55, 0x97)

    p2 = tf.add_paragraph()
    p2.text = "核心产品力剖析 • 客户异议拆解 • 竞品抗性话术实战指南"
    p2.font.size = PPT_Pt(15)
    p2.font.color.rgb = PPT_RGBColor(0x59, 0x59, 0x59)

    s1.notes_slide.notes_text_frame.text = (
        "本战卡供全国零售专家使用。在面对同时考察腾势D9 EV和理想MEGA的高净值家庭客户时，"
        "重点围绕5C超充补能体验、水滴低风阻大空间以及全家安全最高标准进行破冰。"
    )

    # Slide 2: Comparison Matrix Table
    s2 = prs.slides.add_slide(blank_layout)
    title_box = s2.shapes.add_textbox(PPT_Inches(1), PPT_Inches(0.6), PPT_Inches(8), PPT_Inches(0.8))
    title_box.text_frame.text = "核心硬件与性能对比攻防矩阵 (Product Spec Matrix)"
    title_box.text_frame.paragraphs[0].font.size = PPT_Pt(20)
    title_box.text_frame.paragraphs[0].font.bold = True

    table_shape = s2.shapes.add_table(5, 4, PPT_Inches(0.8), PPT_Inches(1.6), PPT_Inches(8.4), PPT_Inches(4.2))
    tbl = table_shape.table

    matrix_rows = [
        ["对比产品维度", "理想 MEGA Ultra (52.98万)", "腾势 D9 EV 四驱旗舰 (46.58万)", "终端销售攻防话术提炼"],
        ["风阻系数 (Cd)", "0.215 Cd (全球量产MPV最低)", "0.30 Cd (传统方正MPV造型)", "高速百公里电耗降低18%，真实高速续航达成率更高"],
        ["高压快充架构", "800V 全栈架构 + 5C 麒麟电池", "800V 平台 + 双枪直流快充", "MEGA 12分钟充500公里，无需寻找双枪桩位且插拔繁琐"],
        ["三排乘坐空间", "三排腿部空间媲美宝马5系", "三排坐姿较低，腿部承托略逊", "MEGA让全家每一位成员（特别是长辈）都能长途舒适久坐"],
        ["高阶辅助驾驶", "双 Orin-X (508 TOPS) + 全场景NOA", "单 Orin-N (84 TOPS) 高速导航辅助", "城市无图领航辅助驾驶全量推送，接娃下班更轻松省心"],
    ]
    for r_idx, row in enumerate(matrix_rows):
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = val
            cell.text_frame.paragraphs[0].font.size = PPT_Pt(10)
            if r_idx == 0:
                cell.text_frame.paragraphs[0].font.bold = True
                cell.fill.solid()
                cell.fill.fore_color.rgb = PPT_RGBColor(0x2F, 0x55, 0x97)
                cell.text_frame.paragraphs[0].font.color.rgb = PPT_RGBColor(0xFF, 0xFF, 0xFF)

    s2.notes_slide.notes_text_frame.text = (
        "销售话术重点: 强调5C超充网络已进驻全国几乎所有核心高速服务区，"
        "带家人自驾长途上洗手间的时间即可完成充电，完全消除长途续航焦虑。"
    )

    # Slide 3: Objection Handling Cards
    s3 = prs.slides.add_slide(blank_layout)
    s3_title = s3.shapes.add_textbox(PPT_Inches(1), PPT_Inches(0.6), PPT_Inches(8), PPT_Inches(0.8))
    s3_title.text_frame.text = "外观设计与安全风评异议处理 (Design & Safety Objection)"
    s3_title.text_frame.paragraphs[0].font.size = PPT_Pt(20)
    s3_title.text_frame.paragraphs[0].font.bold = True

    # Card 1: Design
    c1 = s3.shapes.add_textbox(PPT_Inches(1), PPT_Inches(1.8), PPT_Inches(3.8), PPT_Inches(4.5))
    c1_tf = c1.text_frame
    c1_tf.text = "客户异议 1: '高铁外观造型太激进'"
    c1_tf.paragraphs[0].font.bold = True
    c1_tf.paragraphs[0].font.size = PPT_Pt(13)
    c1_tf.add_paragraph().text = "• 破冰认同: '李总，您对设计的品味很敏锐。MEGA初见确实颠覆认知。'"
    c1_tf.add_paragraph().text = "• 价值塑造: '但所有顶级工程都是功能定义形式。正是水滴流线造就了0.215Cd，不仅电耗极低，更让整车在侧风暴雨中行驶如同高铁般平稳。'"
    c1_tf.add_paragraph().text = "• 圈层归属: '目前提车的车主多是科技创始人与建筑设计师，在小区地库辨识度极高。'"

    # Card 2: Safety
    c2 = s3.shapes.add_textbox(PPT_Inches(5.2), PPT_Inches(1.8), PPT_Inches(3.8), PPT_Inches(4.5))
    c2_tf = c2.text_frame
    c2_tf.text = "客户异议 2: 'MPV第三排追尾安全性担忧'"
    c2_tf.paragraphs[0].font.bold = True
    c2_tf.paragraphs[0].font.size = PPT_Pt(13)
    c2_tf.add_paragraph().text = "• 事实举证: 'MEGA拥有全球最高标准的MPV后碰撞安全体系。'"
    c2_tf.add_paragraph().text = "• 硬件参数: '后防撞梁距第三排座椅靠背高达800mm缓冲溃缩区，采用一体化压铸铝合金后地板。'"
    c2_tf.add_paragraph().text = "• 极限碰撞测试: '在88km/h高速追尾测试中，第三排乘员生存空间毫发无损，中保研3G+全优评级。'"

    s3.notes_slide.notes_text_frame.text = (
        "异议处理三部曲: 倾听认同 -> 用坚实数据与安全认证建立信任 -> 引导客户带全家进行深度试驾。"
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# ══════════════════════════════════════════════════════════════════════════
# 4. IMAGE GENERATORS WITH EXIF METADATA
# ══════════════════════════════════════════════════════════════════════════


def generate_xiaomi_v800_infographic_png(out_dir: Path) -> Path:
    """Generate high-resolution Xiaomi V8s/V800 motor technical spec infographic poster with EXIF."""
    file_path = out_dir / "Xiaomi_V800_Motor_Infographic.png"
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(15, 23, 42))  # Slate 900
    draw = ImageDraw.Draw(img)

    # Accent decorative borders
    draw.rectangle([40, 40, w - 40, h - 40], outline=(59, 130, 246), width=3)  # Blue border
    draw.rectangle([50, 50, w - 50, 150], fill=(30, 41, 59))

    # Try default or truetype font
    font_title = None
    font_large = None
    font_sub = None
    cjk_font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for p in cjk_font_paths:
        if os.path.exists(p):
            try:
                font_title = ImageFont.truetype(p, 42)
                font_large = ImageFont.truetype(p, 32)
                font_sub = ImageFont.truetype(p, 24)
                break
            except Exception:
                pass

    draw.text((80, 75), "小米超级电机 V8s / V800 核心技术规格参数总览", fill=(255, 255, 255), font=font_title)

    specs = [
        ("最高转速 (Max RPM)", "27,200 rpm (全球量产转速天花板)"),
        ("最大综合马力 (Horsepower)", "578 PS / 425 kW 超大功率输出"),
        ("系统峰值扭矩 (Peak Torque)", "635 N·m 强劲轮端扭矩"),
        ("功率密度 (Power Density)", "10.14 kW/kg 紧凑高密度集成"),
        ("电气架构平台电压", "960V SiC 超高压碳化硅平台"),
        ("电机综合工况效率", "98.11% 超高工况转换效率"),
        ("特种硅钢屈服强度", "960 MPa 超高强度特种硅钢转子"),
        ("冷却散热技术", "定转子全油冷双向立体散热回路"),
    ]

    for idx, (label, val) in enumerate(specs):
        col = idx // 4
        row = idx % 4
        x = 100 + col * 880
        y = 220 + row * 180

        # Background card
        draw.rectangle([x, y, x + 820, y + 140], fill=(30, 41, 59), outline=(71, 85, 105), width=2)
        draw.text((x + 30, y + 25), f"• {label}:", fill=(147, 197, 253), font=font_sub)
        draw.text((x + 30, y + 70), val, fill=(241, 245, 249), font=font_large)

    # Set EXIF
    exif = img.getexif()
    exif[0x010F] = "Xiaomi Motors Co., Ltd."  # Make
    exif[0x0110] = "Xiaomi V8s HyperEngine SpecCam"  # Model
    exif[0x0132] = "2026:03:01 10:00:00"  # DateTime
    exif[0x010E] = "Xiaomi V800 Motor High-Resolution Technical Specification Poster"  # ImageDescription

    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_instrument_cluster_warning_jpg(out_dir: Path) -> Path:
    """Generate diagnostic instrument cluster photo with TPMS & BMS alert & EXIF."""
    file_path = out_dir / "Instrument_Cluster_Warning.jpg"
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), color=(10, 10, 15))  # Deep night dashboard
    draw = ImageDraw.Draw(img)

    # Dashboard bezel
    draw.rectangle([30, 30, w - 30, h - 30], outline=(40, 50, 70), width=4)

    # Dial rings
    draw.ellipse([80, 120, 420, 460], outline=(70, 80, 100), width=3)
    draw.ellipse([860, 120, 1200, 460], outline=(70, 80, 100), width=3)

    # Warning alert box in center
    draw.rectangle([440, 140, 840, 480], fill=(25, 25, 35), outline=(220, 38, 38), width=3)

    # Warning icon
    draw.polygon([(640, 170), (600, 230), (680, 230)], fill=(220, 38, 38))
    draw.text((636, 185), "!", fill=(255, 255, 255))

    font_title = None
    font_body = None
    cjk_font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for p in cjk_font_paths:
        if os.path.exists(p):
            try:
                font_title = ImageFont.truetype(p, 22)
                font_body = ImageFont.truetype(p, 18)
                break
            except Exception:
                pass

    draw.text((480, 250), "胎压监测报警 (TPMS Alert)", fill=(239, 68, 68), font=font_title)
    draw.text((470, 290), "左前轮气压过低: 1.6 bar (标准 2.5 bar)", fill=(248, 113, 113), font=font_body)
    draw.text((470, 330), "右前轮: 2.5 bar | 左后轮: 2.5 bar", fill=(203, 213, 225), font=font_body)
    draw.text((470, 370), "高压电池警告: 动力系统受限 请尽快检修", fill=(251, 191, 36), font=font_body)

    # Speedometer and battery
    draw.text((210, 270), "0", fill=(255, 255, 255), font=font_title)
    draw.text((195, 310), "km/h", fill=(148, 163, 184), font=font_body)
    draw.text((1000, 270), "78%", fill=(52, 211, 153), font=font_title)
    draw.text((980, 310), "续航 546 km", fill=(148, 163, 184), font=font_body)

    # Footer metrics
    draw.text((100, 600), "累计里程: 12,480 km | 挡位: P | 室外温度: -8℃ | 车辆状态: 故障诊断中", fill=(148, 163, 184), font=font_body)

    # EXIF
    exif = img.getexif()
    exif[0x010F] = "Sony"  # Make
    exif[0x0110] = "ILCE-7RM5"  # Model
    exif[0x0132] = "2026:02:15 14:22:18"  # DateTime
    exif[0x010E] = "Instrument Cluster Low Tire Pressure & BMS Warning Diagnostic Capture"

    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# ══════════════════════════════════════════════════════════════════════════
# 5. MULTI-PAGE PDF GENERATOR WITH CONTINUOUS TABLES
# ══════════════════════════════════════════════════════════════════════════


def generate_avatr_12_pdf(out_dir: Path) -> Path:
    """Generate official multi-page spec manual with continuous tables, borderless grids, and headers."""
    file_path = out_dir / "Avatr_12_Full_Spec_Manual.pdf"
    doc = fitz.open()

    # Font setup
    cjk_font_file = None
    for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
        if os.path.exists(p):
            cjk_font_file = p
            break

    # Helper function for drawing headers/footers
    def add_page_decorations(page, page_num, total_pages=4):
        if cjk_font_file:
            page.insert_font(fontname="cjk", fontfile=cjk_font_file)
            fn = "cjk"
        else:
            fn = "china-s"
        # Header
        page.insert_text((50, 40), "AVATR 12 OFFICIAL TECHNICAL SPECIFICATION MANUAL • CHN PLATFORM", fontname=fn, fontsize=9, color=(0.4, 0.4, 0.5))
        page.draw_line(fitz.Point(50, 48), fitz.Point(545, 48), color=(0.8, 0.8, 0.85), width=0.8)
        # Footer
        page.draw_line(fitz.Point(50, 800), fitz.Point(545, 800), color=(0.8, 0.8, 0.85), width=0.8)
        page.insert_text((50, 815), f"Page {page_num} of {total_pages} • 阿维塔科技 (重庆) 有限公司 • 受控技术文件", fontname=fn, fontsize=9, color=(0.4, 0.4, 0.5))
        return fn

    # Page 1: Overview and Trim Matrix Table
    p1 = doc.new_page(width=595, height=842)
    fn = add_page_decorations(p1, 1)

    p1.insert_text((50, 80), "阿维塔 12 豪华未来智能轿跑 官方全配置规格手册", fontname=fn, fontsize=16, color=(0.1, 0.2, 0.4))
    p1.insert_text((50, 105), "CHN 架构赋能 (长安汽车 • 华为乾崑智驾 • 宁德时代电池) | 官方指导价格与车型矩阵", fontname=fn, fontsize=10, color=(0.3, 0.3, 0.3))

    # Table 1: Trim overview
    p1.draw_rect(fitz.Rect(50, 130, 545, 310), color=(0.2, 0.3, 0.6), width=1.0)
    # Header fill
    p1.draw_rect(fitz.Rect(50, 130, 545, 160), fill=(0.2, 0.3, 0.6))
    p1.insert_text((58, 150), "车型配置版本", fontname=fn, fontsize=10, color=(1, 1, 1))
    p1.insert_text((180, 150), "动力与驱动形式", fontname=fn, fontsize=10, color=(1, 1, 1))
    p1.insert_text((290, 150), "CLTC纯电续航", fontname=fn, fontsize=10, color=(1, 1, 1))
    p1.insert_text((380, 150), "智驾硬件方案", fontname=fn, fontsize=10, color=(1, 1, 1))
    p1.insert_text((475, 150), "官方指导价", fontname=fn, fontsize=10, color=(1, 1, 1))

    trim_rows = [
        ("700 三激光后驱奢享版", "后驱单电机 (230kW)", "700 km", "3颗激光雷达 + ADS 3.0", "30.08 万元"),
        ("650 三激光四驱性能版", "双电机四驱 (425kW)", "650 km", "3颗激光雷达 + ADS 3.0", "34.08 万元"),
        ("650 三激光四驱GT版", "双电机四驱 (425kW)", "650 km", "空气悬架 + 智能电动尾翼", "40.08 万元"),
        ("700 增程版 MAX (增程)", "后驱电驱 + 昆仑增程", "综合 1155 km", "单激光雷达 + ADS 3.0", "26.99 万元"),
        ("650 皇家剧院定制版", "双电机四驱顶配", "650 km", "双色车身 + 英国之宝音响", "42.08 万元"),
    ]
    for idx, (t, pwr, rng, adas, price) in enumerate(trim_rows):
        y = 185 + idx * 28
        p1.draw_line(fitz.Point(50, y - 18), fitz.Point(545, y - 18), color=(0.85, 0.85, 0.85), width=0.5)
        p1.insert_text((58, y), t, fontname=fn, fontsize=9, color=(0.1, 0.1, 0.1))
        p1.insert_text((180, y), pwr, fontname=fn, fontsize=9, color=(0.2, 0.2, 0.2))
        p1.insert_text((290, y), rng, fontname=fn, fontsize=9, color=(0.2, 0.2, 0.2))
        p1.insert_text((380, y), adas, fontname=fn, fontsize=8.5, color=(0.2, 0.2, 0.2))
        p1.insert_text((475, y), price, fontname=fn, fontsize=9, color=(0.8, 0.1, 0.1))

    # Page 2: Continuous Table Part 1 (Chassis & Battery)
    p2 = doc.new_page(width=595, height=842)
    add_page_decorations(p2, 2)
    p2.insert_text((50, 75), "阿维塔 12 机械底盘与三电核心规格表 (Part 1 跨页连续表格)", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))

    # Borderless continuous table header
    p2.draw_rect(fitz.Rect(50, 95, 545, 125), fill=(0.15, 0.35, 0.6))
    p2.insert_text((60, 115), "系统架构分类", fontname=fn, fontsize=10, color=(1, 1, 1))
    p2.insert_text((170, 115), "关键技术项目", fontname=fn, fontsize=10, color=(1, 1, 1))
    p2.insert_text((300, 115), "技术参数指标", fontname=fn, fontsize=10, color=(1, 1, 1))
    p2.insert_text((430, 115), "技术特性与说明", fontname=fn, fontsize=10, color=(1, 1, 1))

    cont_rows_p1 = [
        ("车身尺寸与轴距", "长 × 宽 × 高", "5020 mm × 1999 mm × 1460 mm", "中大型豪华运动轿跑比例"),
        ("车身尺寸与轴距", "轴距 (Wheelbase)", "3020 mm 超长轴距", "短前悬长轴距座舱布局"),
        ("底盘悬挂总成", "前悬架型式", "全铝合金双叉臂独立悬架", "虚拟主销结构, 提升转向手感"),
        ("底盘悬挂总成", "后悬架型式", "多连杆独立后悬架 (铝合金副车架)", "高刚度衬套过滤路面碎震"),
        ("动力电池包型式", "电池电芯类型", "宁德时代高能量密度三元锂电池", "CTP高集成度电池无模组技术"),
        ("动力电池包型式", "标称电池容量", "94.5 kWh 大容量电池包", "支持 800V 高压超充平台"),
        ("充电速度与补能", "超充最大功率", "最高充电功率可达 240 kW", "充电10分钟增加续航 200 km"),
        ("整备质量与配重", "整备质量 / 轴荷比", "2300 kg (前48: 后52前后平衡)", "重心高度仅 485 mm"),
    ]
    for idx, (c1, c2, c3, c4) in enumerate(cont_rows_p1):
        y = 150 + idx * 36
        p2.draw_line(fitz.Point(50, y - 24), fitz.Point(545, y - 24), color=(0.88, 0.88, 0.88), width=0.5)
        p2.insert_text((60, y), c1, fontname=fn, fontsize=9, color=(0.1, 0.1, 0.1))
        p2.insert_text((170, y), c2, fontname=fn, fontsize=9, color=(0.2, 0.2, 0.2))
        p2.insert_text((300, y), c3, fontname=fn, fontsize=9, color=(0.2, 0.2, 0.2))
        p2.insert_text((430, y), c4, fontname=fn, fontsize=8.5, color=(0.3, 0.3, 0.3))

    # Page 3: Continuous Table Part 2 Continued (Matching column structure)
    p3 = doc.new_page(width=595, height=842)
    add_page_decorations(p3, 3)
    p3.insert_text((50, 75), "阿维塔 12 机械底盘与三电核心规格表 (Part 2 接上页跨页拼接)", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))

    # Matching continuous table header
    p3.draw_rect(fitz.Rect(50, 95, 545, 125), fill=(0.15, 0.35, 0.6))
    p3.insert_text((60, 115), "系统架构分类", fontname=fn, fontsize=10, color=(1, 1, 1))
    p3.insert_text((170, 115), "关键技术项目", fontname=fn, fontsize=10, color=(1, 1, 1))
    p3.insert_text((300, 115), "技术参数指标", fontname=fn, fontsize=10, color=(1, 1, 1))
    p3.insert_text((430, 115), "技术特性与说明", fontname=fn, fontsize=10, color=(1, 1, 1))

    cont_rows_p2 = [
        ("电驱系统总成", "前桥电机最大功率", "195 kW 交流异步电驱", "华为 DriveONE 高效智能电驱"),
        ("电驱系统总成", "后桥电机最大功率", "230 kW 永磁同步电驱", "碳化硅功率模块 综合效率 92%"),
        ("综合动力性能", "系统综合最大扭矩", "650 N·m 峰值轮端扭矩", "0-100 km/h 官方加速 3.9 秒"),
        ("制动系统总成", "前制动盘规格与定钳", "Brembo 四活塞铝合金固定卡钳", "100-0 km/h 制动距离 35.0 米"),
        ("能耗与节能指标", "CLTC 百公里综合能耗", "15.8 kWh / 100km", "热泵空调系统 -30℃ 高效制热"),
        ("主动空气动力学", "智能电动升降尾翼", "车速达 90km/h 自动升起", "增加车尾下压力 45 kg"),
    ]
    for idx, (c1, c2, c3, c4) in enumerate(cont_rows_p2):
        y = 150 + idx * 36
        p3.draw_line(fitz.Point(50, y - 24), fitz.Point(545, y - 24), color=(0.88, 0.88, 0.88), width=0.5)
        p3.insert_text((60, y), c1, fontname=fn, fontsize=9, color=(0.1, 0.1, 0.1))
        p3.insert_text((170, y), c2, fontname=fn, fontsize=9, color=(0.2, 0.2, 0.2))
        p3.insert_text((300, y), c3, fontname=fn, fontsize=9, color=(0.2, 0.2, 0.2))
        p3.insert_text((430, y), c4, fontname=fn, fontsize=8.5, color=(0.3, 0.3, 0.3))

    # Page 4: Borderless Grids for Huawei ADS 3.0 Sensors & Cockpit
    p4 = doc.new_page(width=595, height=842)
    add_page_decorations(p4, 4)
    p4.insert_text((50, 75), "阿维塔 12 华为全栈智驾 ADS 3.0 与 HarmonyOS 智能座舱硬件清单 (无边框网格)", fontname=fn, fontsize=13, color=(0.1, 0.2, 0.4))

    # Borderless grid: no vertical/horizontal table borders, clean spatial reading alignment
    sensor_grid = [
        ("激光雷达 (Lidar)", "3 颗 96线高精激光雷达", "前向 + 左右侧向 300° 超强感知视野"),
        ("毫米波雷达 (MMW)", "3 颗远距高精毫米波雷达", "穿透雨雪大雾，探测距离 250 米"),
        ("超声波雷达 (USS)", "12 颗精准超声波传感器", "近距离泊车测距，厘米级避障精度"),
        ("高清摄像头群 (Cameras)", "11 颗高清感知摄像头", "前向双目800万 + 4个环视 + 4个侧视"),
        ("智驾计算平台 (MDC)", "华为 MDC 810 算力平台", "400 TOPS 稠密算力，端到端大模型"),
        ("智能座舱系统 (Cockpit)", "HarmonyOS 4.0 智能座舱", "35.4 英寸一体远端全景 4K 宽屏"),
        ("电子外后视镜 (CMS)", "高动态流媒体电子外后视镜", "夜视增强，彻底消除雨雪遮挡盲区"),
    ]
    p4.insert_text((50, 110), "感知传感器硬件规格 (无边框对齐网格):", fontname=fn, fontsize=11, color=(0.15, 0.35, 0.6))

    for idx, (part, spec, note) in enumerate(sensor_grid):
        y = 140 + idx * 34
        p4.insert_text((60, y), part, fontname=fn, fontsize=9.5, color=(0.1, 0.2, 0.3))
        p4.insert_text((220, y), spec, fontname=fn, fontsize=9.5, color=(0.2, 0.2, 0.2))
        p4.insert_text((390, y), note, fontname=fn, fontsize=8.5, color=(0.4, 0.4, 0.4))

    doc.save(str(file_path))
    logger.info(f"Generated {file_path}")
    return file_path


# ══════════════════════════════════════════════════════════════════════════
# 6. CSV / TSV / JSON / TOML / MARKDOWN GENERATORS
# ══════════════════════════════════════════════════════════════════════════


def generate_catl_thermal_test_csv(out_dir: Path) -> Path:
    """Generate real-world battery thermal runaway test sensor logs (60+ rows)."""
    file_path = out_dir / "CATL_Qilin_Battery_Thermal_Test.csv"
    lines = [
        "time_s,cell_id,cell_temp_c,pack_temp_c,coolant_temp_c,voltage_v,current_a,resistance_mohm,coolant_flow_l_min,soc_pct,pressure_kpa,status_flag,status_zh"
    ]

    for t in range(0, 65):
        # Realistic thermal escalation profile
        if t < 20:
            status = "NORMAL_DISCHARGE"
            status_zh = "正常放电运行"
            temp = 25.0 + t * 0.4
            volt = 3.90 - t * 0.005
            curr = 85.0
            p_kpa = 101.3
            coolant = 22.0
            flow = 5.0
        elif t < 40:
            status = "THERMAL_WARNING"
            status_zh = "动力电池热失控预警升温"
            temp = 33.0 + (t - 20) * 1.5
            volt = 3.80 - (t - 20) * 0.015
            curr = 150.0
            p_kpa = 102.5 + (t - 20) * 0.8
            coolant = 24.0 + (t - 20) * 0.5
            flow = 12.0
        else:
            status = "SUPPRESSION_ACTIVE"
            status_zh = "强冷循环启动热失控抑制"
            temp = 63.0 - (t - 40) * 0.8
            volt = 3.50 - (t - 40) * 0.01
            curr = 0.0  # cut off
            p_kpa = 118.5 - (t - 40) * 0.4
            coolant = 18.0 - (t - 40) * 0.2
            flow = 25.0

        line = f"{t},CATL-QILIN-CELL-08,{temp:.1f},{temp+1.8:.1f},{coolant:.1f},{volt:.3f},{curr:.1f},0.28,{flow:.1f},{max(10, 85-t):.1f},{p_kpa:.1f},{status},{status_zh}"
        lines.append(line)

    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


def generate_ev_subsidy_policy_json(out_dir: Path) -> Path:
    """Generate comprehensive 2026 EV subsidy policies & vehicle database export."""
    file_path = out_dir / "National_EV_Subsidy_Policy_2026.json"
    data = {
        "policy_metadata": {
            "title": "2026年度新能源汽车减免车辆购置税与以旧换新置换补贴细则",
            "issuing_bodies": ["工业和信息化部", "财政部", "国家税务总局", "商务部"],
            "effective_date": "2026-01-01",
            "expiration_date": "2027-12-31",
            "version": "GB-2026-EV-TAX-01",
        },
        "technical_eligibility_criteria": {
            "pure_electric_battery_density_wh_kg": 140.0,
            "pure_electric_cltc_min_range_km": 200,
            "phev_pure_electric_min_range_km": 50,
            "max_purchase_tax_exemption_per_vehicle_cny": 30000,
        },
        "vehicle_database": [
            {
                "model_name": "小米 SU7 Max",
                "brand": "小米汽车",
                "powertrain_type": "纯电动 (BEV)",
                "msrp_cny": 299900,
                "battery_capacity_kwh": 101.0,
                "cltc_range_km": 800,
                "tax_exemption_amount_cny": 26540,
                "trade_in_national_subsidy_cny": 15000,
                "final_estimated_net_cost_cny": 284900,
            },
            {
                "model_name": "极氪 001 FR",
                "brand": "极氪汽车",
                "powertrain_type": "纯电动 (BEV)",
                "msrp_cny": 769000,
                "battery_capacity_kwh": 100.0,
                "cltc_range_km": 550,
                "tax_exemption_amount_cny": 30000,
                "trade_in_national_subsidy_cny": 15000,
                "final_estimated_net_cost_cny": 754000,
            },
            {
                "model_name": "比亚迪 汉 EV 荣耀版",
                "brand": "比亚迪",
                "powertrain_type": "纯电动 (BEV)",
                "msrp_cny": 249800,
                "battery_capacity_kwh": 85.4,
                "cltc_range_km": 715,
                "tax_exemption_amount_cny": 22106,
                "trade_in_national_subsidy_cny": 15000,
                "final_estimated_net_cost_cny": 234800,
            },
            {
                "model_name": "理想 MEGA Ultra",
                "brand": "理想汽车",
                "powertrain_type": "纯电动 (BEV)",
                "msrp_cny": 529800,
                "battery_capacity_kwh": 102.7,
                "cltc_range_km": 710,
                "tax_exemption_amount_cny": 30000,
                "trade_in_national_subsidy_cny": 15000,
                "final_estimated_net_cost_cny": 514800,
            },
            {
                "model_name": "阿维塔 12 四驱性能版",
                "brand": "阿维塔",
                "powertrain_type": "纯电动 (BEV)",
                "msrp_cny": 340800,
                "battery_capacity_kwh": 94.5,
                "cltc_range_km": 650,
                "tax_exemption_amount_cny": 30000,
                "trade_in_national_subsidy_cny": 15000,
                "final_estimated_net_cost_cny": 325800,
            },
        ],
    }
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


def generate_zeekr_warranty_terms_md(out_dir: Path) -> Path:
    """Generate Zeekr Battery Warranty Terms markdown document with tables."""
    file_path = out_dir / "Zeekr_Battery_Warranty_Terms.md"
    content = """# 极氪汽车动力蓄电池终身质保权益细则与保修条款 (Zeekr Battery Warranty)

文件编号: ZKR-QA-BAT-2026 | 生效日期: 2026年1月1日 | 适用对象: 极氪首任车主 (非营运)

## 1. 终身质保范围与电芯衰减衰减承诺

极氪汽车对首任非营运车主提供动力蓄电池电芯终身质保服务。在正常使用和维护保养条件下，极氪承诺如下质保指标：

| 动力电池类型 | 质保考核周期 | 衰减率判定阈值 | 厂商保障承诺 |
| --- | --- | --- | --- |
| 威睿 800V 金砖磷酸铁锂电池 | 首任车主终身 | 容量衰减 > 30% | 免费维修或更换性能相当电池包 |
| 宁德时代 800V 麒麟三元锂电池 | 首任车主终身 | 容量衰减 > 30% | 免费维修或更换性能相当电池包 |
| 极氪 001 FR 赛道高倍率电池 | 8年或16万公里 | 容量衰减 > 20% | 赛道级原厂电芯配平与模组焕新 |

## 2. 免责与权益失效情形

车主出现以下任一情形时，动力蓄电池终身质保权益将自动终止转为国家法定的8年或12万公里保修：

1. 车辆所有权发生变更（过户转让给他人或单位）。
2. 车辆用于出租、网约车、营运运输等商业经营用途。
3. 未在极氪官方授权服务中心进行事故维修或使用非原厂涉电零部件。
4. 动力电池包因涉水浸泡、底盘剧烈磕碰变形或私自篡改BMS固件。

> **特别提示**: 车辆长途涉水深度超过 300mm 或底盘遭受硬物刮擦撞击后，必须在 48小时内到极氪服务中心进行举升检查。
"""
    file_path.write_text(content, encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


def generate_bosch_esp_config_toml(out_dir: Path) -> Path:
    """Generate Bosch ESP/iBooster stability program parameter definitions in TOML."""
    file_path = out_dir / "Bosch_ESP_Firmware_Config.toml"
    content = """# Bosch ESP 9.3 & iBooster 2.0 Vehicle Dynamics Firmware Parameter Table

[system_metadata]
firmware_version = "v9.3.4-prod-2026"
release_date = "2026-02-01"
calibrator = "Bosch Automotive Chassis Systems Co., Ltd."
vehicle_platform = "AutoVend 800V Performance EV"

[traction_control]
slip_threshold_pct = 8.5
understeer_yaw_gain = 1.45
oversteer_yaw_gain = 1.85
traction_mode = "DYNAMIC_TRACK"
response_latency_ms = 8

[regenerative_braking]
max_regen_decel_g = 0.35
one_pedal_stop_distance_m = 1.2
blend_hydraulic_cutoff_kmh = 3.5
pedal_feel_mapping = "COMFORT_SPORT_ADAPTIVE"

[stability_safety_limits]
lateral_acceleration_threshold_g = 1.35
roll_over_prevention_active = true
trailer_stabilization_enabled = true
emergency_brake_assist_boost = 180.0
"""
    file_path.write_text(content, encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


def generate_powertrain_efficiency_tsv(out_dir: Path) -> Path:
    """Generate TSV motor efficiency map (RPM vs Torque vs Efficiency)."""
    file_path = out_dir / "Powertrain_Efficiency_Matrix.tsv"
    lines = ["motor_rpm\ttorque_nm\tefficiency_pct\tstator_temp_c\tinverter_loss_w"]

    rpms = [1000, 3000, 6000, 9000, 12000, 15000, 18000, 21000, 24000, 27200]
    torques = [50, 150, 300, 450, 635]

    for rpm in rpms:
        for tq in torques:
            # Efficiency peak around 6000-12000 rpm and mid-high torque
            eff = 98.11 - abs(rpm - 9000) / 2000.0 - abs(tq - 300) / 100.0
            eff = max(88.0, min(98.11, eff))
            temp = 45.0 + rpm / 400.0 + tq / 20.0
            loss = (rpm * tq / 9550.0) * (1.0 - eff / 100.0) * 1000.0
            lines.append(f"{rpm}\t{tq}\t{eff:.2f}\t{temp:.1f}\t{loss:.1f}")

    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


def generate_xpeng_xngp_json(out_dir: Path) -> Path:
    """Generate XPeng XNGP Autonomous Driving & Perception Neural Architecture Matrix."""
    file_path = out_dir / "XPeng_XNGP_Autonomous_Driving_Matrix.json"
    data = {
        "title": "小鹏汽车 XNGP 全场景智能辅助驾驶技术规格矩阵",
        "system_version": "AI天玑系统 5.4.0",
        "hardware_platform": {
            "main_compute_chip": "NVIDIA DRIVE Orin-X x 2 (508 TOPS) / 自研图灵AI芯片 (40 TOPS专用端到端NPU)",
            "camera_suite": "11 颗高清视觉感知摄像头 (含双目800万前视 + 4颗300万环视 + 4颗侧视)",
            "radar_sensors": "2 颗超清前向激光雷达 (96线/126线) + 5 颗毫米波雷达 + 12 颗超声波雷达",
            "perception_latency_ms": {
                "vision_stream_pipeline": 38.5,
                "lidar_pointcloud_pipeline": 12.2,
                "fusion_decision_cycle": 10.0,
            },
        },
        "neural_networks": [
            {
                "module_name": "XNet 2.0 深度视觉神经网络",
                "architecture": "时空联合Transformer (Spatial-Temporal Transformer) + 动态BEV网格",
                "dynamic_perception_distance_m": 200,
                "static_occupancy_grid_resolution_cm": 15,
                "inference_frequency_hz": 30,
            },
            {
                "module_name": "XPlanner 端到端决策大模型",
                "architecture": "强化学习与轨迹树搜索 (RL + MCTS) 模拟人类驾驶博弈行为",
                "trajectory_replan_frequency_ms": 100,
                "unprotected_left_turn_success_rate": 0.985,
            },
        ],
        "functional_matrix": [
            {
                "function_code": "CITY_NGP_URBAN",
                "feature_name": "城市全场景自动导航辅助驾驶",
                "available_cities_count": 318,
                "coverage_road_types": "主干道、次干道、无图支路、环岛、复杂立交桥",
                "max_operating_speed_kmh": 80,
                "requires_hd_map": False,
            },
            {
                "function_code": "VPA_MEMORY_PARKING",
                "feature_name": "跨楼层记忆泊车 (VPA-L)",
                "max_memory_route_length_km": 3.0,
                "supported_parking_slots_saved": 100,
                "supports_floor_cross": True,
            },
        ],
    }
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


def generate_aito_m9_excel(out_dir: Path) -> Path:
    """Generate AITO M9 ultra-luxury SUV configuration and Huawei powertrain specs."""
    file_path = out_dir / "AITO_M9_Ultra_Luxury_Configuration.xlsx"
    wb = openpyxl.Workbook()

    # Sheet 1: 增程双电机动力总成
    ws1 = wb.active
    ws1.title = "增程双电机动力总成"
    ws1.merge_cells("A1:E1")
    ws1["A1"] = "问界 AITO M9 旗舰SUV 动力总成与增程底盘架构规格表"
    ws1["A1"].font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color="0B2F3A", end_color="0B2F3A", fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    headers1 = ["系统模块", "技术参数项", "参数数值", "计量单位", "工程说明"]
    for col_idx, h in enumerate(headers1, 1):
        c = ws1.cell(row=2, column=col_idx, value=h)
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="1B4F72", end_color="1B4F72", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")

    powertrain_data = [
        ("增程发电机", "1.5T 专用四缸增程器", "41%", "最高热效率", "米勒循环 + 350bar高压直喷"),
        ("前驱动电机", "异步交流感应电机 (DriveONE)", "160", "kW", "峰值扭矩 277 N·m"),
        ("后驱动电机", "永磁同步电机 (DriveONE)", "230", "kW", "峰值扭矩 396 N·m"),
        ("动力电池包", "宁德时代三元锂电池 (CTP)", "52", "kWh", "WLTC纯电续航 225 km"),
        ("综合工况续航", "CLTC 综合续航里程", "1402", "km", "满油满电极限测试"),
        ("加速性能", "0-100 km/h 官方加速", "4.9", "秒", "弹射起步模式"),
    ]
    for r_idx, row_vals in enumerate(powertrain_data, start=3):
        for c_idx, val in enumerate(row_vals, start=1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            cell.alignment = Alignment(horizontal="center" if c_idx != 2 else "left", vertical="center")

    # Sheet 2: 华为乾坤ADS3与座舱
    ws2 = wb.create_sheet(title="华为乾坤ADS3与座舱")
    ws2.append(["系统分类", "配置项目", "核心指标", "支持状态", "备注说明"])
    for c in ws2[1]:
        c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="1B4F72", end_color="1B4F72", fill_type="solid")

    cabin_data = [
        ("智能驾驶", "华为乾坤 ADS 3.0", "192线车规级激光雷达", "标配", "端到端网络 GOD + PDP"),
        ("智能座舱", "HarmonyOS 4 智慧座舱", "麒麟990A 车机芯片", "标配", "六座全车声学隔离与多屏流转"),
        ("抬头显示", "75英寸临境 AR-HUD", "2K 分辨率 12000nits", "标配", "车道级实景导航AR引导"),
        ("声学系统", "施罗德散布声学技术", "25 扬声器 2080W", "标配", "空间音频 7.1.4 环绕声道"),
    ]
    for r in cabin_data:
        ws2.append(r)

    wb.save(file_path)
    wb.close()
    logger.info(f"Generated {file_path}")
    return file_path


def generate_yangwang_u8_word(out_dir: Path) -> Path:
    """Generate Yangwang U8 emergency flotation & quad-motor rescue manual."""
    file_path = out_dir / "Yangwang_U8_Emergency_Flotation_Manual.docx"
    doc = docx.Document()

    doc.add_heading("仰望 U8 越野玩家版 应急浮水与四电机防爆胎稳定控制规范", level=1)
    p_meta = doc.add_paragraph()
    p_meta.add_run("文件编号: BYD-YW-EMERG-2026-004 | 密级: 核心技术发布 | 适用车型: 仰望 U8 (豪华版/越野玩家版)")

    doc.add_heading("1. 应急浮水技术原理与触发条件", level=2)
    doc.add_paragraph(
        "仰望 U8 车身核心结构采用一体化铸造密封底盘与 IP68 级防尘防水电机电驱总成。"
        "当涉水深度传感器监测到水深超过安全阈值 (1000mm) 且车轮附着力归零时，"
        "整车电子控制单元将在 100 毫秒内自动关闭发动机进气道水阀并锁闭车窗空调外循环，激活应急浮水被动防御状态。"
    )

    doc.add_heading("2. 浮水操控性能与多轮差速桨轮转向指标", level=2)
    t = doc.add_table(rows=1, cols=4)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    hdr[0].text = "控制项目"
    hdr[1].text = "设计指标"
    hdr[2].text = "极限测试工况"
    hdr[3].text = "安全冗余设计"

    flotation_rows = [
        ("静水漂浮承载时长", "最长 30 分钟无进水", "车厢负压排气阀闭合", "底盘双层独立密封胶条"),
        ("水面航行驱动速度", "最高 3.0 km/h", "四轮叶片花纹轮胎划水", "易四方电机独立正反转"),
        ("水面航向调头控制", "原地 360° 掉头转向", "左右侧轮胎反向差速旋转", "前后桥扭矩微秒级自适应分配"),
        ("出水安全自检", "高压电绝缘阻抗监测", "大于 500 MΩ", "自动启动制动盘扫水除湿"),
    ]
    for row in flotation_rows:
        r_cells = t.add_row().cells
        for idx, val in enumerate(row):
            r_cells[idx].text = val

    doc.add_heading("3. 120km/h 高速爆胎极限稳定控制策略 (易四方技术)", level=2)
    doc.add_paragraph(
        "> 危险与安全提示: 车辆在高速 120 km/h 突发单轮爆胎时，易四方系统以每秒 1000 次的频率检测单轮转速失速，"
        "瞬间调整剩余三个车轮的扭矩输出与滑移率，产生反向偏航力矩抵消爆胎撕扯力，确保车身姿态不失控横滑。"
    )

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_lynkco_08_tsv(out_dir: Path) -> Path:
    """Generate Lynk & Co 08 EM-P 3-speed DHT super hybrid technical specs."""
    file_path = out_dir / "LynkCo_08_EM-P_Super_Hybrid_Specs.tsv"
    headers = [
        "gear_position\tgear_ratio\tp1_generator_kw\tp3_drive_kw\tp4_rear_kw\ttotal_system_kw\tsystem_torque_nm\tcltc_ev_km\tcltc_total_km"
    ]
    lines = [headers[0]]
    specs = [
        ("1挡 (高扭起步/大坡度爬坡)", "3.125", "60", "160", "156", "436", "905", "245", "1400"),
        ("2挡 (中速超车/城际快速巡航)", "1.650", "60", "160", "156", "436", "905", "245", "1400"),
        ("3挡 (高速经济直驱/降油耗)", "0.825", "60", "160", "156", "436", "905", "245", "1400"),
        ("P1+P3 纯电双电机直驱模式", "N/A", "0", "160", "156", "316", "640", "245", "N/A"),
    ]
    for row in specs:
        lines.append("\t".join(row))

    file_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


def generate_zf_akc_toml(out_dir: Path) -> Path:
    """Generate ZF Active Kinematics Control (AKC) rear-wheel steering parameters."""
    file_path = out_dir / "ZF_Rear_Axle_Steering_AKC_Parameters.toml"
    toml_content = """# 采埃孚 (ZF Friedrichshafen) 后轮主动转向系统 (AKC) 参数配置文件
[system_overview]
oem_module_name = "ZF_AKC_Gen3_DualActuator"
description = "双执行器后轮主动转向系统，支持反向偏转减小转弯半径与同向偏转提升高速稳定性"
max_steer_angle_deg = 10.0
actuator_max_stroke_mm = 32.0
response_time_ms = 45.0
ip_protection = "IP6K9K"

[kinematics_control]
low_speed_counter_phase_limit_kmh = 50.0   # 低于此车速后轮与前轮反向偏转，减小转弯半径
high_speed_co_phase_threshold_kmh = 70.0  # 高于此车速后轮与前轮同向偏转，抑制甩尾侧倾
min_turning_diameter_meters = 10.45       # 轴距3100mm车型转弯半径由12.2m降至10.45m
crab_mode_enabled = true                  # 蟹行模式: 四轮同向偏转实现斜向平移

[fail_safe_strategy]
sensor_redundancy = "Dual_Hall_Angle_Sensor + Resolver"
fault_reaction_mode = "Mechanical_Center_Lock"  # 断电或故障时中央机械自锁锁中
voltage_operating_range_v = [9.0, 16.0]
"""
    file_path.write_text(toml_content.strip(), encoding="utf-8")
    logger.info(f"Generated {file_path}")
    return file_path


# ══════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════


def generate_all_enterprise_datasets():
    """Generate complete 100-document automotive dataset corpus in data/enterprise_benchmark/ and sync to data/sample_specs/."""
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_SPECS_DIR.mkdir(parents=True, exist_ok=True)

    generated_files = []

    # 1. Excel (20 files: 4 baseline + 16 expanded)
    generated_files.append(generate_byd_financing_excel(BENCHMARK_DIR))
    generated_files.append(generate_xiaomi_su7_ultra_excel(BENCHMARK_DIR))
    generated_files.append(generate_huawei_tuling_bom_excel(BENCHMARK_DIR))
    generated_files.append(generate_aito_m9_excel(BENCHMARK_DIR))
    generated_files.extend(generate_all_new_excel_datasets(BENCHMARK_DIR))

    # 2. Word (20 files: 3 baseline + 17 expanded)
    generated_files.append(generate_tesla_service_bulletin_word(BENCHMARK_DIR))
    generated_files.append(generate_nio_safety_manual_word(BENCHMARK_DIR))
    generated_files.append(generate_yangwang_u8_word(BENCHMARK_DIR))
    generated_files.extend(generate_all_new_word_datasets(BENCHMARK_DIR))

    # 3. PowerPoint (15 files: 2 baseline + 13 expanded)
    generated_files.append(generate_zeekr_001_fr_presentation(BENCHMARK_DIR))
    generated_files.append(generate_li_mega_battlecard_presentation(BENCHMARK_DIR))
    generated_files.extend(generate_all_new_pptx_datasets(BENCHMARK_DIR))

    # 4. Images (15 files: 2 baseline + 13 expanded)
    generated_files.append(generate_xiaomi_v800_infographic_png(BENCHMARK_DIR))
    generated_files.append(generate_instrument_cluster_warning_jpg(BENCHMARK_DIR))
    generated_files.extend(generate_all_new_image_datasets(BENCHMARK_DIR))

    # 5. PDF (10 files: 1 baseline + 9 expanded)
    generated_files.append(generate_avatr_12_pdf(BENCHMARK_DIR))
    generated_files.extend(generate_all_new_pdf_datasets(BENCHMARK_DIR))

    # 6. CSV & TSV Telemetry (10 files: 3 baseline + 7 expanded)
    generated_files.append(generate_catl_thermal_test_csv(BENCHMARK_DIR))
    generated_files.append(generate_powertrain_efficiency_tsv(BENCHMARK_DIR))
    generated_files.append(generate_lynkco_08_tsv(BENCHMARK_DIR))

    # 7. Structured Text: JSON / TOML / MD / HTML / RTF (10 files: 5 baseline + 5 expanded)
    generated_files.append(generate_ev_subsidy_policy_json(BENCHMARK_DIR))
    generated_files.append(generate_zeekr_warranty_terms_md(BENCHMARK_DIR))
    generated_files.append(generate_bosch_esp_config_toml(BENCHMARK_DIR))
    generated_files.append(generate_xpeng_xngp_json(BENCHMARK_DIR))
    generated_files.append(generate_zf_akc_toml(BENCHMARK_DIR))

    # 8. Add expanded 7 CSV/TSV and 5 Structured Text datasets (12 files)
    generated_files.extend(generate_all_new_data_datasets(BENCHMARK_DIR))

    # Ensure BENCHMARK_DIR contains ONLY the generated 100 benchmark files
    generated_names = {f.name for f in generated_files}
    for existing in BENCHMARK_DIR.iterdir():
        if existing.is_file() and existing.name not in generated_names:
            logger.info(f"Removing obsolete file from {BENCHMARK_DIR}: {existing.name}")
            existing.unlink()

    # Mirror all generated benchmark files into sample_specs for unified access
    for src in generated_files:
        dest = SAMPLE_SPECS_DIR / src.name
        shutil.copy2(src, dest)

    logger.info(
        f"Successfully generated {len(generated_files)} benchmark files in {BENCHMARK_DIR} "
        f"and mirrored to {SAMPLE_SPECS_DIR}."
    )
    return generated_files


if __name__ == "__main__":
    generate_all_enterprise_datasets()
