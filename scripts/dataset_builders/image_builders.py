"""
Image Dataset Builders for AutoVend Enterprise Benchmark.
Generates 13 high-resolution automotive infographics and diagnostic captures with EXIF metadata (.png, .jpg).
"""

import logging
import os
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("enterprise_dataset_gen.image")

CJK_FONT_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def _get_fonts(title_size=24, body_size=18):
    f_title, f_body = None, None
    for p in CJK_FONT_PATHS:
        if os.path.exists(p):
            try:
                f_title = ImageFont.truetype(p, title_size)
                f_body = ImageFont.truetype(p, body_size)
                break
            except Exception:
                pass
    return f_title, f_body


# 1. BYD e-Platform 3.0 Evo Infographic (PNG, 1920x1080)
def generate_byd_evo_image(out_dir: Path) -> Path:
    file_path = out_dir / "BYD_ePlatform_3_Evo_Infographic.png"
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(28, 18)

    # Frame
    draw.rectangle([40, 40, w - 40, h - 40], outline=(59, 130, 246), width=3)
    draw.rectangle([40, 40, w - 40, 120], fill=(30, 58, 138))
    draw.text((80, 60), "BYD e-Platform 3.0 Evo 全球首创十二合一智能电驱架构技术图解", fill=(255, 255, 255), font=f_title)

    # Content boxes
    boxes = [
        ("十二合一智能电驱", "最高转速 23,000 rpm | 综合系统效率 92.5%", (80, 160, 920, 560), (30, 41, 59)),
        ("CTB 2.0 电池车身一体化", "刀片电芯作为车身结构件 | 扭转刚度 40,000 N·m/°", (1000, 160, 1840, 560), (30, 41, 59)),
        ("全域 800V 高压碳化硅芯片", "升流超充与智能双枪超充技术 | 充电10分钟续航 400km", (80, 600, 920, 1000), (30, 41, 59)),
        ("智能运动控制 (iTAC)", "微秒级电机转矩闭环控制 | 冰雪路面打滑响应提速 300 倍", (1000, 600, 1840, 1000), (30, 41, 59)),
    ]
    for title, desc, coords, bg in boxes:
        draw.rectangle(coords, fill=bg, outline=(71, 85, 105), width=2)
        draw.text((coords[0] + 30, coords[1] + 30), title, fill=(96, 165, 250), font=f_title)
        draw.text((coords[0] + 30, coords[1] + 80), desc, fill=(226, 232, 240), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "BYD Auto Co., Ltd."
    exif[0x0110] = "e-Platform 3.0 Evo Studio"
    exif[0x0132] = "2026:01:10 10:00:00"
    exif[0x010E] = "BYD e-Platform 3.0 Evo 12-in-1 Powertrain Technical Diagram"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 2. NIO ET9 Steer-by-Wire Diagram (PNG, 1920x1080)
def generate_nio_sbw_image(out_dir: Path) -> Path:
    file_path = out_dir / "NIO_ET9_Steer_By_Wire_Diagram.png"
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(10, 25, 47))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(28, 18)

    draw.rectangle([40, 40, w - 40, h - 40], outline=(14, 165, 233), width=3)
    draw.rectangle([40, 40, w - 40, 120], fill=(3, 105, 161))
    draw.text((80, 60), "蔚来 ET9 天行线控转向系统 (Steer-by-Wire) 冗余电气拓扑图", fill=(255, 255, 255), font=f_title)

    draw.text((80, 160), "• 双无刷电机线控执行机构 (Dual Brushless DC Actuators)", fill=(56, 189, 248), font=f_title)
    draw.text((80, 210), "  - 取消方向盘与前转向节的机械中间轴物理连接，实现传动比 6:1 至 14:1 随速动态调节", fill=(224, 242, 254), font=f_body)
    draw.text((80, 260), "  - 双路独立 48V 电源供电与双路独立高速以太网总线通信，完全满足 ASIL-D 功能安全要求", fill=(224, 242, 254), font=f_body)

    # Diagram lines
    draw.rectangle([100, 340, 500, 540], fill=(15, 23, 42), outline=(56, 189, 248), width=2)
    draw.text((120, 360), "方向盘手感模拟器 (FFE)", fill=(255, 255, 255), font=f_body)
    draw.text((120, 410), "双霍尔角度传感器 A / B", fill=(148, 163, 184), font=f_body)
    draw.text((120, 460), "路感力矩电机 (阻尼反馈)", fill=(148, 163, 184), font=f_body)

    draw.line([(500, 440), (800, 440)], fill=(56, 189, 248), width=4)
    draw.text((550, 410), "以太网数字信号", fill=(255, 255, 255), font=f_body)

    draw.rectangle([800, 340, 1300, 540], fill=(15, 23, 42), outline=(56, 189, 248), width=2)
    draw.text((820, 360), "转向机执行器 (RWA)", fill=(255, 255, 255), font=f_body)
    draw.text((820, 410), "主执行电机 1 (Channel 1)", fill=(148, 163, 184), font=f_body)
    draw.text((820, 460), "热备冗余电机 2 (Channel 2)", fill=(148, 163, 184), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "NIO Inc."
    exif[0x0110] = "SkyRide Autonomous Labs"
    exif[0x0132] = "2026:01:15 14:30:00"
    exif[0x010E] = "NIO ET9 Steer-by-Wire Dual Channel Redundancy Schematic"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 3. Huawei DriveONE 800V SiC Motor Poster (PNG, 1920x1080)
def generate_huawei_motor_image(out_dir: Path) -> Path:
    file_path = out_dir / "Huawei_DriveONE_800V_SiC_Motor_Poster.png"
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(28, 18)

    draw.rectangle([40, 40, w - 40, h - 40], outline=(239, 68, 68), width=3)
    draw.rectangle([40, 40, w - 40, 120], fill=(185, 28, 28))
    draw.text((80, 60), "华为 DriveONE 800V 碳化硅高压黄金动力平台规格海报", fill=(255, 255, 255), font=f_title)

    draw.text((80, 180), "• 极速转速：25,000 rpm 行业顶尖水平", fill=(252, 165, 165), font=f_title)
    draw.text((80, 230), "• 综合系统效率：CLTC 工况综合效率高达 92.0%", fill=(255, 255, 255), font=f_body)
    draw.text((80, 280), "• 散热架构：智能双向全油冷技术，定子铁芯与转子内部直接润滑冷却", fill=(255, 255, 255), font=f_body)
    draw.text((80, 330), "• 功率密度：高集成度七合一总成，功率密度超 3.3 kW/kg", fill=(255, 255, 255), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Huawei Technologies Co., Ltd."
    exif[0x0110] = "DriveONE Powertrain Studio"
    exif[0x0132] = "2026:01:20 09:15:00"
    exif[0x010E] = "Huawei DriveONE 800V High Voltage SiC Electric Drive Architecture"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 4. Tesla Model Y Structural Battery Pack (PNG, 1920x1080)
def generate_tesla_pack_image(out_dir: Path) -> Path:
    file_path = out_dir / "Tesla_Model_Y_Structural_Battery_Pack.png"
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(18, 18, 18))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(28, 18)

    draw.rectangle([40, 40, w - 40, h - 40], outline=(220, 38, 38), width=3)
    draw.rectangle([40, 40, w - 40, 120], fill=(153, 27, 27))
    draw.text((80, 60), "Tesla Model Y 结构化 4680 电池包与前后一体大压铸底盘解析图", fill=(255, 255, 255), font=f_title)

    draw.text((80, 180), "• 前后一体式超大型铝合金压铸件 (Front & Rear Mega-Castings)", fill=(248, 113, 113), font=f_title)
    draw.text((80, 230), "  - 减少 170 多个零部件，消减 1600 多个焊点，车身底盘刚度提升 35%", fill=(229, 231, 235), font=f_body)
    draw.text((80, 290), "• 结构化电池包 (Structural Battery Pack) 作为车身承力地板", fill=(248, 113, 113), font=f_title)
    draw.text((80, 340), "  - 4680 大圆柱电芯直接胶粘在上下蜂窝托盘之间，座椅直接螺栓紧固于电池包上盖", fill=(229, 231, 235), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Tesla, Inc."
    exif[0x0110] = "Gigafactory Texas"
    exif[0x0132] = "2026:01:25 11:20:00"
    exif[0x010E] = "Tesla Model Y Mega-Casting and Structural Pack Architecture Diagram"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 5. Li L9 Magic Carpet Suspension Diagram (PNG, 1920x1080)
def generate_li_susp_image(out_dir: Path) -> Path:
    file_path = out_dir / "Li_L9_Magic_Carpet_Suspension_Diagram.png"
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(28, 18)

    draw.rectangle([40, 40, w - 40, h - 40], outline=(16, 185, 129), width=3)
    draw.rectangle([40, 40, w - 40, 120], fill=(5, 150, 105))
    draw.text((80, 60), "理想 L9 魔毯空气悬架 2.0 (双腔空簧 + CDC 连续阻尼) 原理图", fill=(255, 255, 255), font=f_title)

    draw.text((80, 180), "• 双腔空气弹簧：主腔与副腔电控阀门微秒级切换，实现刚度与高度解耦控制", fill=(110, 231, 183), font=f_title)
    draw.text((80, 230), "• CDC 毫秒级阻尼调节：每秒 1000 次路面扫描，提前主动预判颠簸路况", fill=(241, 245, 249), font=f_body)
    draw.text((80, 280), "• 闭式空气供给系统：充放气速度提高 50%，高海拔低气压工况表现依旧稳定", fill=(241, 245, 249), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Li Auto Inc."
    exif[0x0110] = "Chassis R&D Center"
    exif[0x0132] = "2026:01:28 16:40:00"
    exif[0x010E] = "Li Auto Magic Carpet Air Suspension Dual Chamber System Diagram"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 6. Zeekr 001 ZVC Torque Vectoring Poster (PNG, 1920x1080)
def generate_zeekr_zvc_image(out_dir: Path) -> Path:
    file_path = out_dir / "Zeekr_001_ZVC_Torque_Vectoring_Poster.png"
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(26, 26, 46))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(28, 18)

    draw.rectangle([40, 40, w - 40, h - 40], outline=(245, 158, 11), width=3)
    draw.rectangle([40, 40, w - 40, 120], fill=(217, 119, 6))
    draw.text((80, 60), "极氪 001 FR 四电机 ZVC 极氪扭矩矢量控制系统技术海报", fill=(255, 255, 255), font=f_title)

    draw.text((80, 180), "• 四电机独立控制：前双电机 310kW + 后双电机 620kW，综合 1300 马力", fill=(252, 211, 77), font=f_title)
    draw.text((80, 230), "• ZVC 毫秒级转矩分配：弯道内外侧车轮精准反向分配扭矩，抑制转向不足", fill=(254, 243, 199), font=f_body)
    draw.text((80, 280), "• 坦克掉头黑科技：左右侧车轮以相同转速反向旋转，实现原地 360 度自转", fill=(254, 243, 199), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Zeekr Intelligent Technology"
    exif[0x0110] = "ZVC Dynamics Lab"
    exif[0x0132] = "2026:02:01 13:00:00"
    exif[0x010E] = "Zeekr 001 FR Quad Motor Torque Vectoring Control Poster"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 7. Porsche Active Ride Suspension Poster (PNG, 1920x1080)
def generate_porsche_active_ride_image(out_dir: Path) -> Path:
    file_path = out_dir / "Porsche_Active_Ride_Suspension_Poster.png"
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(17, 24, 39))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(28, 18)

    draw.rectangle([40, 40, w - 40, h - 40], outline=(168, 85, 247), width=3)
    draw.rectangle([40, 40, w - 40, 120], fill=(126, 34, 206))
    draw.text((80, 60), "保时捷主动悬架系统 (Porsche Active Ride) 电驱液压工作原理海报", fill=(255, 255, 255), font=f_title)

    draw.text((80, 180), "• 取消防倾杆：四个减振支柱各集成一组由 400V 高压电机驱动的液压马达泵", fill=(216, 180, 254), font=f_title)
    draw.text((80, 230), "• 弯道主动倾斜：车辆在激烈过弯时像摩托车一样主动向弯心倾斜，完全抵消侧倾", fill=(243, 232, 255), font=f_body)
    draw.text((80, 280), "• 刹车与起步零俯仰：全力加速不抬头，紧急制动不点头，车身保持绝对水平", fill=(243, 232, 255), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Porsche AG"
    exif[0x0110] = "Weissach Chassis Dynamics"
    exif[0x0132] = "2026:02:05 10:10:00"
    exif[0x010E] = "Porsche Active Ride Electro-Hydraulic Suspension Architecture"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 8. Tesla Model 3 VIN Plate Label (JPG, 1280x720)
def generate_tesla_vin_image(out_dir: Path) -> Path:
    file_path = out_dir / "Tesla_Model_3_VIN_Plate_Label.jpg"
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(22, 16)

    # Label sticker
    draw.rectangle([100, 80, 1180, 640], fill=(245, 245, 245), outline=(0, 0, 0), width=4)
    draw.text((140, 110), "MFD BY TESLA MOTORS, INC.  /  特斯拉汽车制造铭牌", fill=(0, 0, 0), font=f_title)
    draw.line([(140, 150), (1140, 150)], fill=(0, 0, 0), width=2)

    specs = [
        "VIN:  LRW3E7EK9RC123456 (上海超级工厂制造)",
        "GVWR (最大设计总质量):  2,250 kg",
        "GAWR FRONT (前轴额定承载):  1,110 kg",
        "GAWR REAR (后轴额定承载):  1,250 kg",
        "COLD TIRE INFLATION (冷态胎压):  前/后 235/40R19 42 PSI (2.9 bar)",
        "PAINT COLOR CODE (车漆代码):  PMNG (Midnight Silver Metallic)",
        "PRODUCTION DATE (制造日期):  01/2026",
    ]
    for idx, s in enumerate(specs):
        draw.text((140, 180 + idx * 55), s, fill=(0, 0, 0), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Apple"
    exif[0x0110] = "iPhone 15 Pro Max"
    exif[0x0132] = "2026:02:10 12:45:00"
    exif[0x010E] = "Tesla Model 3 B-Pillar VIN Certification Plate High Res Capture"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 9. BYD Han EV Instrument BMS Warning (JPG, 1280x720)
def generate_byd_warning_image(out_dir: Path) -> Path:
    file_path = out_dir / "BYD_Han_EV_Instrument_BMS_Warning.jpg"
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), color=(10, 10, 15))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(22, 16)

    draw.rectangle([50, 50, w - 50, h - 50], outline=(70, 70, 80), width=3)
    draw.rectangle([400, 150, 880, 480], fill=(20, 20, 25), outline=(220, 38, 38), width=3)
    draw.text((450, 200), "高压系统绝缘故障 警告", fill=(239, 68, 68), font=f_title)
    draw.text((450, 260), "故障码: P1A0200 (绝缘阻抗偏低)", fill=(248, 113, 113), font=f_body)
    draw.text((450, 310), "动力受限: 已进入小乌龟低速蠕行保护模式", fill=(251, 191, 36), font=f_body)
    draw.text((450, 360), "请立即靠边停车，联系比亚迪官方救援", fill=(203, 213, 225), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Xiaomi"
    exif[0x0110] = "Xiaomi 14 Ultra"
    exif[0x0132] = "2026:02:12 15:30:00"
    exif[0x010E] = "BYD Han EV High Voltage Insulation Fault and Turtle Power Limit Display"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 10. NIO ES8 HUD Navigation Display (JPG, 1280x720)
def generate_nio_hud_image(out_dir: Path) -> Path:
    file_path = out_dir / "NIO_ES8_HUD_Navigation_Display.jpg"
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), color=(5, 10, 20))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(22, 16)

    # HUD projection area
    draw.text((250, 200), "NOP+ 全域领航辅助 已激活", fill=(56, 189, 248), font=f_title)
    draw.text((250, 260), "巡航车速: 118 km/h  |  限速: 120 km/h", fill=(255, 255, 255), font=f_body)
    draw.text((250, 310), "车道提示: 200米后 向右平顺变道至主道", fill=(52, 211, 153), font=f_body)
    draw.text((250, 360), "行人避让感知: 绿灯倒计时 15 秒", fill=(203, 213, 225), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "NIO Inc."
    exif[0x0110] = "HUD Camera Rig"
    exif[0x0132] = "2026:02:15 19:20:00"
    exif[0x010E] = "NIO ES8 PanoCinema Head-Up Display NOP+ Active Projection"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 11. Li L8 Energy Efficiency Window Sticker (JPG, 1280x720)
def generate_li_window_sticker_image(out_dir: Path) -> Path:
    file_path = out_dir / "Li_L8_Energy_Efficiency_Window_Sticker.jpg"
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(22, 16)

    draw.rectangle([60, 60, w - 60, h - 60], outline=(0, 100, 0), width=4)
    draw.rectangle([60, 60, w - 60, 130], fill=(34, 139, 34))
    draw.text((100, 80), "中国能源消耗量标识 (轻型汽车) • 理想 L8 Max 增程式", fill=(255, 255, 255), font=f_title)

    rows = [
        "汽车生产企业: 北京理想汽车有限公司",
        "车辆型号: LXA6510PHEV1",
        "综合工况燃料消耗量 (WLTC): 0.75 L / 100km (电量保持模式: 7.7 L/100km)",
        "纯电工况电能消耗量 (WLTC): 21.9 kWh / 100km",
        "纯电续航里程 (CLTC / WLTC): 225 km / 176 km",
        "综合续航里程: 1,160 km",
        "燃料种类: 95号无铅汽油 + 电",
    ]
    for idx, r in enumerate(rows):
        draw.text((100, 160 + idx * 60), r, fill=(0, 0, 0), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Canon"
    exif[0x0110] = "Canon EOS R5"
    exif[0x0132] = "2026:02:18 10:05:00"
    exif[0x010E] = "Li Auto L8 MIIT Official Energy Consumption Window Sticker"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 12. XPeng X9 Cluster NGP Active (JPG, 1280x720)
def generate_xpeng_cluster_image(out_dir: Path) -> Path:
    file_path = out_dir / "XPeng_X9_Cluster_NGP_Active.jpg"
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), color=(15, 20, 30))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(22, 16)

    draw.rectangle([50, 50, w - 50, h - 50], outline=(0, 150, 255), width=2)
    draw.text((100, 120), "小鹏 XNGP 城市全场景无图智能辅助驾驶已激活", fill=(56, 189, 248), font=f_title)
    draw.text((100, 180), "当前车速: 62 km/h  |  道路最高限速: 60 km/h", fill=(255, 255, 255), font=f_body)
    draw.text((100, 230), "感知状态: 192线激光雷达 + 双 Orin-X 算力平台 (508 TOPS) 运行平稳", fill=(52, 211, 153), font=f_body)
    draw.text((100, 280), "目标意图: 正在识别前方大货车，即将执行向左自主变道超车", fill=(251, 191, 36), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "DJI"
    exif[0x0110] = "Osmo Pocket 3"
    exif[0x0132] = "2026:02:20 16:15:00"
    exif[0x010E] = "XPeng X9 Digital Cockpit XNGP City Navigation Active Capture"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


# 13. BMW i4 Tire Pressure TPMS Alert (JPG, 1280x720)
def generate_bmw_tpms_image(out_dir: Path) -> Path:
    file_path = out_dir / "BMW_i4_Tire_Pressure_TPMS_Alert.jpg"
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    f_title, f_body = _get_fonts(22, 16)

    draw.rectangle([50, 50, w - 50, h - 50], outline=(220, 38, 38), width=3)
    draw.text((100, 120), "BMW iDrive 轮胎失压报警 (Tyre Pressure Loss)", fill=(239, 68, 68), font=f_title)
    draw.text((100, 180), "右前轮气压急剧下降: 1.2 bar (标准 2.4 bar)", fill=(248, 113, 113), font=f_body)
    draw.text((100, 230), "左前轮: 2.4 bar | 左后轮: 2.5 bar | 右后轮: 2.5 bar", fill=(203, 213, 225), font=f_body)
    draw.text((100, 280), "警告提示: 请勿急刹车或大角度转向，尽快安全靠边停驶！", fill=(251, 191, 36), font=f_body)

    exif = img.getexif()
    exif[0x010F] = "Samsung"
    exif[0x0110] = "Galaxy S24 Ultra"
    exif[0x0132] = "2026:02:22 17:40:00"
    exif[0x010E] = "BMW i4 RDC Tire Puncture Pressure Loss Critical Warning"
    img.save(file_path, exif=exif)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_all_new_image_datasets(out_dir: Path) -> List[Path]:
    """Generate all 13 new Image benchmark datasets."""
    generators = [
        generate_byd_evo_image,
        generate_nio_sbw_image,
        generate_huawei_motor_image,
        generate_tesla_pack_image,
        generate_li_susp_image,
        generate_zeekr_zvc_image,
        generate_porsche_active_ride_image,
        generate_tesla_vin_image,
        generate_byd_warning_image,
        generate_nio_hud_image,
        generate_li_window_sticker_image,
        generate_xpeng_cluster_image,
        generate_bmw_tpms_image,
    ]
    results = []
    for g in generators:
        results.append(g(out_dir))
    return results
