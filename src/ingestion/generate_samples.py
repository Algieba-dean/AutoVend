"""
Generator script for realistic enterprise automotive sample documents in data/sample_specs/.
Generates:
1. Xiaomi_SU7_Trims.xlsx (Multi-sheet, merged cells, pricing formulas)
2. Zeekr_001_Service_Manual.docx (Hierarchical headings, maintenance schedules, torque spec tables, callouts, footnotes)
3. NIO_ET9_Launch_Deck.pptx (Multi-slide, spatial text boxes, embedded comparison table, speaker notes)
4. Aito_M9_Spec_Sheet.png (High-resolution spec sheet with EXIF metadata)
5. Battery_Degradation_4680.csv (4680 cylindrical cell battery life cycle test dataset)
"""

from pathlib import Path

import docx
import openpyxl
import pptx
from docx.enum.table import WD_TABLE_ALIGNMENT
from openpyxl.styles import Alignment, Font, PatternFill
from PIL import ExifTags, Image, ImageDraw
from pptx.dml.color import RGBColor as PPT_RGBColor
from pptx.util import Inches as PPT_Inches
from pptx.util import Pt as PPT_Pt

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_specs"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def generate_xiaomi_su7_excel():
    excel_path = SAMPLE_DIR / "Xiaomi_SU7_Trims.xlsx"
    wb = openpyxl.Workbook()

    # Sheets for Standard, Pro, Max trims
    trims_data = [
        {
            "sheet_name": "Standard_标准版",
            "title": "小米 SU7 标准版 (Xiaomi SU7 Standard) 官方技术参数与金融核算表",
            "base_price": 215900,
            "subsidy": 10000,
            "powertrain": "后置单电机 (后驱)",
            "power": "220 kW / 299 PS",
            "torque": "400 N·m",
            "accel": "5.28 秒",
            "battery_type": "弗迪磷酸铁锂刀片电池",
            "battery_capacity": "73.6 kWh",
            "range_cltc": "700 km",
            "voltage_platform": "400V 碳化硅高压平台",
            "chip": "高通骁龙 8295",
            "adas": "Xiaomi Pilot Pro (纯视觉 + 单 Orin-N 84 TOPS)",
        },
        {
            "sheet_name": "Pro_超长续航版",
            "title": "小米 SU7 Pro 超长续航版 官方技术参数与金融核算表",
            "base_price": 245900,
            "subsidy": 12000,
            "powertrain": "后置单电机 (后驱)",
            "power": "220 kW / 299 PS",
            "torque": "400 N·m",
            "accel": "5.70 秒",
            "battery_type": "宁德时代神行全能电池 (磷酸铁锂)",
            "battery_capacity": "94.3 kWh",
            "range_cltc": "830 km",
            "voltage_platform": "400V 碳化硅高压平台",
            "chip": "高通骁龙 8295",
            "adas": "Xiaomi Pilot Max (激光雷达 + 双 Orin-X 508 TOPS)",
        },
        {
            "sheet_name": "Max_高性能版",
            "title": "小米 SU7 Max 双电机四驱超充版 官方技术参数与金融核算表",
            "base_price": 299900,
            "subsidy": 15000,
            "powertrain": "双电机四轮驱动 (全轮驱动)",
            "power": "495 kW / 673 PS",
            "torque": "838 N·m",
            "accel": "2.78 秒",
            "battery_type": "宁德时代麒麟三元锂电池",
            "battery_capacity": "101.0 kWh",
            "range_cltc": "800 km",
            "voltage_platform": "全栈 800V 碳化硅高压平台 (871V)",
            "chip": "高通骁龙 8295",
            "adas": "Xiaomi Pilot Max (激光雷达 + 双 Orin-X 508 TOPS + 城市导航领航)",
        },
    ]

    for idx, trim in enumerate(trims_data):
        if idx == 0:
            ws = wb.active
            ws.title = trim["sheet_name"]
        else:
            ws = wb.create_sheet(title=trim["sheet_name"])

        # Title merged row
        ws.merge_cells("A1:D1")
        ws["A1"] = trim["title"]
        ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1F497D")
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

        # Headers
        headers = ["分类模块", "技术参数项目", "官方技术指标", "说明与选装状态"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=2, column=c_idx, value=h)
            cell.font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Category 1: 动力与底盘 (Rows 3-6)
        ws.merge_cells("A3:A6")
        ws["A3"] = "动力与底盘总成"
        ws["A3"].alignment = Alignment(horizontal="center", vertical="center")
        ws["A3"].font = Font(name="Arial", bold=True)

        specs_group1 = [
            ("驱动电机型式", trim["powertrain"], "标配永磁同步电机"),
            ("最大综合功率/马力", trim["power"], "整车综合动力输出"),
            ("峰值扭矩", trim["torque"], "官方额定轮端扭矩"),
            ("0-100km/h 加速时间", trim["accel"], "实测百公里弹射加速"),
        ]
        for r_offset, (item, val, note) in enumerate(specs_group1, start=3):
            ws.cell(row=r_offset, column=2, value=item)
            ws.cell(row=r_offset, column=3, value=val)
            ws.cell(row=r_offset, column=4, value=note)

        # Category 2: 电池与高压电气系统 (Rows 7-10)
        ws.merge_cells("A7:A10")
        ws["A7"] = "电池与高压电气"
        ws["A7"].alignment = Alignment(horizontal="center", vertical="center")
        ws["A7"].font = Font(name="Arial", bold=True)

        specs_group2 = [
            ("动力电池包型式", trim["battery_type"], "CTB一体化车身电池集成技术"),
            ("动力电池标称电量", trim["battery_capacity"], "额定总可用容量"),
            ("CLTC 综合工况续航", trim["range_cltc"], "标准工况循环里程"),
            ("电气架构平台电压", trim["voltage_platform"], "高压快充核心架构"),
        ]
        for r_offset, (item, val, note) in enumerate(specs_group2, start=7):
            ws.cell(row=r_offset, column=2, value=item)
            ws.cell(row=r_offset, column=3, value=val)
            ws.cell(row=r_offset, column=4, value=note)

        # Category 3: 智能座舱与高阶智驾 (Rows 11-12)
        ws.merge_cells("A11:A12")
        ws["A11"] = "智能座舱与智驾"
        ws["A11"].alignment = Alignment(horizontal="center", vertical="center")
        ws["A11"].font = Font(name="Arial", bold=True)

        specs_group3 = [
            ("座舱芯片与操作系统", trim["chip"], "澎湃 HyperOS 车载生态系统"),
            ("智能驾驶辅助系统", trim["adas"], "高精感知硬件与算力平台"),
        ]
        for r_offset, (item, val, note) in enumerate(specs_group3, start=11):
            ws.cell(row=r_offset, column=2, value=item)
            ws.cell(row=r_offset, column=3, value=val)
            ws.cell(row=r_offset, column=4, value=note)

        # Category 4: 金融与官方定价核算 (Rows 13-17) with FORMULAS!
        ws.merge_cells("A13:A17")
        ws["A13"] = "金融核算与购车测算"
        ws["A13"].alignment = Alignment(horizontal="center", vertical="center")
        ws["A13"].font = Font(name="Arial", bold=True)

        ws.cell(row=13, column=2, value="官方整车指导价 (元)")
        ws.cell(row=13, column=3, value=trim["base_price"])
        ws.cell(row=13, column=4, value="全国统一零售指导价")

        ws.cell(row=14, column=2, value="首销权益/选配基金 (元)")
        ws.cell(row=14, column=3, value=trim["subsidy"])
        ws.cell(row=14, column=4, value="限时赠送选装抵扣权益")

        ws.cell(row=15, column=2, value="实际购车裸车总价 (元)")
        ws.cell(row=15, column=3, value="=C13-C14")  # Formula!
        ws.cell(row=15, column=4, value="公式计算: [指导价 - 选配权益]")

        ws.cell(row=16, column=2, value="首年商业全险预估 (元)")
        ws.cell(row=16, column=3, value="=ROUND(C15*0.032, 0)")  # Formula!
        ws.cell(row=16, column=4, value="按裸车价 3.2% 预估费率")

        ws.cell(row=17, column=2, value="全款落地预估总计 (元)")
        ws.cell(row=17, column=3, value="=C15+C16+500")  # Formula!
        ws.cell(row=17, column=4, value="公式计算: [裸车价 + 商业险 + 500上牌工本费]")

        # Format columns width
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 25
        ws.column_dimensions["C"].width = 32
        ws.column_dimensions["D"].width = 35

    wb.save(excel_path)
    print(f"Generated {excel_path} (3 sheets, formulas, merged cells)")


def generate_zeekr_001_word():
    doc_path = SAMPLE_DIR / "Zeekr_001_Service_Manual.docx"
    doc = docx.Document()

    # Section Header & Footer
    sec0 = doc.sections[0]
    sec0.header.paragraphs[0].text = "极氪汽车售后技术文件 • 内部受控服务指导书"
    sec0.footer.paragraphs[0].text = "第 1 页 • 严禁未授权翻印"

    # Document Title & Subtitle
    doc.add_paragraph("极氪 001 服务维保技术手册 (Zeekr 001 Service Manual)", style="Title")
    doc.add_paragraph("极氪售后技术培训部 • 新能源服务中心车间标准机修作业指导书", style="Subtitle")

    # Image Caption
    doc.add_paragraph("图 1-1: 极氪 001 前双叉臂悬架与双腔空气弹簧空间布置示意图", style="Caption")

    # Heading 1
    doc.add_heading("1. 动力电池与高压电驱系统维保规程", level=1)

    doc.add_paragraph(
        "全新极氪 001 标配全栈 800V 高压电气架构，配备大容量三元锂或磷酸铁锂电池系统。"
        "在车间作业过程中，任何涉电操作均必须严格遵守国家新能源汽车高压维修安全规范 GB/T 18384。"
    )

    # Callout / Warning box
    doc.add_paragraph(
        "【高压维保重大安全警告】: 进入动力电池箱内部维修或拆解高压母线前，必须首先断开整车 MSD (手动维修开关)，"
        "并使用经定期校准的 1000V 绝缘万用表测试高压直流母线输出端，确认残余电压降低至 36V 安全电压以下方可施工！",
        style="Quote"
    )

    # Heading 2
    doc.add_heading("1.1 冷却回路与防冻液更换周期", level=2)
    doc.add_paragraph("极氪 001 采用高效液冷温控循环回路，包含电驱回路、动力电池回路与座舱热泵空调回路。日常维保检查要求如下：")

    # Bullet lists
    doc.add_paragraph("冷却液标准冰点指标测试：需达到 -45℃ 极寒防冻等级。", style="List Bullet")
    doc.add_paragraph("系统气密性检测：向膨胀水壶施加 120 kPa 稳压测试，3分钟内压降不得大于 5 kPa。", style="List Bullet")
    doc.add_paragraph("全车冷却液更换周期：首次满 4 年或 80,000 公里更换，后续每 2 年或 40,000 公里更换。", style="List Bullet")

    # Heading 2
    doc.add_heading("1.2 底盘与悬挂系统关键紧固力矩标准", level=2)
    doc.add_paragraph("双腔空气悬架与前双叉臂、后多连杆悬挂结构关键紧固件力矩参数表如下：")

    # Complex Table with Merged cells and Multi-paragraph cells
    table = doc.add_table(rows=6, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Table Header
    headers = ["装配模块", "紧固件规格与描述", "标准紧固力矩 (N·m)", "工艺拧紧方法", "复检与更换要求"]
    for c_idx, h in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.text = h

    # Row 1-2 merged module
    table.cell(1, 0).merge(table.cell(2, 0))
    table.cell(1, 0).text = "前悬挂双叉臂总成"

    table.cell(1, 1).text = "前下摆臂与副车架连接螺栓 (M14×1.5)"
    table.cell(1, 2).text = "120 ± 10 N·m"
    table.cell(1, 3).text = "扭矩法 + 90° 塑性角度拧紧\n(预紧50Nm -> 终拧120Nm -> 旋转90度)"
    table.cell(1, 4).text = "拆卸后必须更换全新达克罗涂层螺栓"

    table.cell(2, 1).text = "转向节上球头销锁紧螺母 (M12×1.25)"
    table.cell(2, 2).text = "75 ± 5 N·m"
    table.cell(2, 3).text = "单级扭矩一次性到位"
    table.cell(2, 4).text = "需使用开口销彻底锁止防松"

    # Row 3-4 merged module
    table.cell(3, 0).merge(table.cell(4, 0))
    table.cell(3, 0).text = "后副车架与双腔空悬"

    table.cell(3, 1).text = "后副车架固定螺栓 (M16×1.5 10.9级)"
    table.cell(3, 2).text = "180 ± 15 N·m"
    table.cell(3, 3).text = "交叉分级对称拧紧 (90Nm -> 180Nm)"
    table.cell(3, 4).text = "每次下副车架作业必须换新"

    table.cell(4, 1).text = "双腔空悬空气弹簧下支架紧固螺栓"
    table.cell(4, 2).text = "95 ± 8 N·m"
    table.cell(4, 3).text = "扭矩扳手垂直校核"
    table.cell(4, 4).text = "紧固前需确保悬架处于空载几何标准位"

    # Row 5: 轮毂总成
    table.cell(5, 0).text = "轮毂与制动盘"
    table.cell(5, 1).text = "车轮固定螺母 (M14×1.5, 21寸/22寸锻造轮毂)"
    table.cell(5, 2).text = "140 ± 10 N·m"
    table.cell(5, 3).text = "对角线五星交替顺序逐级拧紧"
    table.cell(5, 4).text = "行车50公里后需使用扭力扳手实施二次复紧"

    # Footnotes
    doc.add_paragraph("【特别附注说明与工艺要求】:", style="Caption")
    doc.add_paragraph("* 注1: 所有铝合金铸造副车架与摆臂连接紧固件，严禁使用气动冲击扳手直接高速拧死，避免铝制螺纹孔滑丝滑扣。")
    doc.add_paragraph("* 注2: 双腔空气悬架在执行拆卸充放气时，必须使用极氪专用诊断仪 (Zeekr Diag) 激活【车间机修维修举升模式】。")

    # Heading 1
    doc.add_heading("2. 激光雷达与高阶智驾传感器动态标定", level=1)
    doc.add_paragraph("当车辆经历挡风玻璃更换、前保险杠拆装或底盘四轮定位调整后，必须执行高级辅助驾驶系统的传感器对中与动态路试标定：")
    doc.add_paragraph("1. 静态标定：在标准水平反射标定间，架设三维光学标定靶板，靶板距离车头前车标中心点为 3000 ± 10 mm。", style="List Number")
    doc.add_paragraph("2. 激光雷达姿态校准：使用专用雷达光斑校准仪确认水平俯仰角在 -1.5° 至 +0.5° 公差范围内。", style="List Number")
    doc.add_paragraph("3. 动态路试学习：连接车载诊断仪进入自学习标定模式，在车道线清晰的双向四车道城市快速路以 50-80 km/h 匀速行驶 15 分钟。", style="List Number")

    doc.save(doc_path)
    print(f"Generated {doc_path} (headings, torque table with merged cells, callouts, footnotes)")


def generate_nio_et9_pptx():
    pptx_path = SAMPLE_DIR / "NIO_ET9_Launch_Deck.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.333)
    prs.slide_height = PPT_Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Slide 1: Title Slide
    slide1 = prs.slides.add_slide(blank_layout)
    # Background shape or title
    title_box = slide1.shapes.add_textbox(PPT_Inches(1.0), PPT_Inches(2.0), PPT_Inches(11.333), PPT_Inches(2.5))
    tf1 = title_box.text_frame
    tf1.word_wrap = True
    p_title = tf1.paragraphs[0]
    p_title.text = "蔚来 ET9 旗舰行政轿车发布会"
    p_title.font.size = PPT_Pt(44)
    p_title.font.bold = True
    p_title.font.color.rgb = PPT_RGBColor(15, 34, 64)

    p_sub = tf1.add_paragraph()
    p_sub.text = "NIO ET9 Official Launch Deck • 行政旗舰的技术全景与智能电动底盘革新"
    p_sub.font.size = PPT_Pt(22)
    p_sub.font.color.rgb = PPT_RGBColor(80, 95, 120)

    # Slide 2: Core Architecture Features with Spatial Layout
    slide2 = prs.slides.add_slide(blank_layout)
    s2_title_box = slide2.shapes.add_textbox(PPT_Inches(1.0), PPT_Inches(0.6), PPT_Inches(11.333), PPT_Inches(1.0))
    s2_tf = s2_title_box.text_frame
    s2_p = s2_tf.paragraphs[0]
    s2_p.text = "核心技术架构: 全域900V高压与天行智能底盘"
    s2_p.font.size = PPT_Pt(32)
    s2_p.font.bold = True

    # 3 Spatial content columns (Left, Middle, Right)
    col_w = PPT_Inches(3.5)
    gap = PPT_Inches(0.4)
    left_base = PPT_Inches(1.0)

    features = [
        ("全域 900V 超充高压架构", [
            "全球首个最高电压达 925V 的整车全域电气系统",
            "自研 1200V 碳化硅功率模块，最高电驱效率 99.5%",
            "峰值充电功率可达 600kW，5C 超快充 5分钟续航增加 255km",
            "自研 46105 大圆柱电池电芯，整包容量 120kWh",
        ]),
        ("自研神玑 NX9031 智驾芯片", [
            "首款采用 5nm 车规级尖端制程的自研算力芯片",
            "单颗芯片拥有超过 32 核高能效 CPU 与双核 NPU",
            "超大内存带宽，可毫秒级完成 BEV 多模态感知融合",
            "中央超算平台 ADAM 2.0 实现智驾、座舱与整车底盘融合",
        ]),
        ("天行智能全主动底盘系统", [
            "全球首创集成式液压全主动悬架，各轮独立快速举升",
            "毫秒级频响 (1000次/秒路况感知与悬架自适应调整)",
            "线控转向系统 (Steer-by-Wire)，方向盘无机械连接",
            "后轮最大转向角 8.3 度，最小转弯直径仅 10.9 米",
        ]),
    ]

    for col_idx, (col_title, bullet_items) in enumerate(features):
        col_left = left_base + col_idx * (col_w + gap)
        box = slide2.shapes.add_textbox(col_left, PPT_Inches(1.8), col_w, PPT_Inches(5.0))
        tf = box.text_frame
        tf.word_wrap = True

        h_p = tf.paragraphs[0]
        h_p.text = col_title
        h_p.font.size = PPT_Pt(20)
        h_p.font.bold = True
        h_p.font.color.rgb = PPT_RGBColor(31, 78, 120)

        for b in bullet_items:
            bp = tf.add_paragraph()
            bp.text = b
            bp.font.size = PPT_Pt(14)
            bp.level = 1

    # Speaker notes for Slide 2
    slide2_notes = slide2.notes_slide.notes_text_frame
    slide2_notes.text = (
        "【演讲者要点提示】: 强调全域 900V 不仅是充电桩端高压，而是涵盖电机、电控、空调压缩机等所有附件的真900V。"
        "神玑芯片的能效比高通/英伟达公版方案提升30%以上。"
    )

    # Slide 3: Comparison Table (ET9 vs Panamera vs Maybach)
    slide3 = prs.slides.add_slide(blank_layout)
    s3_title_box = slide3.shapes.add_textbox(PPT_Inches(1.0), PPT_Inches(0.6), PPT_Inches(11.333), PPT_Inches(1.0))
    s3_tf = s3_title_box.text_frame
    s3_p = s3_tf.paragraphs[0]
    s3_p.text = "行政旗舰技术参数横向对比矩阵"
    s3_p.font.size = PPT_Pt(32)
    s3_p.font.bold = True

    # Embedded Slide Table
    tbl_shape = slide3.shapes.add_table(6, 4, PPT_Inches(1.0), PPT_Inches(1.8), PPT_Inches(11.333), PPT_Inches(4.8))
    table = tbl_shape.table

    matrix = [
        ["技术维度 / 车型", "蔚来 ET9 (自主旗舰)", "保时捷 Panamera 4 E-Hybrid", "迈巴赫 S 580 4MATIC"],
        ["整车电气架构电压", "全域 925V (真900V碳化硅平台)", "400V 高压混合动力架构", "48V 轻度混动架构"],
        ["底盘悬架系统", "天行全主动集成液压悬挂 (1000Hz响应)", "双腔双阀空气悬架 (PASM)", "智能车身控制魔毯悬架 (AIRMATIC)"],
        ["转向控制技术", "全线控转向 (后轮转向角达 8.3°)", "机械电动助力转向 (后轮转角 2.8°)", "电子助力转向 (后轮转角 4.5°/10°)"],
        ["智驾超算芯片", "双自研神玑 NX9031 (5nm 32核NPU)", "公版辅驾芯片 (L2级ADAS)", "Drive Pilot 芯片平台 (特定路段L3)"],
        ["官方预售价 / 指导价", "80.00 万元 (预售)", "128.80 万元起", "248.80 万元起"],
    ]

    for r_idx, row in enumerate(matrix):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                p.font.size = PPT_Pt(14)
                if r_idx == 0:
                    p.font.bold = True
                    p.font.color.rgb = PPT_RGBColor(255, 255, 255)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = PPT_RGBColor(31, 78, 120)

    slide3_notes = slide3.notes_slide.notes_text_frame
    slide3_notes.text = "【对比话术】: ET9在电气电压、主动底盘响应频率和线控转向技术上全面超越传统德系D级行政豪车，且价格具备极强颠覆性。"

    # Slide 4: Active SkyRide Chassis with Deep Speaker Notes
    slide4 = prs.slides.add_slide(blank_layout)
    s4_title_box = slide4.shapes.add_textbox(PPT_Inches(1.0), PPT_Inches(0.6), PPT_Inches(11.333), PPT_Inches(1.0))
    s4_tf = s4_title_box.text_frame
    s4_p = s4_tf.paragraphs[0]
    s4_p.text = "天行底盘: 极致平稳与香槟塔挑战"
    s4_p.font.size = PPT_Pt(32)
    s4_p.font.bold = True

    s4_box = slide4.shapes.add_textbox(PPT_Inches(1.0), PPT_Inches(1.8), PPT_Inches(11.333), PPT_Inches(4.5))
    s4_ctf = s4_box.text_frame
    s4_ctf.word_wrap = True
    s4_paras = [
        "• 全球首个车头堆叠四层香槟塔高速通过连续减速带的量产车型，滴水不洒。",
        "• 每个减震器集成独立电动液压泵，可在 1毫秒内快速施加高达 5000 N 的瞬时推拉力。",
        "• 迎宾离地间隙无感降低 50mm，颠簸路面自动快速抬升 20mm 保证通过性。",
        "• 抑制车辆制动点头率 90%，抑制过弯侧倾角 85%，重构头等舱级后排静谧平稳体验。",
    ]
    for idx, p_text in enumerate(s4_paras):
        if idx == 0:
            p = s4_ctf.paragraphs[0]
        else:
            p = s4_ctf.add_paragraph()
        p.text = p_text
        p.font.size = PPT_Pt(18)

    slide4_notes = slide4.notes_slide.notes_text_frame
    slide4_notes.text = (
        "【演讲者要点提示】: 强调香槟塔视频的真实性与病毒式传播效应。"
        "天行底盘核心是把主动控制从毫秒级推进到微秒级，为后排行政商务用户创造如履平地的平稳性。"
    )

    prs.save(pptx_path)
    print(f"Generated {pptx_path} (4 slides, spatial text layout, comparison table, speaker notes)")


def generate_aito_m9_image():
    img_path = SAMPLE_DIR / "Aito_M9_Spec_Sheet.png"
    w, h = 1200, 900
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Header Box
    draw.rectangle([(30, 30), (w - 30, 110)], fill=(25, 45, 80))
    # Outer Border
    draw.rectangle([(30, 30), (w - 30, h - 30)], outline=(25, 45, 80), width=3)

    # Draw Title text (mocking text lines)
    draw.text((60, 50), "问界 M9 旗舰车型配置规格表 (AITO M9 Spec Sheet)", fill=(255, 255, 255))

    # Spec sheet grid lines
    specs = [
        ("车辆基本参数", "指标数值与技术方案说明"),
        ("整车长宽高尺寸", "5230mm × 1999mm × 1800mm, 轴距: 3110mm"),
        ("动力驱动总成", "前后双电机智能四驱系统, 最大总功率 365kW / 390kW"),
        ("综合百公里加速", "纯电版 4.3 秒 / 增程版 4.9 秒"),
        ("动力电池与续航", "CLTC 综合工况 630km (纯电版) / 综合续航 1402km (增程版)"),
        ("智能驾驶系统", "华为乾崑智驾 ADS 3.0 高阶智能驾驶辅助"),
        ("智能座舱系统", "HarmonyOS 4 智能座舱, 临境抬头显示 AR-HUD 75英寸"),
        ("底盘与悬挂结构", "华为途灵智能底盘, 闭式空气悬架 + CDC 连续可变阻尼减振器"),
        ("官方指导售价", "46.98 万元 - 56.98 万元 (增程Max/Ultra, 纯电Max/Ultra)"),
    ]

    row_top = 130
    row_h = 75
    draw.rectangle([(50, row_top), (w - 50, row_top + row_h)], fill=(225, 235, 250))
    draw.line([(50, row_top), (w - 50, row_top)], fill=(25, 45, 80), width=2)
    draw.line([(400, row_top), (400, row_top + row_h * len(specs))], fill=(25, 45, 80), width=2)

    for i, (k, v) in enumerate(specs):
        curr_y = row_top + i * row_h
        draw.line([(50, curr_y), (w - 50, curr_y)], fill=(200, 210, 225), width=1)
        draw.text((70, curr_y + 25), f"{k}:", fill=(20, 20, 20))
        draw.text((420, curr_y + 25), v, fill=(40, 40, 40))

    draw.line([(50, row_top + len(specs) * row_h), (w - 50, row_top + len(specs) * row_h)], fill=(25, 45, 80), width=2)

    # Footnote
    draw.text((60, h - 60), "注: 以上参数源自鸿蒙智行 AITO 问界官方产品技术规范库，最终配置请以实车交付为准。", fill=(120, 120, 120))

    # Add EXIF metadata tags
    exif = img.getexif()
    exif[ExifTags.Base.Make] = "AutoVend Enterprise Camera"
    exif[ExifTags.Base.Model] = "Aito-M9-Scanner-Pro"
    exif[ExifTags.Base.DateTime] = "2026:01:15 10:30:00"
    exif[ExifTags.Base.Software] = "AutoVend Image Engine 2.0"

    img.save(img_path, "PNG", exif=exif)
    print(f"Generated {img_path} ({w}x{h}, EXIF metadata tags)")


def generate_battery_degradation_csv():
    csv_path = SAMPLE_DIR / "Battery_Degradation_4680.csv"
    headers = [
        "Cycle_Number",
        "Capacity_Retention_Percent",
        "Discharge_Capacity_Ah",
        "Internal_Resistance_mOhm",
        "Charge_Temp_Celsius",
        "Discharge_Temp_Celsius",
        "State_Of_Health_SOH",
        "Degradation_Phase",
        "Testing_Notes",
    ]

    rows = []
    initial_cap = 25.0  # Ah
    base_ir = 12.5      # mOhm

    # 30 cycle milestone points from cycle 1 to cycle 1500
    cycles = [1, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500]

    for c in cycles:
        # Realistic non-linear battery degradation model:
        # SEI growth + lithium plating (square root of cycle count with late-stage acceleration)
        retention = max(70.0, 100.0 - (c ** 0.55) * 0.55 - (c / 1000.0) * 1.5)
        cap = initial_cap * (retention / 100.0)
        ir = base_ir + (100.0 - retention) * 0.42

        if retention >= 95.0:
            soh = "EXCELLENT"
            phase = "SEI Formation Stabilization"
            note = "容量极低衰减，电化学阻抗稳定"
        elif retention >= 88.0:
            soh = "GOOD"
            phase = "Linear Diffusion Aging"
            note = "活性锂缓慢消耗，内阻轻微上升"
        elif retention >= 80.0:
            soh = "AGED_NORMAL"
            phase = "Electrode Microcracking"
            note = "动力电池健康寿命临界点，满足车用质保SLA"
        else:
            soh = "REPLACE_RECOMMENDED"
            phase = "Accelerated Fade Knee"
            note = "梯次利用退役指标，建议移至储能储能系统"

        rows.append([
            str(c),
            f"{retention:.2f}%",
            f"{cap:.3f}",
            f"{ir:.2f}",
            "25.0",
            "28.5",
            soh,
            phase,
            note,
        ])

    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for r in rows:
            f.write(",".join(r) + "\n")

    print(f"Generated {csv_path} ({len(rows)} records, 4680 battery cycle life data)")


if __name__ == "__main__":
    generate_xiaomi_su7_excel()
    generate_zeekr_001_word()
    generate_nio_et9_pptx()
    generate_aito_m9_image()
    generate_battery_degradation_csv()
