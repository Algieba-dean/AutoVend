"""
PDF Dataset Builders for AutoVend Enterprise Benchmark.
Generates 9 high-quality, realistic automotive multi-page PDF specification manuals (.pdf) using PyMuPDF.
"""

import logging
import os
from pathlib import Path
from typing import List

import pymupdf as fitz

logger = logging.getLogger("enterprise_dataset_gen.pdf")

CJK_FONT_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def _get_cjk_font():
    for p in CJK_FONT_PATHS:
        if os.path.exists(p):
            return p
    return None


def _setup_page(doc, title_banner: str, page_num: int, total_pages: int = 3):
    page = doc.new_page(width=595, height=842)
    font_file = _get_cjk_font()
    if font_file:
        page.insert_font(fontname="cjk", fontfile=font_file)
        fn = "cjk"
    else:
        fn = "china-s"

    # Header
    page.insert_text((50, 40), title_banner, fontname=fn, fontsize=8.5, color=(0.3, 0.4, 0.5))
    page.draw_line(fitz.Point(50, 48), fitz.Point(545, 48), color=(0.8, 0.8, 0.85), width=0.8)

    # Footer
    page.draw_line(fitz.Point(50, 800), fitz.Point(545, 800), color=(0.8, 0.8, 0.85), width=0.8)
    page.insert_text((50, 815), f"Page {page_num} of {total_pages} • 官方技术受控文档 • 机密级", fontname=fn, fontsize=8.5, color=(0.4, 0.4, 0.5))

    return page, fn


def _draw_table(page, fn, start_y: float, headers: List[str], col_x: List[float], rows: List[List[str]], row_height: float = 28.0):
    # Header background
    page.draw_rect(fitz.Rect(50, start_y, 545, start_y + 24), fill=(0.15, 0.35, 0.6))
    for i, h in enumerate(headers):
        page.insert_text((col_x[i], start_y + 16), h, fontname=fn, fontsize=9.5, color=(1, 1, 1))

    cur_y = start_y + 24
    for r in rows:
        page.draw_line(fitz.Point(50, cur_y), fitz.Point(545, cur_y), color=(0.85, 0.85, 0.85), width=0.5)
        for i, val in enumerate(r):
            page.insert_text((col_x[i], cur_y + 18), str(val), fontname=fn, fontsize=8.5, color=(0.15, 0.15, 0.15))
        cur_y += row_height
    return cur_y


# 1. Xiaomi SU7 Owners Quick Start Manual (3 pages)
def generate_xiaomi_su7_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "Xiaomi_SU7_Owners_Quick_Start_Manual.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "XIAOMI SU7 OWNER QUICK START MANUAL • 小米汽车车主操作指引", 1)
    p1.insert_text((50, 75), "小米 SU7 车主快速上手与智能互联操作手册", fontname=fn, fontsize=15, color=(0.1, 0.2, 0.4))
    p1.insert_text((50, 98), "适用车型: 小米 SU7 标准版 / Pro 版 / Max 版 / Ultra 量产版", fontname=fn, fontsize=9.5, color=(0.4, 0.4, 0.4))

    headers1 = ["钥匙形式", "解锁方式", "有效感应距离", "电量耗尽应急操作"]
    col_x1 = [55, 170, 310, 420]
    rows1 = [
        ["手机蓝牙无感钥匙", "靠近车辆 1.5 米内自动解锁", "0 - 10 米", "通过小米汽车 App 远程云端解锁"],
        ["NFC 智能卡片钥匙", "贴合主驾 B 柱感应区域", "0 - 3 cm", "物理芯片无源工作，无需电池"],
        ["实体机械备用钥匙", "按压把手尾部拔出机械钥匙孔", "接触式", "直接插入主驾车门物理机械锁孔"],
    ]
    _draw_table(p1, fn, 120, headers1, col_x1, rows1)

    p2, fn = _setup_page(doc, "XIAOMI SU7 OWNER QUICK START MANUAL • 充电与高压安全", 2)
    p2.insert_text((50, 75), "800V 碳化硅高压超充与慢充指示灯规范", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers2 = ["指示灯颜色与状态", "当前工作状态", "输出功率范围", "操作建议"]
    col_x2 = [55, 180, 320, 430]
    rows2 = [
        ["白色常亮", "充电枪已插好未开始", "0 kW", "在车机端或手机端确认支付与充电"],
        ["绿色呼吸渐变", "高压直流快充中", "最高可达 350 kW", "充电中切勿强行拔出充电枪"],
        ["蓝色常亮", "交流家用慢充中", "7 kW", "充满后车辆将自动断电防过充"],
        ["红色常亮/闪烁", "系统检测到故障告警", "0 kW", "请拔枪重试或联系小米官方热线"],
    ]
    _draw_table(p2, fn, 110, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "XIAOMI SU7 OWNER QUICK START MANUAL • 空气动力学与尾翼", 3)
    p3.insert_text((50, 75), "电动升降尾翼 4 挡位角度与下压力设定", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers3 = ["尾翼挡位", "迎风仰角 (°)", "最大下压力 (kg)", "适用驾驶工况与车速"]
    col_x3 = [55, 170, 300, 420]
    rows3 = [
        ["0 挡 (收回模式)", "0° 平齐", "0 kg", "市区低速行驶，保持最低风阻 0.195"],
        ["1 挡 (破风模式)", "5°", "18 kg", "车速达 90km/h 自动升起，降低紊流"],
        ["2 挡 (耐力模式)", "12°", "45 kg", "高速 120km/h 巡航，兼顾下压力与能耗"],
        ["3 挡 (极限下压力)", "25°", "130 kg (Max版)", "赛道模式/运动+，最大化制动稳定性"],
    ]
    _draw_table(p3, fn, 110, headers3, col_x3, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


# 2. BYD Yangwang U8 Technical Spec Sheet (3 pages)
def generate_yangwang_u8_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "BYD_Yangwang_U8_Technical_Spec_Sheet.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "YANGWANG U8 OFFICIAL TECHNICAL SPEC SHEET • 仰望 U8 规格手册", 1)
    p1.insert_text((50, 75), "仰望 U8 豪华版 / 越野玩家版 整车尺寸与通过性指标", fontname=fn, fontsize=15, color=(0.1, 0.2, 0.4))

    headers = ["规格参数维度", "豪华版官方指标", "越野玩家版官方指标", "通过性意义解析"]
    col_x = [55, 180, 310, 430]
    rows = [
        ["整车长 × 宽 × 高", "5319 × 2050 × 1930 mm", "5319 × 2050 × 1930 mm", "大型硬派豪华越野SUV"],
        ["轴距 (Wheelbase)", "3050 mm", "3050 mm", "车内三排超宽敞乘坐体验"],
        ["接近角 / 离去角", "36.5° / 35.4°", "37.5° / 36.4°", "大角度陡坡无刮碰爬升"],
        ["最大涉水深度", "1000 mm", "1400 mm (带涉水喉)", "行业顶尖全地形涉水能力"],
    ]
    _draw_table(p1, fn, 110, headers, col_x, rows)

    p2, fn = _setup_page(doc, "YANGWANG U8 OFFICIAL TECHNICAL SPEC SHEET • 易四方动力总成", 2)
    p2.insert_text((50, 75), "易四方四电机独立驱动系统动力输出矩阵", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers2 = ["电机分布位置", "额定/峰值功率 (kW)", "峰值扭矩 (N·m)", "最高转速 (rpm)", "技术特性"]
    col_x2 = [55, 170, 280, 380, 460]
    rows2 = [
        ["左前轮驱动电机", "110 / 220 kW", "320 N·m", "20,500 rpm", "独立逆变器精准矢量调速"],
        ["右前轮驱动电机", "110 / 220 kW", "320 N·m", "20,500 rpm", "独立正反转支持差速调头"],
        ["左后轮驱动电机", "110 / 220 kW", "320 N·m", "20,500 rpm", "集成机械驻车锁止齿轮"],
        ["右后轮驱动电机", "110 / 220 kW", "320 N·m", "20,500 rpm", "集成机械驻车锁止齿轮"],
        ["整车综合动力", "440 / 880 kW (1197 PS)", "1280 N·m", "综合零百 3.6 秒", "四轮动力独立微秒级自适应"],
    ]
    _draw_table(p2, fn, 110, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "YANGWANG U8 OFFICIAL TECHNICAL SPEC SHEET • 云辇-P 悬架", 3)
    p3.insert_text((50, 75), "云辇-P 智能液压车身控制系统性能指标", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers3 = ["控制维度", "技术设计指标", "工作响应时间", "实际应用场景"]
    col_x3 = [55, 180, 310, 420]
    rows3 = [
        ["悬架高度调节总行程", "150 mm (抬升+下降)", "< 5 秒", "越野抬高通过，高速降低风阻"],
        ["三级阻尼与刚度调节", "软/中/硬 自适应", "10 毫秒", "高速过弯抑制侧倾，颠簸路过滤震动"],
        ["四轮液压联动平衡", "对角油路压力互通", "微秒级", "单轮悬空时将重力转移至着地轮"],
    ]
    _draw_table(p3, fn, 110, headers3, col_x3, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


# 3. NIO ET7 Executive Sedan Brochure (3 pages)
def generate_nio_et7_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "NIO_ET7_Executive_Sedan_Brochure.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "NIO ET7 EXECUTIVE SEDAN BROCHURE • 蔚来 ET7 行政旗舰手册", 1)
    p1.insert_text((50, 75), "蔚来 ET7 智能电动行政旗舰轿车设计哲学与座舱空间", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers = ["空间与材质维度", "ET7 旗舰配置指标", "豪华质感与舒适价值"]
    col_x = [55, 200, 380]
    rows = [
        ["整车尺寸与轴距", "5101 × 1987 × 1509 mm, 轴距 3060 mm", "宽奢行政级纵向与横向后排空间"],
        ["专属内饰材质", "Karuun 可再生热带藤木饰板 + 可持续天然材质", "每一片木纹自然唯一，彰显环保理念"],
        ["座椅舒适性", "前后排标配座椅加热、通风与 16 点石墨烯热石按摩", "长途差旅中享受头等舱级舒缓放松"],
    ]
    _draw_table(p1, fn, 110, headers, col_x, rows)

    p2, fn = _setup_page(doc, "NIO ET7 EXECUTIVE SEDAN BROCHURE • PanoCinema 声学座舱", 2)
    p2.insert_text((50, 75), "PanoCinema 全景数字座舱与 7.1.4 空间音频", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers2 = ["声学系统组成", "扬声器数量与功率", "支持音频解码格式"]
    col_x2 = [55, 230, 400]
    rows2 = [
        ["全车扬声器单元", "23 个高品质扬声器，总功率达 1000 W", "杜比全景声 (Dolby Atmos) 原生支持"],
        ["四路车顶天空声道", "4 个独立高位反射单元", "构建真正三维立体环绕声场"],
        ["重低音炮单元", "前围双音圈大冲程重低音单元", "低频下潜可达 20 Hz"],
    ]
    _draw_table(p2, fn, 110, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "NIO ET7 EXECUTIVE SEDAN BROCHURE • Aquila 超感系统", 3)
    p3.insert_text((50, 75), "Aquila 蔚来超感系统感知硬件规格表", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers3 = ["感知硬件类型", "硬件配置数量", "探测距离与视场角", "主要负责感知功能"]
    col_x3 = [55, 170, 280, 410]
    rows3 = [
        ["超远距高精激光雷达", "1 颗 (1550nm 猎鹰激光雷达)", "最远 500 米 / 120° FOV", "车顶瞭望塔布局，前向高精避障"],
        ["800万高清感知相机", "11 颗 (前视+环视+侧视)", "探测距离超 680 米", "视觉全场景车道线与障碍物识别"],
        ["毫米波雷达群", "5 个五代毫米波雷达", "最远 210 米", "雨雪恶劣天气目标穿透检测"],
        ["Adam 超算平台", "4 颗 NVIDIA Drive Orin 芯片", "算力高达 1016 TOPS", "支撑 NAD 全自动领航算法架构"],
    ]
    _draw_table(p3, fn, 110, headers3, col_x3, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


# 4. Tesla Model S Plaid Track Package Manual (3 pages)
def generate_tesla_plaid_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "Tesla_Model_S_Plaid_Track_Package_Manual.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "TESLA MODEL S PLAID TRACK PACKAGE MANUAL • 赛道套件手册", 1)
    p1.insert_text((50, 75), "Tesla Model S Plaid 赛道性能套件与碳陶制动系统规范", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers = ["赛道套件部件", "规格与尺寸", "材质工艺", "赛用工况性能提升"]
    col_x = [55, 180, 310, 430]
    rows = [
        ["前碳陶制动盘", "Ф 410 × 40 mm", "碳化硅碳纤维复合材料", "极限耐温超 1000℃ 零衰退"],
        ["后碳陶制动盘", "Ф 410 × 32 mm", "碳化硅碳纤维复合材料", "大幅减轻簧下质量 24 kg"],
        ["一体化锻造制动卡钳", "前 6 活塞 / 后 4 活塞", "高刚度一体铝合金锻造", "制动脚感极为线性质感"],
        ["赛道高温制动液", "DOT 4 赛道专用", "干沸点 > 325 ℃", "防止极端制动气阻失效"],
    ]
    _draw_table(p1, fn, 110, headers, col_x, rows)

    p2, fn = _setup_page(doc, "TESLA MODEL S PLAID TRACK PACKAGE MANUAL • 轮毂与轮胎", 2)
    p2.insert_text((50, 75), "20英寸 Zero-G 锻造轮毂与赛道热熔胎规格", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers2 = ["车轮安装轴向", "轮毂规格尺寸", "匹配赛道轮胎型号", "冷态赛道气压建议"]
    col_x2 = [55, 180, 310, 440]
    rows2 = [
        ["前轴车轮 (Front)", "20 × 9.5J ET40 锻造铝", "Goodyear Eagle F1 285/35R20", "2.1 bar (热态目标 2.6 bar)"],
        ["后轴车轮 (Rear)", "20 × 10.5J ET40 锻造铝", "Goodyear Eagle F1 305/30R20", "2.1 bar (热态目标 2.6 bar)"],
    ]
    _draw_table(p2, fn, 110, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "TESLA MODEL S PLAID TRACK PACKAGE MANUAL • 赛道模式V2", 3)
    p3.insert_text((50, 75), "Track Mode V2 赛道界面动态扭矩与散热设定表", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers3 = ["调节功能参数", "可调节范围", "默认赛道推荐设定", "车辆动态行为表现"]
    col_x3 = [55, 170, 300, 420]
    rows3 = [
        ["前后动力分配比例", "100:0 (前驱) 至 0:100 (后驱)", "30:70 (偏后驱模式)", "入弯灵活出弯动力强劲"],
        ["电子稳定性控制 (ESC)", "100% (全开) 至 0% (完全关闭)", "20% (赛道滑动模式)", "允许适度漂移攻弯同时兜底安全"],
        ["能量回收制动强度", "0% 至 100%", "80%", "入弯松油门强减速建立前轴载荷"],
    ]
    _draw_table(p3, fn, 110, headers3, col_x3, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


# 5. Li Auto L7 Maintenance Schedule Guide (3 pages)
def generate_li_l7_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "Li_Auto_L7_Maintenance_Schedule_Guide.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "LI AUTO L7 PERIODIC MAINTENANCE GUIDE • 理想 L7 定期保养指南", 1)
    p1.insert_text((50, 75), "理想 L7 增程电动系统 10,000 至 50,000 公里保养项目表", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers = ["行驶里程 / 时间间隔", "机油及滤清器", "空调滤芯", "空气滤清器", "火花塞检查"]
    col_x = [55, 180, 280, 380, 470]
    rows = [
        ["10,000 km / 12个月", "更换 0W-20 机油", "检查清洁", "检查清洁", "免检"],
        ["20,000 km / 24个月", "更换 0W-20 机油", "必须更换", "必须更换", "免检"],
        ["30,000 km / 36个月", "更换 0W-20 机油", "检查清洁", "检查清洁", "免检"],
        ["40,000 km / 48个月", "更换 0W-20 机油", "必须更换", "必须更换", "全部更换4只"],
        ["50,000 km / 60个月", "更换 0W-20 机油", "检查清洁", "检查清洁", "免检"],
    ]
    _draw_table(p1, fn, 110, headers, col_x, rows)

    p2, fn = _setup_page(doc, "LI AUTO L7 PERIODIC MAINTENANCE GUIDE • 三电与底盘油液", 2)
    p2.insert_text((50, 75), "三电冷却系统防冻液与制动液检测更换周期", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers2 = ["关键液体油品", "标准规格型号", "系统总加注容量", "建议更换周期"]
    col_x2 = [55, 180, 310, 430]
    rows2 = [
        ["动力电池冷却液", "高绝缘有机型 OAT (-40℃)", "8.5 L", "4 年 或 80,000 公里"],
        ["增程发动机冷却液", "长效防冻液 (-40℃)", "6.8 L", "4 年 或 80,000 公里"],
        ["前后电驱减速箱油", "长城/壳牌纯电专用传动油", "前 1.1L / 后 1.4L", "6 年 或 120,000 公里"],
        ["全车液压制动液", "DOT 4 Plus 高温制动液", "1.0 L", "2 年 或 40,000 公里"],
    ]
    _draw_table(p2, fn, 110, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "LI AUTO L7 PERIODIC MAINTENANCE GUIDE • 易损件保修规范", 3)
    p3.insert_text((50, 75), "易损易耗零部件官方质保期及维保承诺说明", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers3 = ["易损零部件类别", "质保期限 (时间/里程)", "日常维护注意事项", "索赔保修条件"]
    col_x3 = [55, 180, 310, 430]
    rows3 = [
        ["雨刮片胶条", "6 个月 或 10,000 公里", "定期清洗风挡，避免干刮", "胶条自然开裂无外力划伤"],
        ["遥控钥匙纽扣电池", "12 个月", "车机低电量提示时更换", "电池电压过低无法搜寻感应"],
        ["保险丝与普通继电器", "12 个月 或 20,000 公里", "严禁私自改装超功率电器", "无私接高压或涉水短路痕迹"],
    ]
    _draw_table(p3, fn, 110, headers3, col_x3, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


# 6. Zeekr 007 Silicon Carbide Architecture Spec (3 pages)
def generate_zeekr_007_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "Zeekr_007_Silicon_Carbide_Architecture_Spec.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "ZEEKR 007 TECHNICAL SPECIFICATION • 全栈 800V 架构", 1)
    p1.insert_text((50, 75), "极氪 007 全栈 800V 高压架构与碳化硅电驱动总成技术表", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers = ["三电核心系统", "技术指标规格", "供应商 / 自研属性", "用户端体验收益"]
    col_x = [55, 180, 310, 430]
    rows = [
        ["后驱主电机总成", "310 kW 碳化硅永磁同步电机", "威睿电动全栈自研", "后驱零百加速 5.4 秒，动力输出强劲"],
        ["四驱前感应电机", "165 kW 交流异步感应电驱", "威睿电动全栈自研", "四驱版综合 475 kW，零百弹射 2.84 秒"],
        ["碳化硅功率模块", "全域 800V SiC 芯片功率管", "自研封测技术", "最高效率 99.5%，高温大负荷发热减少 50%"],
    ]
    _draw_table(p1, fn, 110, headers, col_x, rows)

    p2, fn = _setup_page(doc, "ZEEKR 007 TECHNICAL SPECIFICATION • 金砖与麒麟双电池", 2)
    p2.insert_text((50, 75), "金砖磷酸铁锂 (75kWh) 与麒麟三元锂 (100kWh) 对比", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers2 = ["对比项目", "自研金砖电池包 (75 kWh)", "宁德时代麒麟电池包 (100 kWh)"]
    col_x2 = [55, 200, 380]
    rows2 = [
        ["电芯化学材料", "高能量密度短刀磷酸铁锂 (LFP)", "高能量密度三元锂电芯 (NMC)"],
        ["CLTC 最大续航", "688 km (后驱)", "870 km (后驱长续航)"],
        ["最高充电倍率", "4.5C 极速充电", "4C 极速充电"],
        ["充电补能效率", "充电 15 分钟增加续航 500 km", "充电 15 分钟增加续航 610 km"],
    ]
    _draw_table(p2, fn, 110, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "ZEEKR 007 TECHNICAL SPECIFICATION • 智能座舱与智驾", 3)
    p3.insert_text((50, 75), "高通 8295 芯片与浩瀚智驾系统硬件配置单", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers3 = ["智能化硬件分区", "搭载元器件型号", "运算性能指标", "核心支持功能"]
    col_x3 = [55, 180, 310, 430]
    rows3 = [
        ["智能座舱主控", "高通 8295 旗舰车机芯片", "AI 算力 30 TOPS", "KR AI 语言大模型与 3D 沉浸车控"],
        ["高阶辅助驾驶", "双 NVIDIA DRIVE Orin-X", "综合算力 508 TOPS", "浩瀚智驾 2.0 高速与城市领航 NZP"],
        ["激光雷达总成", "1 颗顶置超远距激光雷达", "128 线，最远探测 200 米", "暗光与逆光微小障碍物高精避障"],
    ]
    _draw_table(p3, fn, 110, headers3, col_x3, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


# 7. Huawei AITO M7 Ultra Homologation Sheet (3 pages)
def generate_aito_m7_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "Huawei_AITO_M7_Ultra_Homologation_Sheet.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "AITO M7 ULTRA HOMOLOGATION SHEET • 问界 M7 工信部准入参数", 1)
    p1.insert_text((50, 75), "问界新 M7 Ultra 工信部道路机动车辆产品准入申报参数表", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers = ["国家申报技术指标", "单电机后驱版数据", "双电机四驱版数据", "国标符合依据"]
    col_x = [55, 180, 310, 430]
    rows = [
        ["整备质量 (kg)", "2370 kg", "2460 kg", "GB/T 12676 制动达标"],
        ["最大允许总质量", "2830 kg", "2920 kg", "额定载客 5/6 人"],
        ["前悬 / 后悬 (mm)", "945 mm / 1155 mm", "945 mm / 1155 mm", "外廓尺寸 GB 1589-2016"],
        ["最高车速 (km/h)", "190 km/h", "190 km/h", "电子安全最高限速"],
    ]
    _draw_table(p1, fn, 110, headers, col_x, rows)

    p2, fn = _setup_page(doc, "AITO M7 ULTRA HOMOLOGATION SHEET • 发动机与驱动电机", 2)
    p2.insert_text((50, 75), "H15RT 增程器与 DriveONE 驱动电机技术参数备案", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers2 = ["动力单元型号", "制造企业", "排量 / 额定功率", "最大净功率 (kW)"]
    col_x2 = [55, 180, 310, 430]
    rows2 = [
        ["1.5T 增程器 H15RT", "重庆小康动力有限公司", "1498 mL / 40 kW", "112 kW (最高热效率 41%)"],
        ["前驱动电机 CTZ196", "华为数字能源技术有限公司", "额定 65 kW", "峰值功率 130 kW"],
        ["后驱动电机 CTZ200", "华为数字能源技术有限公司", "额定 75 kW", "峰值功率 200 kW"],
    ]
    _draw_table(p2, fn, 110, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "AITO M7 ULTRA HOMOLOGATION SHEET • 电池与被动安全", 3)
    p3.insert_text((50, 75), "宁德时代三元锂电池包规格与 2000MPa 热成型钢车身", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers3 = ["安全系统结构", "设计用料参数", "行业技术地位", "碰撞吸能保护"]
    col_x3 = [55, 180, 310, 430]
    rows3 = [
        ["A/B柱热成型钢", "抗拉强度高达 2000 MPa", "潜艇级特种特高强钢", "严苛顶压与侧面碰撞零侵入"],
        ["动力电池包外壳", "全铝合金一体箱体 + 1200℃ 隔热云母板", "IPX8 防水防尘", "五层结构防护抵抗底部碎石托底"],
        ["全车安全气囊", "标配 8 处安全气囊 + 前后贯穿头部气帘", "双预紧限力安全带", "碰撞后 3 秒内自动高压下电断油"],
    ]
    _draw_table(p3, fn, 110, headers3, col_x3, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


# 8. Porsche Taycan High Voltage Safety Guide (3 pages)
def generate_porsche_safety_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "Porsche_Taycan_High_Voltage_Safety_Guide.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "PORSCHE TAYCAN HIGH VOLTAGE SAFETY MANUAL • 保时捷高压安全手册", 1)
    p1.insert_text((50, 75), "保时捷 Taycan 800V DC 高压电气系统救援隔离作业指引", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers = ["安全隔离步骤", "执行动作与工具", "安全确认标准", "潜在电击风险"]
    col_x = [55, 180, 310, 430]
    rows = [
        ["1. 切断点火开关", "按下仪表左侧启动按键并拔出钥匙", "仪表盘完全黑屏无唤醒显示", "接触器可能处于保持状态"],
        ["2. 断开低压蓄电池", "拆除前机舱 12V 锂离子蓄电池负极接地线", "使用 10mm 绝缘套筒扳手锁固", "防气囊或预紧器误爆触发"],
        ["3. 拔脱高压断开插头", "拔出前围挡板下方 Manual Cut Plug", "红色锁止销完全弹起锁死", "高压继电器彻底物理断开"],
    ]
    _draw_table(p1, fn, 110, headers, col_x, rows)

    p2, fn = _setup_page(doc, "PORSCHE TAYCAN HIGH VOLTAGE SAFETY MANUAL • 车间验电规程", 2)
    p2.insert_text((50, 75), "车间维修五步验电法与绝缘电阻核验表", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers2 = ["验电检测点", "检测仪器设备", "允许安全电压", "异常情况排查"]
    col_x2 = [55, 180, 310, 430]
    rows2 = [
        ["直流母线正负极之间", "CAT IV 1000V 双极电压表", "< 5.0 V", "若电压 > 10V，说明电容放电阻失效"],
        ["直流正极对底盘车身", "CAT IV 1000V 双极电压表", "< 5.0 V", "排查正极高压接触器黏连"],
        ["直流负极对底盘车身", "CAT IV 1000V 双极电压表", "< 5.0 V", "排查负极高压接触器黏连"],
    ]
    _draw_table(p2, fn, 110, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "PORSCHE TAYCAN HIGH VOLTAGE SAFETY MANUAL • 消防灭火与注水", 3)
    p3.insert_text((50, 75), "动力蓄电池热失控专用消防注水接口使用规范", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    headers3 = ["操作项目", "设备与技术参数要求", "标准作业规范", "安全注意事项"]
    col_x3 = [55, 180, 310, 430]
    rows3 = [
        ["注水接口连接", "标准消防 Storz C 快速接头", "位于车底中央专用应急注水阀", "只能注入清水，禁止化学泡沫"],
        ["注水压力要求", "供水压力 2.0 至 4.0 bar", "保持持续水流灌入电池包内部", "压力过大可能破坏电芯结构防爆阀"],
        ["持续灌注时间", "不少于 45 分钟", "热成像仪监测包体温度低于 50℃", "持续观察 24 小时防止死灰复燃"],
    ]
    _draw_table(p3, fn, 110, headers3, col_x3, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


# 9. Wey Lanshan Coffee Pilot Ultra Technical Manual (3 pages)
def generate_wey_lanshan_pdf(out_dir: Path) -> Path:
    file_path = out_dir / "Wey_Lanshan_Coffee_Pilot_Ultra_Technical_Manual.pdf"
    doc = fitz.open()

    p1, fn = _setup_page(doc, "WEY LANSHAN COFFEE PILOT ULTRA MANUAL • 魏牌蓝山智驾手册", 1)
    p1.insert_text((50, 75), "魏牌蓝山智驾版 Coffee Pilot Ultra 智能座舱与高阶智驾规格手册", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    p1.insert_text((50, 95), "适用车型: 长城汽车 魏牌 蓝山智驾版 (六座旗舰大SUV)", fontname=fn, fontsize=9.0, color=(0.3, 0.3, 0.3))
    headers = ["智驾感知硬件", "规格型号与参数", "安装布局位置", "功能赋能范围"]
    col_x = [55, 180, 310, 430]
    rows = [
        ["超高清车规级激光雷达", "128线高线束 / 探测距离 200m", "车顶正中央单颗瞭望塔式", "全天候无图城市与高速NOA领航"],
        ["高清视觉感知相机", "800万像素前视双目 + 300万环视", "前风挡集成 + 四周车身包围", "360度红绿灯、静态障碍物识别"],
        ["高算力智驾域控平台", "英伟达 Orin-X (单颗算力 254 TOPS)", "主驾仪表板下方专用屏蔽舱", "SEE 端到端感知决策一体化大模型"],
    ]
    _draw_table(p1, fn, 115, headers, col_x, rows)

    p2, fn = _setup_page(doc, "WEY LANSHAN COFFEE PILOT ULTRA MANUAL • 智能座舱与空间", 2)
    p2.insert_text((50, 75), "Coffee OS 3 智慧空间与高通骁龙 8295 芯片技术参数", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    p2.insert_text((50, 95), "座舱配置: 15.6英寸双联屏 + 后排17.3英寸娱乐屏 + 29英寸SR-HUD", fontname=fn, fontsize=9.0, color=(0.3, 0.3, 0.3))
    headers2 = ["座舱系统模块", "技术规格参数", "响应延迟与性能", "乘员体验提升"]
    col_x2 = [55, 180, 310, 430]
    rows2 = [
        ["高通 8295 旗舰芯片", "5nm制程工艺 / NPU算力 30 TOPS", "车机开机仅需 2.8 秒", "多屏流畅交互与大型3D车模实时渲染"],
        ["Coffee OS 3 语音大模型", "毫秒级全时免唤醒四音区识别", "指令响应时间 < 280 ms", "一句话支持执行四个连续车控指令"],
        ["二排双零重力座椅", "12向电动调节 + 8点气动按摩", "一键躺平时背部倾角 135°", "长途旅行缓解腰椎疲劳，舒适度拉满"],
    ]
    _draw_table(p2, fn, 115, headers2, col_x2, rows2)

    p3, fn = _setup_page(doc, "WEY LANSHAN COFFEE PILOT ULTRA MANUAL • 动力与底盘", 3)
    p3.insert_text((50, 75), "Hi4 性能版智能四驱电混与电控减振器特性", fontname=fn, fontsize=14, color=(0.1, 0.2, 0.4))
    p3.insert_text((50, 95), "动力总成: 1.5T 混动专用发动机 + 4挡混动DHT + 前后双电机", fontname=fn, fontsize=9.0, color=(0.3, 0.3, 0.3))
    headers3 = ["动力底盘部件", "标定技术参数", "工作控制模式", "整车性能表现"]
    col_x2 = [55, 180, 310, 430]
    rows3 = [
        ["Hi4 综合系统功率", "380 kW / 933 N·m 峰值扭矩", "纯电/直驱/并联智能切换", "零百加速 4.9 秒，破百推背感强劲"],
        ["宁德时代动力电池", "容量 52.3 kWh 三元锂电池", "支持 45kW 直流快充", "CLTC 纯电续航 220 km，综合续航 1343 km"],
        ["CDC 电控可变阻尼减振器", "每秒 100 次路面自适应调节", "舒适/标准/运动三挡阻尼", "大幅抑制起步抬头、制动点头与过弯侧倾"],
    ]
    _draw_table(p3, fn, 115, headers3, col_x2, rows3)

    doc.save(file_path)
    doc.close()
    logger.info(f"Generated {file_path}")
    return file_path


def generate_all_new_pdf_datasets(out_dir: Path) -> List[Path]:
    """Generate all 9 new PDF benchmark specification manuals."""
    generators = [
        generate_xiaomi_su7_pdf,
        generate_yangwang_u8_pdf,
        generate_nio_et7_pdf,
        generate_tesla_plaid_pdf,
        generate_li_l7_pdf,
        generate_zeekr_007_pdf,
        generate_aito_m7_pdf,
        generate_porsche_safety_pdf,
        generate_wey_lanshan_pdf,
    ]
    results = []
    for g in generators:
        results.append(g(out_dir))
    return results
