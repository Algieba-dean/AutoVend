"""
Automotive Specification PDF Generator for AutoVend.
Generates complex multi-page vehicle spec PDFs with titles, multi-column sections,
and bordered tables for layout analysis and parent-child retrieval testing.
"""

import io
import os
from pathlib import Path
from PIL import Image as PILImage, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image as RLImage,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from reportlab.pdfbase.cidfonts import UnicodeCIDFont

font_name = "STSong-Light"
try:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
except Exception:
    font_name = "Helvetica"


def generate_xiaomi_su7_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A202C"),
        spaceAfter=14,
    )
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8,
    )

    story = []

    # Title & Header
    story.append(Paragraph("Xiaomi SU7 Ultra Technical Specification Manual", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra Prototype & Production. 本手册包含三电机动力总成、纽北调校底盘、宁德时代麒麟II高功率电池及全栈自研高阶智驾硬件清单。",
            body_style,
        )
    )
    story.append(Spacer(1, 10))

    # Section 1
    story.append(Paragraph("1. Powertrain and Performance Specifications", h1_style))
    story.append(
        Paragraph(
            "小米SU7 Ultra搭载两台V8s超级电机与一台V6s电机，综合最大马力达到1548匹马力，最高转速可达27200rpm。零百加速仅需1.98秒，最高时速超过350km/h。",
            body_style,
        )
    )

    # Table 1: Performance Matrix
    t1_data = [
        ["Specification", "Xiaomi SU7 Ultra", "Xiaomi SU7 Max", "Tesla Model S Plaid"],
        ["Powertrain", "Triple-Motor AWD (V8s+V8s+V6s)", "Dual-Motor AWD (V6s+V6)", "Tri-Motor AWD"],
        ["Max Horsepower", "1548 PS", "673 PS", "1020 PS"],
        ["0-100 km/h (s)", "1.98 s", "2.78 s", "2.10 s"],
        ["Top Speed", "350 km/h", "265 km/h", "322 km/h"],
        ["100-0 km/h Braking", "30.8 m (Carbon Ceramic)", "33.3 m (Brembo)", "34.0 m"],
    ]
    t1 = Table(t1_data, colWidths=[120, 140, 130, 130])
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
            ]
        )
    )
    story.append(t1)
    story.append(Spacer(1, 15))

    # Section 2
    story.append(Paragraph("2. Battery Pack and Thermal Architecture", h1_style))
    story.append(
        Paragraph(
            "采用宁德时代麒麟II高功率赛道专用电池包，支持最大5.2C超级快充。峰值放电功率达到1330kW，即使在20%低电量状态下仍可输出超过800kW电量保障赛道圈速。",
            body_style,
        )
    )

    # Table 2: Battery Specs
    t2_data = [
        ["Parameter", "Value", "Standard / Unit", "Description"],
        ["Pack Capacity", "93.7", "kWh", "CATL Qilin II High-rate Cell"],
        ["Max Discharge Power", "1330", "kW", "Track Mode Peak Discharge"],
        ["Charging Multiplier", "5.2", "C", "897V High Voltage Platform"],
        ["10%-80% Charge Time", "11", "Minutes", "Dual-Gun / Ultra 480kW Terminal"],
        ["CLTC Electric Range", "630", "km", "Standard aerodynamic package"],
    ]
    t2 = Table(t2_data, colWidths=[130, 90, 120, 180])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A0AEC0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#EDF2F7"), colors.white]),
            ]
        )
    )
    story.append(t2)
    story.append(PageBreak())

    # Page 2: Section 3
    story.append(Paragraph("3. Autonomous Driving Sensors and Perception Suite", h1_style))
    story.append(
        Paragraph(
            "搭载两颗NVIDIA DRIVE Orin计算芯片，总算力508 TOPS。标配超远距激光雷达、高清环视摄像头及毫米波雷达，实现全场景无图城市导航驾驶与赛道遥测记录。",
            body_style,
        )
    )

    # Table 3: Sensor Inventory
    t3_data = [
        ["Sensor Type", "Quantity", "Detection Range", "Key Supplier / Model"],
        ["LiDAR (128-beam)", "1", "200 m (10% Reflectivity)", "Hesai AT128 Roof-mounted"],
        ["8MP HD Cameras", "11", "Up to 250 m", "Sony Automotive Image Sensors"],
        ["Millimeter Wave Radars", "3", "160 m", "Continental 4D mmWave"],
        ["Ultrasonic Sensors", "12", "5.5 m", "Bosch Ultrasonic Sonar"],
        ["Compute Platform", "2 chips", "508 TOPS", "Dual NVIDIA DRIVE Orin-X"],
    ]
    t3 = Table(t3_data, colWidths=[140, 70, 140, 170])
    t3.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
            ]
        )
    )
    story.append(t3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    print(f"Generated sample PDF at: {output_path}")


def generate_byd_yangwang_u9_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "U9DocTitle",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#742A2A"),
        spaceAfter=14,
    )
    h1_style = ParagraphStyle(
        "U9H1",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#9B2C2C"),
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "U9Body",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8,
    )

    story = []

    # Title & Header
    story.append(Paragraph("BYD Yangwang U9 Electric Supercar Technical Datasheet", title_style))
    story.append(
        Paragraph(
            "Vehicle Model: BYD Yangwang U9 (仰望U9). 本手册详细记载易四方四电机独立驱动架构、云辇-X全主动车身控制系统、超跑专用刀片电池及赛道遥测数据规格。",
            body_style,
        )
    )
    story.append(Spacer(1, 10))

    # Section 1: Powertrain
    story.append(Paragraph("1. e4 (易四方) Quad-Motor Powertrain & DiSus-X Architecture", h1_style))
    story.append(
        Paragraph(
            "仰望U9搭载易四方四电机独立驱动技术，系统综合最大功率960kW（1306马力），峰值扭矩1680N·m，最高转速可达21000rpm。0-100km/h加速时间仅需2.36秒。",
            body_style,
        )
    )

    # Table 1: Powertrain & Dynamics with merged cells / spans
    t1_data = [
        ["System / Module", "Technical Specification", "Rating / Value", "Operating Regime"],
        ["e4 Quad-Motor", "Front Dual Motors", "2 x 240 kW", "Individual Torque Vectoring"],
        ["e4 Quad-Motor", "Rear Dual Motors", "2 x 240 kW", "Individual Torque Vectoring"],
        ["Output Metrics", "Total Horsepower", "1306 PS (960 kW)", "All-Wheel Drive Full Load"],
        ["Output Metrics", "0-100 km/h Acceleration", "2.36 s", "Track Launch Mode"],
        ["Chassis System", "DiSus-X (云辇-X)", "Active Hydraulic", "Full Active Body Control"],
    ]
    t1 = Table(t1_data, colWidths=[110, 150, 120, 140])
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#9B2C2C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFF5F5"), colors.white]),
            ]
        )
    )
    story.append(t1)
    story.append(Spacer(1, 15))

    # Section 2: Battery & Charging
    story.append(Paragraph("2. Blade Battery Pack and High Voltage Charging", h1_style))
    story.append(
        Paragraph(
            "采用专为超跑定制的高倍率磷酸铁锂刀片电池，容量80kWh，连续放电功率达1200kW。支持双枪超级快充，最大充电功率达500kW，从30%充至80%仅需10分钟。",
            body_style,
        )
    )

    t2_data = [
        ["Parameter", "Specification", "Unit", "Benchmark Standards"],
        ["Battery Type", "Lithium Iron Phosphate (Blade)", "LFP", "High-rate Track Pack"],
        ["Capacity", "80.0", "kWh", "Structural Cell-to-Chassis"],
        ["Continuous Discharge", "1200", "kW", "Thermal Runaway Protected"],
        ["Max Fast Charging", "500", "kW", "Dual-Gun DC Charging 800V"],
        ["CLTC Range", "450", "km", "Standard Track/Street Mix"],
    ]
    t2 = Table(t2_data, colWidths=[120, 160, 80, 160])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#742A2A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A0AEC0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#EDF2F7"), colors.white]),
            ]
        )
    )
    story.append(t2)
    story.append(PageBreak())

    # Page 2: Aerodynamics & Cockpit
    story.append(Paragraph("3. Carbon Fiber Aerodynamics & Cockpit Telemetry", h1_style))
    story.append(
        Paragraph(
            "仰望U9全车采用12组空气动力学套件与碳纤维超级驾驶舱。座舱搭载DiLink 150智能座舱平台与赛道随享助理，提供专业圈速记录与转角G值实时显示。",
            body_style,
        )
    )

    t3_data = [
        ["Telemetry Feature", "Hardware / Specification", "Max Performance", "Functionality"],
        ["Aero Downforce", "Active Carbon Rear Wing", "280 kg @ 250 km/h", "Adjustable 4 Angles"],
        ["Braking System", "Carbon Ceramic Discs + 6-Piston", "32.2 m (100-0 km/h)", "Fade Free on Track"],
        ["Cockpit Processor", "BYD DiLink 150 4nm Chip", "High Throughput", "Real-time Telemetry"],
        ["G-Force Sensor", "6-Axis High-Rate IMU", "Up to 3.0 G", "Cornering Telemetry Display"],
    ]
    t3 = Table(t3_data, colWidths=[120, 160, 120, 120])
    t3.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#9B2C2C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFF5F5"), colors.white]),
            ]
        )
    )
    story.append(t3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    print(f"Generated sample PDF at: {output_path}")


def generate_enterprise_multipage_pdf(output_path: Path):
    """
    Generates a complex 3-page enterprise technical spec PDF with:
    1. Cross-page table spanning Page 1 and Page 2 with identical headers.
    2. Dual-column technical whitepaper layout on Page 3.
    3. Running headers, page numbers, and background watermark.
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EntTitle",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A202C"),
        spaceAfter=10,
    )
    h1_style = ParagraphStyle(
        "EntH1",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=12,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "EntH2",
        parent=styles["Heading3"],
        fontName=font_name,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2C5282"),
        spaceBefore=6,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "EntBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=6,
    )

    story = []

    # Page 1: Title and Cross-Page Table Part 1
    story.append(Paragraph("AutoVend 2026 旗舰高性能新能源车型技术全景白皮书", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra & BYD Yangwang U9 联合竞品技术对标。本白皮书包含全系动力总成横向对比矩阵、双栏底盘工程白皮书与高阶智驾硬件清单。",
            body_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("1. 全系动力总成与选装规格对比总表", h1_style))
    story.append(
        Paragraph(
            "本表收录小米SU7系列与仰望U9全版本动力、电池、智驾算力及定价参数，支持跨页持续对比解析。",
            body_style,
        )
    )

    headers = ["版本型号 / Trim", "动力架构 / Drive", "综合马力 / Power", "电池容量 / Battery", "指导价 / Price", "智驾芯片 / Autonomous"]
    t_part1_data = [
        headers,
        ["SU7 标准版", "单电机后驱", "299 PS", "73.6 kWh", "21.59 万元", "NVIDIA Orin-N 84TOPS"],
        ["SU7 Pro", "单电机长续航", "299 PS", "94.3 kWh", "24.59 万元", "Dual Orin-X 508TOPS"],
        ["SU7 Max", "双电机四驱", "673 PS", "101.0 kWh", "29.99 万元", "Dual Orin-X 508TOPS"],
        ["SU7 Ultra 量产版", "三电机全驱", "1548 PS", "93.7 kWh", "81.49 万元", "Dual Orin-X 508TOPS"],
        ["SU7 Ultra 赛道版", "三电机高功率", "1548 PS", "93.7 kWh", "81.49 万元", "赛道遥测传感器套件"],
    ]
    t_part1 = Table(t_part1_data, colWidths=[95, 85, 80, 80, 75, 105])
    t_part1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_part1)
    story.append(PageBreak())

    # Page 2: Cross-Page Table Part 2 (Repeated headers with continuation rows)
    story.append(Paragraph("1. 全系动力总成与选装规格对比总表 (续)", h1_style))
    t_part2_data = [
        headers,  # Repeated header on Page 2
        ["仰望U9 标准版", "易四方四电机", "1306 PS", "80.0 kWh", "168.0 万元", "DiPilot 600 高阶智驾"],
        ["仰望U9 赛道套件版", "易四方+云辇-X", "1306 PS", "80.0 kWh", "188.0 万元", "DiPilot 600 + 赛道遥测"],
        ["仰望U9 碳纤维特装版", "易四方+全碳车身", "1306 PS", "80.0 kWh", "198.0 万元", "DiPilot 600 全栈方案"],
        ["仰望U9 纽北极速版", "易四方超高转", "1400 PS", "80.0 kWh", "218.0 万元", "赛道六轴高精度IMU"],
    ]
    t_part2 = Table(t_part2_data, colWidths=[95, 85, 80, 80, 75, 105])
    t_part2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#EDF2F7"), colors.white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_part2)
    story.append(Spacer(1, 15))

    # Page 2 Section: Additional text
    story.append(Paragraph("1.2 动力性能综合评测小结", h2_style))
    story.append(
        Paragraph(
            "对比测试表明，小米SU7 Ultra在极速延伸与轻量化三电机效率方面具备优势，而仰望U9在易四方原地掉头、云辇-X全主动垂向控制方面展现顶级工程水准。",
            body_style,
        )
    )
    story.append(PageBreak())

    # Page 3: Dual-Column Layout Section
    story.append(Paragraph("2. 底盘悬架与空气动力学工程白皮书", h1_style))
    story.append(
        Paragraph(
            "2.1 左右双栏技术解析: 本章节针对前后轴独立控制技术采用双栏排版，展示前轴主动悬架与后轴扭矩矢量差速控制。",
            body_style,
        )
    )
    story.append(Spacer(1, 10))

    left_column_paras = [
        Paragraph("2.1.1 前轴主动悬架与气动阻尼", h2_style),
        Paragraph(
            "前轴采用全铝合金双叉臂独立悬架，集成连续阻尼可调减振器（CDC）与双腔空气弹簧。系统以每秒1000次的频率实时监测路面冲击，动态调节悬架刚度与车身姿态。在高速过弯时前外侧悬架瞬间提高阻尼抑制侧倾，提供极限抓地力与循迹指向性。",
            body_style,
        ),
        Paragraph(
            "同时前唇配备主动升降气坝，可根据当前车速（超过120km/h时）自动降低20mm，在前桥区域额外产生50kg下压力，有效减少空气升力，稳定高速行驶轮荷分布。",
            body_style,
        ),
    ]

    right_column_paras = [
        Paragraph("2.1.2 后轴扭矩矢量分配与主动差速", h2_style),
        Paragraph(
            "后轴搭载双独立电机矢量控制单元，具备微秒级独立正负扭矩响应能力。在弯道极限状态下，系统通过外侧车轮主动加速与内侧车轮电机制动产生偏航力矩，实现赛道级中性转向。",
            body_style,
        ),
        Paragraph(
            "搭配后桥高效散热回路与双枪快充高压直冷回路，即使超跑连续在赛道高负荷刷圈，驱动桥温度依然被牢牢压制在85摄氏度以下，杜绝热保护降扭现象。",
            body_style,
        ),
    ]

    dual_col_table = Table([[left_column_paras, right_column_paras]], colWidths=[255, 255])
    dual_col_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(dual_col_table)

    def draw_header_footer_watermark(canvas, doc_obj):
        canvas.saveState()
        # Running Header
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend Confidential Enterprise Specification Manual 2026")
        canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
        canvas.setLineWidth(0.5)
        canvas.line(36, 800, 559, 800)

        # Running Footer
        page_num = doc_obj.page
        canvas.drawString(36, 25, "保密文件 仅供内部技术与销售策略传阅")
        canvas.drawRightString(559, 25, f"Page {page_num} of 3")
        canvas.line(36, 35, 559, 35)

        # Background Watermark
        canvas.setFont("Helvetica", 42)
        canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.3))
        canvas.translate(300, 420)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "CONFIDENTIAL")
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=draw_header_footer_watermark, onLaterPages=draw_header_footer_watermark)
    print(f"Generated enterprise multi-page PDF at: {output_path}")


def generate_enterprise_3page_continuous_table_pdf(output_path: Path):
    """
    Generates a 4-page enterprise PDF containing:
    1. A 3-page continuous scroll table (Page 1 -> Page 2 -> Page 3).
    2. A multi-level header table on Page 4.
    3. A 3-column layout section on Page 4.
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EntTitle",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A202C"),
        spaceAfter=10,
    )
    h1_style = ParagraphStyle(
        "EntH1",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=12,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "EntH2",
        parent=styles["Heading3"],
        fontName=font_name,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2C5282"),
        spaceBefore=6,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "EntBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=6,
    )

    story = []

    # Page 1: 3-Page Continuous Table Part 1
    story.append(Paragraph("AutoVend 2026 跨三页长表格与复合表头企业白皮书", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra & BYD Yangwang U9 & Porsche Taycan 极限对标长表。本表格连续横跨第1至第3页。",
            body_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("1. 全球顶级超跑三页滚动对比总表 (第1页)", h1_style))

    headers = ["Trim / 版本", "Drive / 驱动", "Power / 功率", "Battery / 电池", "Price / 指导价"]
    t1_data = [
        headers,
        ["SU7 标准版", "单电机后驱", "299 PS", "73.6 kWh", "21.59 万元"],
        ["SU7 Pro", "单电机长续航", "299 PS", "94.3 kWh", "24.59 万元"],
        ["SU7 Max", "双电机四驱", "673 PS", "101.0 kWh", "29.99 万元"],
    ]
    t1 = Table(t1_data, colWidths=[100, 100, 100, 100, 120])
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t1)
    story.append(PageBreak())

    # Page 2: Continuous Table Part 2
    story.append(Paragraph("1. 全球顶级超跑三页滚动对比总表 (第2页续)", h1_style))
    t2_data = [
        headers,
        ["SU7 Ultra 量产版", "三电机全驱", "1548 PS", "93.7 kWh", "81.49 万元"],
        ["SU7 Ultra 赛道版", "三电机高功率", "1548 PS", "93.7 kWh", "81.49 万元"],
        ["仰望U9 标准版", "易四方四电机", "1306 PS", "80.0 kWh", "168.0 万元"],
    ]
    t2 = Table(t2_data, colWidths=[100, 100, 100, 100, 120])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t2)
    story.append(PageBreak())

    # Page 3: Continuous Table Part 3
    story.append(Paragraph("1. 全球顶级超跑三页滚动对比总表 (第3页结)", h1_style))
    t3_data = [
        headers,
        ["仰望U9 纽北极速版", "易四方超高转", "1400 PS", "80.0 kWh", "218.0 万元"],
        ["Taycan Turbo GT", "前后双电机", "1034 PS", "97.0 kWh", "199.8 万元"],
    ]
    t3 = Table(t3_data, colWidths=[100, 100, 100, 100, 120])
    t3.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t3)
    story.append(PageBreak())

    # Page 4: Multi-level header table & 3-Column section
    story.append(Paragraph("2. 复合多级表头与三栏三段工程架构", h1_style))
    ml_data = [
        ["基本信息", "基本信息", "动力性能", "动力性能"],
        ["车型代号", "指导价格", "系统马力", "零百加速"],
        ["Xiaomi SU7 Ultra", "81.49 万元", "1548 PS", "1.98 秒"],
        ["BYD Yangwang U9", "168.0 万元", "1306 PS", "2.36 秒"],
    ]
    ml_table = Table(ml_data, colWidths=[130, 120, 130, 140])
    ml_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#2C5282")),
                ("TEXTCOLOR", (0, 0), (-1, 1), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(ml_table)
    story.append(Spacer(1, 15))

    # 3-column section
    story.append(Paragraph("2.1 三栏独立系统工程解析", h2_style))
    col1 = [
        Paragraph("<b>左栏: 电池系统</b>", body_style),
        Paragraph("高倍率动力三元锂电池包，支持5.2C超级快充，放电峰值功率1330kW。", body_style),
    ]
    col2 = [
        Paragraph("<b>中栏: 电驱系统</b>", body_style),
        Paragraph("前V6s后双V8s超级三电机总成，最高转速27200rpm，全铝转子设计。", body_style),
    ]
    col3 = [
        Paragraph("<b>右栏: 底盘系统</b>", body_style),
        Paragraph("闭式双腔空悬与CDC减振系统，碳陶制动盘搭配前六活塞高性能卡钳。", body_style),
    ]
    three_col_tbl = Table([[col1, col2, col3]], colWidths=[170, 170, 170])
    three_col_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(three_col_tbl)

    def draw_watermark(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend Multi-Level & 3-Page Scroll Benchmark 2026")
        canvas.line(36, 800, 559, 800)
        canvas.drawString(36, 25, "保密文件 仅供研发评测")
        canvas.drawRightString(559, 25, f"Page {doc_obj.page} of 4")
        canvas.line(36, 35, 559, 35)

        canvas.setFont("Helvetica", 42)
        canvas.setFillColor(colors.Color(0.88, 0.88, 0.88, alpha=0.25))
        canvas.translate(300, 420)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "CONFIDENTIAL")
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    print(f"Generated enterprise 3-page continuous table PDF at: {output_path}")


def generate_financial_autoloan_pdf(output_path: Path):
    """
    Case 1: Financial / Auto-loan insurance policy & interest rate table with multi-tier nested terms and fine print.
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=42,
        bottomMargin=42,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FinTitle", parent=styles["Heading1"], fontName=font_name, fontSize=18, leading=22, textColor=colors.HexColor("#1A202C"), spaceAfter=10
    )
    h1_style = ParagraphStyle(
        "FinH1", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=17, textColor=colors.HexColor("#2B6CB0"), spaceBefore=12, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "FinBody", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#2D3748"), spaceAfter=6
    )
    fine_print_style = ParagraphStyle(
        "FinFinePrint", parent=styles["Normal"], fontName=font_name, fontSize=7.5, leading=10.5, textColor=colors.HexColor("#718096"), spaceAfter=4
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("AutoVend 汽车金融贷款与全险定制方案白皮书", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra & BYD Yangwang U9 全系专属金融政策。本手册详细规定首付比例、还款期数、综合年化费率IRR、贴息额度及提前还款违约金约定。",
            body_style,
        )
    )
    story.append(Spacer(1, 8))

    # Section 1: Multi-tier interest rate matrix
    story.append(Paragraph("1. 阶梯年化费率与贴息金融方案矩阵", h1_style))

    fin_headers_l1 = ["金融方案分类", "分期期限与首付", "分期期限与首付", "利率及年化费率", "利率及年化费率", "月供与贴息政策", "月供与贴息政策"]
    fin_headers_l2 = ["方案名称", "首付比例", "还款期数", "银行名义费率", "综合年化利率IRR", "预估月供金额", "主机厂贴息额"]
    fin_data = [
        fin_headers_l1,
        fin_headers_l2,
        ["0息先享方案", "15% 起", "24 期", "0.00%", "0.00%", "28,860 元", "25,000 元"],
        ["0息先享方案", "20% 起", "36 期", "0.00%", "0.00%", "18,100 元", "38,000 元"],
        ["超低息长贷方案", "15% 起", "48 期", "1.99%", "3.80%", "14,250 元", "15,000 元"],
        ["超低息长贷方案", "15% 起", "60 期", "2.15%", "4.12%", "11,880 元", "12,000 元"],
        ["50-50残值保值贷", "50% 尾款", "24 期", "1.20%", "2.35%", "1,880 元", "20,000 元"],
    ]

    tbl_fin = Table(fin_data, colWidths=[85, 65, 65, 75, 80, 75, 78])
    tbl_fin.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#2C5282")),
                ("TEXTCOLOR", (0, 0), (-1, 1), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(tbl_fin)
    story.append(Spacer(1, 6))

    # Fine print footnotes
    story.append(Paragraph("*注1：以上综合年化利率（IRR）均依据中国人民银行单利计算口径测算，实际执行费率以合作金融机构最终批复为准。", fine_print_style))
    story.append(Paragraph("*注2：客户还款满12个月后可申请提前还款，资方按剩余未还本金金额的 3% 计收提前结清违约金手续费。", fine_print_style))
    story.append(Paragraph("*特别约定：主机厂贴息额度由AutoVend专属金融基金直冲购车款，不可兑换现金或转赠第三方。", fine_print_style))
    story.append(PageBreak())

    # Page 2: Insurance policy table
    story.append(Paragraph("2. 专属综合商业险方案与高压电池特约险", h1_style))
    ins_data = [
        ["险种大类", "具体保险责任", "保障限额", "免赔率约定"],
        ["机动车损失险", "车辆全损及零部件损坏赔付", "车身发票价 (81.49~168万)", "0% 绝对免赔"],
        ["第三者责任险", "人身伤亡与财产损失保额", "最高 1,000 万元", "0% 绝对免赔"],
        ["高压电池专属险", "电池热失控自燃及碰撞底盘穿刺", "电池总成全额重置 (35万元)", "0% 绝对免赔"],
        ["赛道事故特约险", "封闭赛道非竞技刷圈意外车损", "最高 50 万元", "5% 绝对免赔"],
    ]
    tbl_ins = Table(ins_data, colWidths=[100, 190, 130, 100])
    tbl_ins.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ]
        )
    )
    story.append(tbl_ins)
    story.append(Spacer(1, 6))
    story.append(Paragraph("*特别免责条款：在未取得赛事主管机构认证或非法改装动力总成工况下发生的事故，保险人不承担任何赔偿责任。", fine_print_style))

    def draw_fin_watermark(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend Financial Services & Insurance Policy 2026")
        canvas.line(36, 800, 559, 800)
        canvas.drawString(36, 25, "保密商务政策 仅限金融部与授权交付中心传阅")
        canvas.drawRightString(559, 25, f"Page {doc_obj.page} of 2")
        canvas.line(36, 35, 559, 35)

        canvas.setFont("Helvetica", 42)
        canvas.setFillColor(colors.Color(0.88, 0.88, 0.88, alpha=0.25))
        canvas.translate(300, 420)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "CONFIDENTIAL")
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=draw_fin_watermark, onLaterPages=draw_fin_watermark)
    print(f"Generated financial auto-loan PDF at: {output_path}")


def generate_vehicle_maintenance_manual_pdf(output_path: Path):
    """
    Case 2: Complex vehicle maintenance manual with mixed column layouts:
    Single-column intro banner -> Dual-column diagnostic steps -> Embedded spec table -> Single-column safety sign-off.
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MaintTitle", parent=styles["Heading1"], fontName=font_name, fontSize=17, leading=21, textColor=colors.HexColor("#1A202C"), spaceAfter=8
    )
    banner_style = ParagraphStyle(
        "MaintBanner", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#C53030"), spaceAfter=10
    )
    h1_style = ParagraphStyle(
        "MaintH1", parent=styles["Heading2"], fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor("#2B6CB0"), spaceBefore=8, spaceAfter=4
    )
    h2_style = ParagraphStyle(
        "MaintH2", parent=styles["Heading3"], fontName=font_name, fontSize=10.5, leading=14, textColor=colors.HexColor("#2C5282"), spaceBefore=4, spaceAfter=4
    )
    body_style = ParagraphStyle(
        "MaintBody", parent=styles["Normal"], fontName=font_name, fontSize=8.5, leading=12, textColor=colors.HexColor("#2D3748"), spaceAfter=4
    )

    story = []

    # Title & Top Spanning Warning Banner (Single Column)
    story.append(Paragraph("AutoVend 高压电驱与电池系统检修技术手册", title_style))
    story.append(Paragraph("车型代号: Xiaomi SU7 Ultra 高压架构专用诊断规范", body_style))
    story.append(
        Paragraph(
            "<b>【高压作业安全规范警示】</b> 在进行任何高压配电盒 (PDU) 与逆变器检修前，必须断开主断路熔断开关 (MSD)，等待5分钟释放母线电容残余电压，并佩戴10kV绝缘手套与护目镜。",
            banner_style,
        )
    )
    story.append(Spacer(1, 6))

    # Middle Section: Dual-Column Diagnostic Steps
    col1 = [
        Paragraph("1.1 故障现象与DTC码读取", h2_style),
        Paragraph("读取网关控制器中的DTC故障代码（如P0A0F-00高压互锁开路故障、P0C73-00预充回路超时）。", body_style),
        Paragraph("连接OBD-II诊断仪进入三电系统实时数据流监测模式，记录高压母线电压及主正主负接触器闭合状态。", body_style),
    ]
    col2 = [
        Paragraph("1.2 物理测量与排故处置流程", h2_style),
        Paragraph("使用高内阻数字万用表测试高压互锁回路（HVIL）引脚端子通断状态。正常导通阻值应小于1.5Ω。", body_style),
        Paragraph("若测量阻值无穷大，排查前电机控制器低压线束接插件是否存在针脚退针、氧化或密封圈破损漏水导致短路。", body_style),
    ]
    dual_tbl = Table([[col1, col2]], colWidths=[255, 255])
    dual_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(dual_tbl)
    story.append(Spacer(1, 10))

    # Embedded Borderless Spec Table
    story.append(Paragraph("2. 高压互锁与传感器引脚电气规格参数对照表", h1_style))
    spec_data = [
        ["端子代号", "功能定义", "标准工作电压", "导通阻值上限", "诊断控制策略"],
        ["HVIL-IN", "高压互锁输入检测信号", "DC 12.0V ± 0.5V", "≤ 1.0 Ω", "开路低电平报警"],
        ["HVIL-OUT", "高压互锁回路反馈状态", "DC 12.0V ± 0.5V", "≤ 1.5 Ω", "切断主接触器供电"],
        ["PDU-TEMP", "配电盒NTC温度传感", "DC 0.5V - 4.5V", "10.0 kΩ (25℃)", "超温降扭限功率"],
        ["INV-GATE", "逆变器IGBT驱动使能", "PWM 5.0V / 20kHz", "≤ 0.5 Ω", "封锁三相驱动脉冲"],
    ]
    spec_tbl = Table(spec_data, colWidths=[90, 130, 100, 90, 110])
    spec_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(spec_tbl)
    story.append(Spacer(1, 6))
    story.append(Paragraph("*注：测量端子阻值前务必将低压蓄电池负极断开，严禁在带电状态下使用万用表电阻档测量。", body_style))
    story.append(Spacer(1, 10))

    # Bottom Spanning Sign-off Banner (Single Column)
    signoff_style = ParagraphStyle(
        "MaintSignoff", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#276749"), spaceAfter=6
    )
    story.append(
        Paragraph(
            "<b>【终检验收规范】</b> 排除故障后，必须使用专用绝缘耐压测试仪对整车高压绝缘电阻进行打压测试（测试电压DC 1000V，绝缘阻值必须大于500MΩ），测试通过后方可恢复MSD并试车交付。",
            signoff_style,
        )
    )

    def draw_maint_watermark(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend High-Voltage Maintenance & Diagnostics 2026")
        canvas.line(36, 800, 559, 800)
        canvas.drawString(36, 25, "售后技术服务中心受控文件 | 单双栏混合排版规范")
        canvas.drawRightString(559, 25, "Page 1 of 1")
        canvas.line(36, 35, 559, 35)
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=draw_maint_watermark, onLaterPages=draw_maint_watermark)
    print(f"Generated vehicle maintenance manual PDF at: {output_path}")


def generate_irregular_borderless_specs_pdf(output_path: Path):
    """
    Case 3: Irregular / borderless spec table where gridlines are missing (whitespace-delimited columns).
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=42,
        bottomMargin=42,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BorderTitle", parent=styles["Heading1"], fontName=font_name, fontSize=18, leading=22, textColor=colors.HexColor("#1A202C"), spaceAfter=10
    )
    h1_style = ParagraphStyle(
        "BorderH1", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=17, textColor=colors.HexColor("#2B6CB0"), spaceBefore=12, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BorderBody", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#2D3748"), spaceAfter=6
    )

    story = []

    story.append(Paragraph("Xiaomi SU7 Ultra & BYD Yangwang U9 极限技术参数表 (无网格线白皮书)", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra & Yangwang U9 全维度参数对比，本表格采用无框线留白对齐排版，考察版面空白流列对齐自适应识别能力。",
            body_style,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. 全球顶级纯电超跑参数全系总表 (纯留白排版)", h1_style))

    # Pure borderless table: NO grid, NO box in TableStyle!
    data = [
        ["Trim / 版本型号", "Power / 功率", "Torque / 扭矩", "Battery / 电池", "0-100 / 加速", "Price / 指导价"],
        ["SU7 Ultra 量产版", "1548 PS", "1770 Nm", "93.7 kWh 麒麟II", "1.98 秒", "81.49 万元"],
        ["SU7 Ultra 赛道版", "1548 PS", "1770 Nm", "93.7 kWh 麒麟II", "1.98 秒", "81.49 万元"],
        ["仰望U9 标准版", "1306 PS", "1680 Nm", "80.0 kWh 刀片", "2.36 秒", "168.0 万元"],
        ["仰望U9 纽北极速版", "1400 PS", "1680 Nm", "80.0 kWh 刀片", "2.15 秒", "218.0 万元"],
    ]
    borderless_tbl = Table(data, colWidths=[105, 75, 75, 100, 75, 90])
    # TableStyle without any GRID, BOX, or LINE
    borderless_tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(borderless_tbl)
    story.append(Spacer(1, 6))

    story.append(Paragraph("*注：以上零百加速成绩均在干燥沥青路面、弹射起步模式及电量大于80%工况下实测所得。", body_style))
    story.append(Spacer(1, 14))

    story.append(Paragraph("2. 超跑电驱平台核心技术解读", h1_style))
    story.append(
        Paragraph(
            "小米V8s超级电机最高转速达到27200rpm，采用超高强度硅钢片与定转子双向直冷油冷技术；比亚迪易四方四电机系统具备微秒级独立正负扭矩响应，支持原地掉头与敏捷矢量控车。",
            body_style,
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    print(f"Generated irregular borderless specs PDF at: {output_path}")


def generate_mixed_orientation_enterprise_specs_pdf(output_path: Path):
    """
    Case 4: Multi-page document with mixed page orientations (Portrait, Landscape, Portrait).
    """
    doc = BaseDocTemplate(str(output_path), pagesize=A4)

    # Portrait frame (A4: 595.27 x 841.89)
    frame_p = Frame(36, 36, 595.27 - 72, 841.89 - 72, id="f_portrait")
    # Landscape frame (landscape(A4): 841.89 x 595.27)
    frame_l = Frame(36, 36, 841.89 - 72, 595.27 - 72, id="f_landscape")

    def draw_portrait_decor(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend Global Multi-Orientation Supercar Benchmark 2026")
        canvas.line(36, 800, 559, 800)
        canvas.drawString(36, 25, "混合排版规范 | 纵向页")
        canvas.drawRightString(559, 25, f"Page {doc_obj.page} of 3")
        canvas.line(36, 35, 559, 35)
        canvas.restoreState()

    def draw_landscape_decor(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 560, "AutoVend Global Multi-Orientation Supercar Benchmark 2026 (Landscape Matrix)")
        canvas.line(36, 555, 805, 555)
        canvas.drawString(36, 25, "混合排版规范 | 横向超宽矩阵页")
        canvas.drawRightString(805, 25, f"Page {doc_obj.page} of 3")
        canvas.line(36, 35, 805, 35)
        canvas.restoreState()

    doc.addPageTemplates(
        [
            PageTemplate(id="portrait", frames=frame_p, pagesize=A4, onPage=draw_portrait_decor),
            PageTemplate(id="landscape", frames=frame_l, pagesize=landscape(A4), onPage=draw_landscape_decor),
        ]
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MixedTitle", parent=styles["Heading1"], fontName=font_name, fontSize=18, leading=22, textColor=colors.HexColor("#1A202C"), spaceAfter=10
    )
    h1_style = ParagraphStyle(
        "MixedH1", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=17, textColor=colors.HexColor("#2B6CB0"), spaceBefore=12, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "MixedBody", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#2D3748"), spaceAfter=6
    )

    story = []

    # Page 1: Portrait Overview
    story.append(Paragraph("AutoVend 全球超跑全维度技术对标汇编 (混合排版版面)", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra & BYD Yangwang U9 & Porsche Taycan Turbo GT。本白皮书包含竖版平台介绍、第2页横版12列全景矩阵、及第3页研发战略研判。",
            body_style,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("1. 动力总成与电驱平台架构研讨", h1_style))
    story.append(
        Paragraph(
            "本章节剖析三电机全驱与易四方四电机架构的扭矩响应带宽，针对赛道弯道工况展开前沿动力学建模与能量流分析。",
            body_style,
        )
    )

    # Transition to Landscape for Page 2
    story.append(NextPageTemplate("landscape"))
    story.append(PageBreak())

    # Page 2: Landscape Ultra-Wide 12-Column Table
    story.append(Paragraph("2. 超跑全系十二维度技术指标横向对比全局矩阵 (横版宽屏)", h1_style))
    wide_headers = ["车型名称", "驱动形式", "电机数", "马力(PS)", "扭矩(Nm)", "电池容量", "放电倍率", "零百加速", "最高时速", "制动距离", "整备质量", "官方指导价"]
    wide_data = [
        wide_headers,
        ["Xiaomi SU7 Ultra", "全时四驱", "3电机", "1548", "1770", "93.7 kWh", "5.2C", "1.98 s", "350 km/h", "30.8 m", "1900 kg", "81.49 万元"],
        ["BYD Yangwang U9", "易四方四驱", "4电机", "1306", "1680", "80.0 kWh", "5.5C", "2.36 s", "309 km/h", "32.0 m", "2475 kg", "168.0 万元"],
        ["Taycan Turbo GT", "前后双电机", "2电机", "1034", "1300", "97.0 kWh", "4.0C", "2.20 s", "305 km/h", "31.5 m", "2220 kg", "199.8 万元"],
    ]
    # Total width = 64 * 12 = 768 pt (fits 841.89 pt page comfortably)
    wide_tbl = Table(wide_data, colWidths=[85, 60, 48, 55, 60, 68, 55, 55, 65, 60, 65, 90])
    wide_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(wide_tbl)
    story.append(Spacer(1, 8))
    story.append(Paragraph("*注：横版矩阵由系统自适应检测为 Landscape 方向，具有更大的水平显示宽度和独立边距。", body_style))

    # Transition back to Portrait for Page 3
    story.append(NextPageTemplate("portrait"))
    story.append(PageBreak())

    # Page 3: Portrait Summary
    story.append(Paragraph("3. 产业格局研判与商业化量产竞争力", h1_style))
    story.append(
        Paragraph(
            "综合全系超跑性能数据，国产高性能电动化架构在转速、升功率、矢量差速及热管理回路方面已全面超越传统燃油与混动超跑标杆。",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "碳陶制动系统搭配闭式双腔空气悬架已成为百万级纯电性能车型的标准工程配置，标志着中国汽车工业在高端性能赛道实现了全栈自研的里程碑突破。",
            body_style,
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    print(f"Generated mixed orientation enterprise specs PDF at: {output_path}")


def generate_scanned_brochure_watermark_pdf(output_path: Path):
    """
    Case 5: Scanned / image-heavy brochure with noisy watermarks, non-standard text encoding, or OCR fallback scenarios.
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=42,
        bottomMargin=42,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ScanTitle", parent=styles["Heading1"], fontName=font_name, fontSize=18, leading=22, textColor=colors.HexColor("#1A202C"), spaceAfter=10
    )
    h1_style = ParagraphStyle(
        "ScanH1", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=17, textColor=colors.HexColor("#2B6CB0"), spaceBefore=12, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "ScanBody", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#2D3748"), spaceAfter=6
    )

    story = []

    # Page 1: Digital page with heavy repeated watermarks
    story.append(Paragraph("AutoVend 绝密内部研发手册与选装手册", title_style))
    story.append(Paragraph("车型代号: Xiaomi SU7 Ultra 纽北赛道版内部验证手册", body_style))
    story.append(Paragraph("1. 极限赛道调校与动态控制参数", h1_style))
    story.append(
        Paragraph(
            "本章节包含纽博格林北环刷圈专用下压力尾翼角度、热熔轮胎预热策略及电驱高压直冷回路控制逻辑。",
            body_style,
        )
    )
    story.append(PageBreak())

    # Page 2: Pure image page with blueprint schematic drawing (Simulating scanned image page)
    # Generate blueprint image in memory
    img = PILImage.new("RGB", (800, 600), color=(235, 240, 248))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 760, 560], outline=(30, 70, 150), width=4)
    draw.line([40, 300, 760, 300], fill=(60, 110, 190), width=2)
    draw.line([400, 40, 400, 560], fill=(60, 110, 190), width=2)
    draw.ellipse([300, 200, 500, 400], outline=(200, 40, 40), width=3)
    draw.text((60, 60), "CHASSIS POWERTRAIN SUSPENSION SCHEMATIC DIAGRAM", fill=(20, 40, 80))

    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)

    rl_img = RLImage(img_buf, width=480, height=360)
    story.append(rl_img)
    story.append(Spacer(1, 10))
    # Less than 30 characters of text to trigger scanned page classification
    story.append(Paragraph("Blueprint CAD Spec", body_style))
    story.append(PageBreak())

    # Page 3: Digital conclusion page
    story.append(Paragraph("3. 质保细则与技术服务规范", h1_style))
    story.append(
        Paragraph(
            "全系车型提供整车5年或10万公里质保，关键三电系统提供8年或16万公里质保。赛道版享受专属驻场技师团队技术支持与热衰退监测。",
            body_style,
        )
    )

    def draw_repeated_watermarks(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend Confidential Engineering Manual")
        canvas.line(36, 800, 559, 800)
        canvas.drawString(36, 25, "机密文件 禁止外传")
        canvas.drawRightString(559, 25, f"Page {doc_obj.page} of 3")
        canvas.line(36, 35, 559, 35)

        # Repeated diagonal watermarks across 4 grid positions
        canvas.setFont("Helvetica", 24)
        canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.3))
        positions = [(180, 650), (420, 650), (180, 250), (420, 250)]
        for x, y in positions:
            canvas.saveState()
            canvas.translate(x, y)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, "CONFIDENTIAL - INTERNAL ONLY")
            canvas.restoreState()

        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=draw_repeated_watermarks, onLaterPages=draw_repeated_watermarks)
    print(f"Generated scanned brochure watermark PDF at: {output_path}")


def generate_enterprise_borderless_multipage_pdf(output_path: Path):
    """
    Case 6: Multi-page continuous BORDERLESS table across Page 1 and Page 2 without gridlines.
    Tests seamless cross-page borderless detection, header deduplication, and table stitching.
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BorderMultiTitle", parent=styles["Heading1"], fontName=font_name, fontSize=17, leading=21, textColor=colors.HexColor("#1A202C"), spaceAfter=8
    )
    h1_style = ParagraphStyle(
        "BorderMultiH1", parent=styles["Heading2"], fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor("#2B6CB0"), spaceBefore=10, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BorderMultiBody", parent=styles["Normal"], fontName=font_name, fontSize=8.5, leading=12, textColor=colors.HexColor("#2D3748"), spaceAfter=5
    )

    story = []

    # Page 1: Header + Part 1 of Borderless Table
    story.append(Paragraph("AutoVend 全球超跑全系规格表 (跨页无网格线白皮书)", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra & BYD Yangwang U9 & Porsche Taycan 全系列跨页无网格线技术指标，考察跨页连续空白流列表格检测与缝合对齐能力。",
            body_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("1. 全球顶级超跑动力学参数跨页总表 (第一部分)", h1_style))

    headers = ["版本型号 / Trim", "电机架构 / Motor", "最大马力 / Power", "电池规格 / Battery", "零百加速 / 0-100", "官方指导价 / Price"]
    p1_data = [
        headers,
        ["SU7 标准版", "单电机后驱", "299 PS", "73.6 kWh 磷酸铁锂", "5.28 秒", "21.59 万元"],
        ["SU7 Pro 长续航版", "单电机后驱", "299 PS", "94.3 kWh 神行电池", "5.70 秒", "24.59 万元"],
        ["SU7 Max 性能版", "双电机四驱", "673 PS", "101.0 kWh 麒麟电池", "2.78 秒", "29.99 万元"],
        ["SU7 Ultra 量产版", "三电机四驱", "1548 PS", "93.7 kWh 麒麟II高功率", "1.98 秒", "81.49 万元"],
        ["SU7 Ultra 纽北版", "三电机四驱", "1548 PS", "93.7 kWh 麒麟II全碳陶", "1.98 秒", "81.49 万元"],
    ]
    t_p1 = Table(p1_data, colWidths=[105, 80, 80, 105, 75, 78])
    t_p1.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_p1)
    story.append(PageBreak())

    # Page 2: Part 2 of Borderless Table (Repeated Headers)
    story.append(Paragraph("1. 全球顶级超跑动力学参数跨页总表 (续页部分)", h1_style))
    p2_data = [
        headers,
        ["仰望U9 标准版", "易四方四电机", "1306 PS", "80.0 kWh 刀片高倍率", "2.36 秒", "168.0 万元"],
        ["仰望U9 纽北极速版", "易四方四电机", "1400 PS", "80.0 kWh 刀片热管理版", "2.15 秒", "218.0 万元"],
        ["Taycan Turbo GT", "前后双电机", "1034 PS", "97.0 kWh 高性能蓄电池", "2.20 秒", "199.8 万元"],
        ["Model S Plaid", "三电机全驱", "1020 PS", "100.0 kWh 锂离子电池", "2.10 秒", "82.89 万元"],
    ]
    t_p2 = Table(p2_data, colWidths=[105, 80, 80, 105, 75, 78])
    t_p2.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_p2)
    story.append(Spacer(1, 8))
    story.append(Paragraph("*注：以上跨页无网格线白皮书性能数据均在标准工况与干燥沥青路面实测，已剔除起步延时。", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("2. 跨页数据拓扑完整性验证说明", h1_style))
    story.append(
        Paragraph(
            "跨页无框线表格通过列锚点对齐自适应匹配，去除第2页重复表头并无缝缝合为统一表格对象。",
            body_style,
        )
    )

    def draw_decor(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend Multi-Page Continuous Borderless Table Benchmark 2026")
        canvas.line(36, 800, 559, 800)
        canvas.drawString(36, 25, "跨页无框线表格拼接规范")
        canvas.drawRightString(559, 25, f"Page {doc_obj.page} of 2")
        canvas.line(36, 35, 559, 35)
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=draw_decor, onLaterPages=draw_decor)
    print(f"Generated enterprise borderless multipage PDF at: {output_path}")


def generate_oem_warranty_maintenance_matrix_pdf(output_path: Path):
    """
    Case 7: OEM Multi-Tier Warranty, Maintenance & Recall Matrix with 3-Level Deep Merged Category Hierarchy.
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "WarrTitle", parent=styles["Heading1"], fontName=font_name, fontSize=17, leading=21, textColor=colors.HexColor("#1A202C"), spaceAfter=8
    )
    h1_style = ParagraphStyle(
        "WarrH1", parent=styles["Heading2"], fontName=font_name, fontSize=12, leading=16, textColor=colors.HexColor("#2B6CB0"), spaceBefore=10, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "WarrBody", parent=styles["Normal"], fontName=font_name, fontSize=8.5, leading=12, textColor=colors.HexColor("#2D3748"), spaceAfter=5
    )

    story = []

    story.append(Paragraph("AutoVend 全生命周期整车三电质保与维保巡检大纲", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra & Yangwang U9 全维度三电系统与核心部件质保政策。本表格包含三级树状合并单元格，考察层级归一化与父级缓存重置能力。",
            body_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("1. 三电高压核心系统与底盘总成质保周期细则", h1_style))

    warr_headers = ["一级核心系统", "二级总成部件", "具体零件/传感器", "质保期限", "定期维保巡检周期", "召回与免费更换特约条款"]
    warr_data = [
        warr_headers,
        ["三电高压核心系统", "动力电池总成(PACK)", "电芯单体与模组", "8年或16万公里", "每20,000公里", "容量衰减超过20%免费更换全新电池包"],
        ["", "", "BMS电池管理系统", "8年或16万公里", "每10,000公里", "软件逻辑死锁或通讯丢失召回升级"],
        ["", "", "高压继电器与熔断丝", "5年或10万公里", "每40,000公里", "触点烧蚀粘连免费更换PDU总成"],
        ["", "双电机电驱总成", "V8s超级电机定转子", "8年或16万公里", "每40,000公里更换绝缘油", "定子绝缘击穿或转子退磁终身质保"],
        ["", "", "电机旋变与温度传感器", "5年或10万公里", "每20,000公里", "信号失步免费更换传感器总成"],
        ["智能底盘与制动", "云辇-X/主动悬架", "双阀CDC连续可调减振器", "5年或10万公里", "每10,000公里", "减振器漏油阻尼失效免费更换单侧总成"],
        ["", "", "高压电动液压泵站", "5年或10万公里", "每20,000公里", "工作压力不足免费更换泵组总成"],
        ["", "碳陶制动总成", "碳陶制动通风盘", "10年或20万公里", "每30,000公里称重检测", "盘面裂纹超标免费更换前后制动盘"],
    ]

    tbl_warr = Table(warr_data, colWidths=[80, 85, 95, 75, 80, 108])
    tbl_warr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E0")),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tbl_warr)
    story.append(Spacer(1, 6))
    story.append(Paragraph("*特别说明：所有核心零件在整车质保期内由于设计缺陷或偶发性材料断裂均享受全国联保与全免费备件更换。", body_style))

    def draw_warr_decor(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend Lifetime OEM Warranty & Maintenance Policy 2026")
        canvas.line(36, 800, 559, 800)
        canvas.drawString(36, 25, "受控文件 | 多级合并树状质保表")
        canvas.drawRightString(559, 25, "Page 1 of 1")
        canvas.line(36, 35, 559, 35)
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=draw_warr_decor, onLaterPages=draw_warr_decor)
    print(f"Generated OEM warranty maintenance matrix PDF at: {output_path}")


def generate_unequal_three_column_specs_pdf(output_path: Path):
    """
    Case 8: Three-column technical teardown with unequal column gutter widths and spanning callout box.
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ThreeColTitle", parent=styles["Heading1"], fontName=font_name, fontSize=17, leading=21, textColor=colors.HexColor("#1A202C"), spaceAfter=8
    )
    h1_style = ParagraphStyle(
        "ThreeColH1", parent=styles["Heading2"], fontName=font_name, fontSize=11, leading=15, textColor=colors.HexColor("#2B6CB0"), spaceBefore=6, spaceAfter=4
    )
    body_style = ParagraphStyle(
        "ThreeColBody", parent=styles["Normal"], fontName=font_name, fontSize=8, leading=11.5, textColor=colors.HexColor("#2D3748"), spaceAfter=4
    )
    callout_style = ParagraphStyle(
        "ThreeColCallout", parent=styles["Normal"], fontName=font_name, fontSize=8.5, leading=12.5, textColor=colors.HexColor("#C53030"), spaceAfter=4
    )

    story = []

    story.append(Paragraph("AutoVend 高压电气故障诊断与部件更换工时白皮书 (三栏非对称排版)", title_style))
    story.append(
        Paragraph(
            "车型代号: Xiaomi SU7 Ultra 故障码链路、示波器测量与备件采购三栏技术清单，考察非对称宽度多栏版面自然阅读顺序还原。",
            body_style,
        )
    )
    story.append(Spacer(1, 6))

    # Zone 1: Three unequal columns
    # Col 1 (width 155): DTC telemetry
    # Col 2 (width 215): Waveform analysis & physical measurement
    # Col 3 (width 153): Spare part catalog & labor hours
    col1_z1 = [
        Paragraph("1.1 DTC遥测流", h1_style),
        Paragraph("读取网关控制器DTC码P0A0F-00高压互锁开路故障，诊断仪监测母线电压状态。", body_style),
        Paragraph("监测BMS主正主负接触器闭合信号及高压配电盒PDU实时电流波形。", body_style),
    ]
    col2_z1 = [
        Paragraph("1.2 示波器波形与物理测量", h1_style),
        Paragraph("使用双通道数字示波器抓取HVIL方波反馈脉冲信号（占空比50% ± 5%，幅值DC 12V）。", body_style),
        Paragraph("使用高内阻数字万用表测试HVIL回路引脚电阻，标准导通阻值应 ≤ 1.0 Ω。", body_style),
    ]
    col3_z1 = [
        Paragraph("1.3 备件定额与采购", h1_style),
        Paragraph("高压互锁低压接插件零件号: AV-HVIL-897-C，库存充足，更换工时定额0.5小时。", body_style),
        Paragraph("配电盒控制主板零件号: AV-PDU-CTRL-01，保税仓紧急调拨周期24小时。", body_style),
    ]

    tbl_z1 = Table([[col1_z1, col2_z1, col3_z1]], colWidths=[155, 215, 153])
    tbl_z1.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(tbl_z1)
    story.append(Spacer(1, 8))

    # Middle Spanning Banner: spans all 3 columns
    story.append(
        Paragraph(
            "<b>【高压系统安全隔离与防电弧飞溅强制规程】</b> 拔插任何高压端子前必须断开低压蓄电池负极与主断路器 (MSD)，等待5分钟释放逆变器电容残余电压，并使用1000V绝缘棒进行验电确认零电位！",
            callout_style,
        )
    )
    story.append(Spacer(1, 8))

    # Zone 2: Three unequal columns (continuation)
    col1_z2 = [
        Paragraph("2.1 线束与总线检查", h1_style),
        Paragraph("检查CAN-FD总线终端电阻（正常阻值60 Ω），排查低压插头退针与氧化。", body_style),
    ]
    col2_z2 = [
        Paragraph("2.2 绝缘耐压打压测试", h1_style),
        Paragraph("使用DC 1000V高压绝缘表测量正极/负极对车身绝缘电阻，阻值必须 ≥ 500 MΩ。", body_style),
    ]
    col3_z2 = [
        Paragraph("2.3 终检验收与放行", h1_style),
        Paragraph("恢复MSD开关，连接诊断仪清除历史DTC，试车确认整车就绪指示灯(READY)点亮。", body_style),
    ]

    tbl_z2 = Table([[col1_z2, col2_z2, col3_z2]], colWidths=[155, 215, 153])
    tbl_z2.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(tbl_z2)

    def draw_3col_decor(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(36, 805, "AutoVend Asymmetric 3-Column Diagnostic & Labor Manual 2026")
        canvas.line(36, 800, 559, 800)
        canvas.drawString(36, 25, "非对称三栏排版规范 | 高压维修受控文件")
        canvas.drawRightString(559, 25, "Page 1 of 1")
        canvas.line(36, 35, 559, 35)
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=draw_3col_decor, onLaterPages=draw_3col_decor)
    print(f"Generated unequal 3-column specs PDF at: {output_path}")


if __name__ == "__main__":
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    _SAMPLE_DIR = _PROJECT_ROOT / "data" / "sample_specs"
    _SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    out_su7 = _SAMPLE_DIR / "xiaomi_su7_ultra_specs.pdf"
    generate_xiaomi_su7_pdf(out_su7)

    out_u9 = _SAMPLE_DIR / "byd_yangwang_u9_specs.pdf"
    generate_byd_yangwang_u9_pdf(out_u9)

    out_ent = _SAMPLE_DIR / "enterprise_multipage_specs.pdf"
    generate_enterprise_multipage_pdf(out_ent)

    out_3p = _SAMPLE_DIR / "enterprise_3page_scroll_specs.pdf"
    generate_enterprise_3page_continuous_table_pdf(out_3p)

    out_fin = _SAMPLE_DIR / "financial_autoloan_policy_specs.pdf"
    generate_financial_autoloan_pdf(out_fin)

    out_maint = _SAMPLE_DIR / "vehicle_maintenance_diagnostic_manual.pdf"
    generate_vehicle_maintenance_manual_pdf(out_maint)

    out_border = _SAMPLE_DIR / "irregular_borderless_specs.pdf"
    generate_irregular_borderless_specs_pdf(out_border)

    out_mixed = _SAMPLE_DIR / "mixed_orientation_enterprise_specs.pdf"
    generate_mixed_orientation_enterprise_specs_pdf(out_mixed)

    out_scan = _SAMPLE_DIR / "scanned_brochure_watermark_specs.pdf"
    generate_scanned_brochure_watermark_pdf(out_scan)

    out_border_multi = _SAMPLE_DIR / "enterprise_borderless_multipage_specs.pdf"
    generate_enterprise_borderless_multipage_pdf(out_border_multi)

    out_warr = _SAMPLE_DIR / "oem_warranty_maintenance_matrix.pdf"
    generate_oem_warranty_maintenance_matrix_pdf(out_warr)

    out_3col = _SAMPLE_DIR / "unequal_three_column_specs.pdf"
    generate_unequal_three_column_specs_pdf(out_3col)
