"""
PowerPoint Dataset Builders for AutoVend Enterprise Benchmark.
Generates 13 high-quality, realistic automotive PowerPoint presentations (.pptx) across leading OEMs.
"""

import logging
from pathlib import Path
from typing import List

import pptx
from pptx.dml.color import RGBColor as PPT_RGBColor
from pptx.util import Inches as PPT_Inches
from pptx.util import Pt as PPT_Pt

logger = logging.getLogger("enterprise_dataset_gen.pptx")


def _add_slide(prs, title_text: str, bullet_points: List[str], notes_text: str = "", table_data: List[List[str]] = None):
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    # Title box
    tx_box = slide.shapes.add_textbox(PPT_Inches(0.8), PPT_Inches(0.5), PPT_Inches(11.5), PPT_Inches(1.0))
    tf = tx_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = PPT_Pt(24)
    p.font.bold = True
    p.font.color.rgb = PPT_RGBColor(0x1F, 0x49, 0x7D)

    # Bullet points box
    content_top = 1.6
    if bullet_points:
        bullet_box = slide.shapes.add_textbox(PPT_Inches(0.8), PPT_Inches(content_top), PPT_Inches(11.5), PPT_Inches(2.2))
        btf = bullet_box.text_frame
        btf.word_wrap = True
        for i, pt in enumerate(bullet_points):
            bp = btf.add_paragraph() if i > 0 else btf.paragraphs[0]
            bp.text = f"•  {pt}"
            bp.font.size = PPT_Pt(14)
            bp.font.color.rgb = PPT_RGBColor(0x2C, 0x3E, 0x50)
        content_top += 2.0

    # Embedded table
    if table_data:
        rows_cnt = len(table_data)
        cols_cnt = len(table_data[0])
        tbl_shape = slide.shapes.add_table(rows_cnt, cols_cnt, PPT_Inches(0.8), PPT_Inches(content_top), PPT_Inches(11.5), PPT_Inches(0.4 * rows_cnt))
        tbl = tbl_shape.table
        for r_i, row in enumerate(table_data):
            for c_i, val in enumerate(row):
                cell = tbl.cell(r_i, c_i)
                cell.text = str(val)
                p = cell.text_frame.paragraphs[0]
                p.font.size = PPT_Pt(11)
                if r_i == 0:
                    p.font.bold = True
                    p.font.color.rgb = PPT_RGBColor(0xFF, 0xFF, 0xFF)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = PPT_RGBColor(0x2F, 0x55, 0x97)

    # Speaker notes
    if notes_text:
        notes_slide = slide.notes_slide
        notes_text_frame = notes_slide.notes_text_frame
        notes_text_frame.text = notes_text

    return slide


# 1. Xiaomi SU7 Launch Keynote Deck
def generate_xiaomi_su7_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Xiaomi_SU7_Launch_Keynote_Deck.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "小米 SU7 全球发布会 • 人车家全生态核心战略",
        ["雷军亲自发布：小米汽车首款作品定位 C 级豪华科技轿跑", "人车家全生态闭环：澎湃 OS 深度打通手机、平板与智能座舱", "全栈自研底层技术：超级电机、CTB 一体化电池、压铸、智驾、座舱"],
        notes_text="演讲者备注: 重点向现场科技粉丝与车主传达小米十年造车沉淀与全栈自研硬核实力。",
    )

    tbl = [
        ["电机型号", "最高转速 (rpm)", "最大马力 (PS)", "峰值扭矩 (N·m)", "搭载车型"],
        ["HyperEngine V6", "21,000 rpm", "299 PS", "400 N·m", "SU7 标准版 / Pro 版"],
        ["HyperEngine V6s", "21,000 rpm", "374 PS", "500 N·m", "SU7 Max 双电机四驱"],
        ["HyperEngine V8s", "27,200 rpm", "578 PS", "635 N·m", "SU7 Ultra 量产超跑版"],
    ]
    _add_slide(
        prs,
        "HyperEngine 超级电机总览与极限转速对决",
        ["全球顶级量产电机转速天花板：V8s 达到不可思议的 27,200 rpm", "双向全油冷散热与 960MPa 特种超高强硅钢转子冲片", "完全自主研发并拥有全部专利与工艺定义"],
        notes_text="演讲者备注: 强调 27,200 rpm 是目前全球量产电机绝对第一，直接对标保时捷和特斯拉。",
        table_data=tbl,
    )

    wb_path = file_path
    prs.save(wb_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 2. BYD Yangwang U9 Supercar Teardown Deck
def generate_yangwang_u9_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "BYD_Yangwang_U9_Supercar_Teardown_Deck.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "仰望 U9 纯电超级跑车技术拆解 • 易四方与云辇-X 系统",
        ["四轮四电机独立扭矩矢量控制：最大马力 1306 PS，零百加速 2.36 秒", "云辇-X 全主动智能车身控制系统：四轮独立大行程主动电驱液压支柱", "原地起跳与跳舞模式：超高响应速度展现底盘动力学极限"],
        notes_text="演讲者备注: 剖析云辇-X 的高压电驱液压泵工作原理，四轮具备完全独立的升沉与俯仰主动调节能力。",
    )

    tbl = [
        ["核心系统", "核心指标", "技术供应商", "创新亮点"],
        ["易四方电机总成", "4 × 240 kW 四电机", "比亚迪自研弗迪动力", "单电机极速 21,000 rpm"],
        ["云辇-X 车身控制", "最大单轮举升力 1吨", "比亚迪全栈自研", "响应时间仅 10 毫秒"],
        ["碳纤维座舱单体壳", "扭转刚度 54,425 N·m/°", "中航复材联合研发", "航天级高模量碳布模压"],
    ]
    _add_slide(
        prs,
        "仰望 U9 赛道级关键零部件工程拆解矩阵",
        ["轻量化极致追求：碳纤维座舱重量仅 110 kg", "赛道高效导风气动布局：车头双气道与碳纤维主动可调鹅颈大尾翼"],
        notes_text="演讲者备注: 对比法拉利 SF90 与保时捷 GT3 RS 的扭转刚度数据。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 3. Huawei HIMA Smart Driving Investor Briefing
def generate_huawei_hima_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Huawei_HIMA_Smart_Driving_Investor_Briefing.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "鸿蒙智行 (HIMA) 2026 智能驾驶与生态战略投资者沟通会",
        ["商业闭环全面成型：问界 (AITO)、智界 (Luxeed)、享界 (Stelato)、尊界 (Maextro) 四界并进", "华为乾崑 ADS 3.0：架构升级为 PDP 预测决策规控一体化端到端大模型", "全国都能开，有路就能开：全国城市道路领航全面商用落地"],
        notes_text="演讲者备注: 向二级市场投资人重点介绍华为智能汽车业务 BU 的毛利率改善与交付放量数据。",
    )

    tbl = [
        ["联盟品牌 (界)", "合作整车厂", "旗舰车型代表", "细分市场定位"],
        ["问界 (AITO)", "赛力斯汽车 (Seres)", "问界 M9 / 新 M7", "全景智慧大型/中大型豪华SUV"],
        ["智界 (Luxeed)", "奇瑞汽车 (Chery)", "智界 S7 / 智界 R7", "高能智慧纯电轿跑/轿跑SUV"],
        ["享界 (Stelato)", "北汽新能源 (BAIC)", "享界 S9", "全景智慧行政级豪华纯电轿车"],
        ["尊界 (Maextro)", "江淮汽车 (JAC)", "尊界首款超豪华车", "百万级超豪华行政座驾对标迈巴赫"],
    ]
    _add_slide(
        prs,
        "鸿蒙智行全产品矩阵与合作主机厂生态矩阵",
        ["技术赋能而非造车：提供智驾、座舱、电驱、底盘及销售渠道全链路赋能", "月度整体交付量持续突破 4.5 万辆大关"],
        notes_text="演讲者备注: 阐述华为智能汽车解决方案在行业中的标准化平台定位。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 4. Tesla Cybertruck 48V Architecture Teardown
def generate_tesla_cybertruck_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Tesla_Cybertruck_48V_Architecture_Teardown.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "Tesla Cybertruck 48V Low-Voltage Bus & Steer-by-Wire Review",
        ["全面颠覆传统 12V 架构：Cybertruck 成为全球首款纯 48V 低压电气系统量产车", "电流降低至传统 1/4，线束截面积缩减，全车低压线束总重减轻超 70%", "以太网吉比特环网通信，彻底取代传统低速 CAN 总线"],
        notes_text="演讲者备注: 强调特斯拉公开 48V 规范手册给全球车企的开源精神与行业深远影响。",
    )

    tbl = [
        ["子系统指标", "传统 12V 电气架构", "Cybertruck 48V 架构", "工程收益"],
        ["线束工作电流 (1000W负载)", "83.3 A", "20.8 A", "线损热量下降 16 倍"],
        ["低压线束总重量", "约 45 kg", "约 12 kg", "减重 33 kg 提升续航"],
        ["转向执行机构", "机械转向柱 + 液压/电动助力", "完全线控转向 (Steer-by-Wire)", "方向盘转角无需倒手 (1.3圈)"],
    ]
    _add_slide(
        prs,
        "48V 低压电气系统与线控转向参数深度对照",
        ["可变转向比 1:5 至 1:15：低速掉头轻松调向，高速巡航沉稳微调", "双冗余转向电机与独立供电电池确保绝对失效安全 (Fail-Operational)"],
        notes_text="演讲者备注: 阐明没有机械转向柱连接后碰撞安全性的巨大飞跃。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 5. NIO Day Power Swap 5 Roadmap
def generate_nio_swap5_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "NIO_Day_Power_Swap_5_Roadmap.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "蔚来第五代换电站 (Power Swap Station 5.0) 全球技术发布",
        ["换电效率质的飞跃：换电全流程缩短至 120 秒，单站单日服务能力超 600 次", "跨品牌多平台兼容：全面兼容乐道 (ONVO)、萤火虫 (Firefly) 及战略合作品牌", "多规格托盘自适应升降机械臂与车地通信毫米波超精对齐"],
        notes_text="演讲者备注: 突出换电网络从蔚来专属基础设施进化为全行业公共电网补能网络的战略升维。",
    )

    tbl = [
        ["换电站世代", "换电耗时 (分钟)", "电池仓电池仓位", "单日最大服务次数", "激光雷达与算力"],
        ["第一代换电站", "4.5 分钟", "5 块电池", "72 次", "无雷达 / 基础PLC"],
        ["第三代换电站", "3.0 分钟", "21 块电池", "408 次", "2颗激光雷达 / 2颗Orin-X"],
        ["第四代换电站", "2.4 分钟", "23 块电池", "480 次", "4颗激光雷达 / 4颗Orin-X"],
        ["第五代换电站 (5.0)", "2.0 分钟", "28 块电池", "600 次", "全固态毫米波 / 自研神玑芯片"],
    ]
    _add_slide(
        prs,
        "蔚来历代换电站核心能力与技术演进对比表",
        ["电网互动与虚拟电厂：参与高峰期电网调频调峰，实现年化千万级电价套利", "车电分离模式全面获得资本市场与主流车企联盟认可"],
        notes_text="演讲者备注: 详细解答多品牌电池锁止机构标准化的实施进展。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 6. XPeng X9 vs Zeekr 009 Competitive Battlecard
def generate_xpeng_x9_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "XPeng_X9_vs_Zeekr_009_Competitive_Battlecard.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "小鹏 X9 对决 极氪 009 旗舰纯电 MPV 销售攻防话术战报",
        ["年轻奶爸与商务接待双重诉求：打破传统方盒子 MPV 油腻老气形象", "小鹏 X9 核心王牌：全系标配主动后轮转向与第三排一键魔术收纳", "极氪 009 核心防线：全车豪华用料、双 A 柱一体压铸与更强直线加速"],
        notes_text="演讲者备注: 指导一线销售顾问如何引导客户对比第三排完全下沉收纳与狭窄地库调头的灵活性。",
    )

    tbl = [
        ["关键对比项", "小鹏 X9 旗舰全配版", "极氪 009 2026款", "销售话术进攻要点"],
        ["主动后轮转向", "全系标配 (转弯半径 5.4m)", "无后轮转向 (转弯半径 6.2m)", "开起来像小轿车一样灵活，狭窄掉头一把过"],
        ["第三排折叠收纳", "电动一键下沉翻折完全纯平", "后排固定靠背不可收纳", "放平后就是大平层，露营能放四辆自行车"],
        ["底盘悬架架构", "全铝一体双叉臂+双腔空簧", "空气悬架+CCD连续阻尼", "双腔空簧高低软硬双维自适应，更舒适不晕车"],
        ["起售指导价格", "35.98 万元起", "43.90 万元起", "价格门槛更亲民，性价比高出整整一大截"],
    ]
    _add_slide(
        prs,
        "X9 vs 009 核心产品力参数对比矩阵与异议话术",
        ["智驾差异攻防：小鹏 XNGP 城市全场景无图领航 vs 极氪高速 NZP", "三电超充攻防：全栈 800V SiC 平台充电 10 分钟续航增加 300 公里"],
        notes_text="演讲者备注: 遇到极氪强调加速快的客户，应转移到 MPV 乘坐舒适度与家庭不晕车逻辑。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 7. Maextro S800 Executive Luxury Launch Keynote
def generate_maextro_s800_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Maextro_S800_Executive_Luxury_Keynote.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "尊界 S800 时代旗舰全球首发 • 鸿蒙智行百万级超豪华行政座驾",
        [
            "鸿蒙智行第四界：华为携手江淮联合打造，开创中国超豪华时代新纪元",
            "天地翱翔纵横之美：5.48米超长车身与星河璀璨座舱星空顶设计",
            "首创途灵全主动悬架：四轮独立全主动电液控制，过减速带车身零起伏",
            "全栈华为技术赋能：华为乾崑 ADS 3.0 全场景智能驾驶与鸿蒙座舱 4.5",
        ],
        notes_text="演讲者备注: 重点向高净值客户传递尊界对标劳斯莱斯与迈巴赫的东方豪华美学及极致智能科技。",
    )

    tbl = [
        ["豪华配置维度", "尊界 S800 旗舰技术规格", "对标竞品 (迈巴赫S级 / 宝马i7)", "工程创新价值"],
        ["整车尺寸架构", "长 5480mm / 宽 2000mm / 轴距 3370mm", "长 5470mm / 轴距 3396mm", "超越传统D级车行政后排纵向乘坐空间"],
        ["智能主动底盘", "华为途灵全主动悬架 (全主动电液执行机构)", "魔毯空气悬架 (传统单/双腔空簧)", "毫秒级预瞄路况，实现颠簸路面如履平地"],
        ["智驾与安全总成", "华为乾崑 ADS 3.0 (高精度固态激光雷达)", "L2级辅助驾驶系统 (毫米波雷达为主)", "全国道路车位到车位领航辅助与全向防碰撞"],
        ["座舱奢华工艺", "首创智能星空车顶 + 纯手工顶级小牛皮包覆", "传统翻毛皮车顶 / 选装星空顶", "首创全场景声学隐私隔绝与智能防窃听模式"],
    ]
    _add_slide(
        prs,
        "尊界 S800 核心技术规格与百万级豪华对标矩阵",
        [
            "首创智能星光迎宾光毯，开门瞬间仪式感拉满",
            "后排双零重力奢华头等舱座椅，支持 140° 大仰角躺平与全身气动石按摩",
        ],
        notes_text="演讲者备注: 突出尊界是中国汽车工业第一次在百万级超豪华轿车赛道实现核心技术与豪华美学的双重领跑。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 8. Avatr 12 Design Philosophy PPTX
def generate_avatr_12_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Avatr_12_Design_Philosophy_and_Aerodynamics.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "阿维塔 12 未来看未来 • 情感智能豪华轿跑设计解密",
        ["无后舷窗极致流线：重塑 GT 豪华跑车车尾美学与掀背优雅姿态", "全天候高清流媒体电子外后视镜：风阻降低 0.015，夜间暴雨高感透视", "HALO 交互屏：前风挡下方 10,500 颗 LED 点阵屏展现专属仪式感"],
        notes_text="演讲者备注: 阐述由德国慕尼黑全球设计中心打造的未来前瞻设计语言。",
    )

    tbl = [
        ["设计元素", "技术实现规格", "美学与工程价值"],
        ["全天候流媒体后视镜", "高动态 60fps 摄像头 + 6.7英寸内显示屏", "消除死角与雨水盲区，高速风阻下降 2.8%"],
        ["35.4英寸一体远端屏", "4K 超清分辨率贯穿式超宽视网膜屏", "驾驶视线不离路面，数字信息沉浸展开"],
        ["智能电动升降尾翼", "双速电控升降，90km/h自适应开启", "提供 45kg 尾部下压力提升高速附着力"],
    ]
    _add_slide(
        prs,
        "阿维塔 12 工业设计与空气动力学工程参数表",
        ["CHN 架构赋能：长安造车底蕴 + 华为乾崑智驾 + 宁德时代电池", "豪华内饰：全粒面苯胺真皮包裹与智能光感变色天幕"],
        notes_text="演讲者备注: 突出阿维塔在先锋设计与实用安全之间的平衡艺术。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 9. Porsche Taycan vs Tesla Model S Plaid Battlecard
def generate_porsche_vs_tesla_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Porsche_Taycan_vs_Tesla_Model_S_Plaid_Battlecard.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "Porsche Taycan Turbo S vs Tesla Model S Plaid 赛道性能终极对决",
        ["德系底盘工程对决硅谷极客动力：纽北赛道圈速实测见真章", "800V 架构两挡变速箱 vs 400V 三电机碳包转子架构", "保时捷主动悬架系统 (Active Ride)：极限过弯车身保持完全水平"],
        notes_text="演讲者备注: 引导高端玩家关注赛道持续高负荷下的动力一致性与热衰减表现。",
    )

    tbl = [
        ["评测项目", "Porsche Taycan Turbo GT / S", "Tesla Model S Plaid", "胜出方与工程原因"],
        ["纽博格林北环官方圈速", "7分07秒55 (Turbo GT)", "7分25秒23 (Track Pack)", "保时捷胜出 (弯道极限与下压力更高)"],
        ["连续20次0-100弹射起步", "各次加速误差 < 0.1秒 (无衰减)", "第5次起步后电池触发热保护降功率", "保时捷胜出 (800V及极致电驱液冷)"],
        ["直线 0-400米加速极速", "9.4 秒 @ 250 km/h", "9.23 秒 @ 250 km/h", "特斯拉险胜 (三电机直线马力更大)"],
    ]
    _add_slide(
        prs,
        "赛道性能与连续放电热管理极限对比表",
        ["保时捷主动悬架 (Active Ride)：取消防倾杆，利用电动液压泵主动倾斜吸收横向离心力", "制动系统：保时捷 420mm 碳陶制动盘耐受 1200℃ 高温依然无热衰退"],
        notes_text="演讲者备注: 重点向超跑客户讲解保时捷调校的机械质感与驾驶者之车的底蕴。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 10. Mercedes-Benz MB.OS Architecture Keynote
def generate_mercedes_mbos_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Mercedes_Benz_MB_OS_Architecture_Keynote.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "梅赛德斯-奔驰 MB.OS 新一代端到端自研芯片到云软件架构",
        ["软件定义汽车 (SDV) 战略转型核心基石：自研专用汽车操作系统 MB.OS", "四大核心领域硬件解耦：智能座舱、自动驾驶、车身舒适、动力底盘", "芯片到云端全栈打通：携手 Nvidia、Google 与 Unity 打造下一代智能体验"],
        notes_text="演讲者备注: 强调梅赛德斯-奔驰在保有豪华造车DNA的同时，全面掌控数字软件核心灵魂。",
    )

    tbl = [
        ["域控制器 (Domain)", "核心主控计算芯片", "运行操作系统 / 中间件", "主要功能承载"],
        ["Infotainment 座舱域", "Qualcomm Snapdragon 8295 / SA8775P", "MB.OS 专属内核 + Unity 渲染引擎", "沉浸式三维游戏导航与全车语音"],
        ["Automated Driving 智驾域", "Nvidia DRIVE Orin / Thor (1000 TOPS)", "QNX OS for Safety (ASIL-D)", "Drive Pilot SAE L3 级条件自动驾驶"],
        ["Body & Comfort 车身域", "NXP / ST 32位高性能车规 MCU", "AUTOSAR Adaptive / Classic", "座椅律动、香氛、多区温控及门窗"],
    ]
    _add_slide(
        prs,
        "MB.OS 跨域计算平台芯片与软件技术架构矩阵",
        ["全球首款在欧洲与美国合规落地的商业化 L3 级自动驾驶 (Drive Pilot)", "持续 OTA 升级保障全生命周期软件功能常用常新"],
        notes_text="演讲者备注: 展示奔驰在安全冗余架构上的严苛合规要求。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 11. BMW Neue Klasse Gen6 Battery Roadmap
def generate_bmw_battery_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "BMW_Neue_Klasse_Gen6_Battery_Roadmap.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "宝马新世代 (Neue Klasse) 第六代 eDrive 电驱技术战略演进",
        ["宝马百年造车最大战略转型：新世代 (Neue Klasse) 专属纯电平台 2026 量产", "第六代 BMW eDrive 技术核心：全面切换为 4695 / 46120 大圆柱电芯", "800V 高压电气架构：充电速度提升 30%，能量密度提升 20%，续航增加 30%"],
        notes_text="演讲者备注: 面向机构投资人展示宝马电气化规模化盈利与技术自主权。",
    )

    tbl = [
        ["技术指标", "第五代 eDrive (方形电芯)", "第六代 eDrive (大圆柱电芯)", "性能提升幅度"],
        ["电芯规格形态", "方形铝壳电芯 (Prismatic)", "46 毫米直径大圆柱电芯 (4695/46120)", "标准化程度大幅提升"],
        ["体积能量密度", "约 550 Wh/L", "约 660 Wh/L", "体积能量密度提升 20%"],
        ["系统工作电压", "400 V", "800 V 高压超充平台", "支持峰值 270 kW 直流超快充"],
        ["生产碳足迹", "基准碳排放", "降低 60% 制造端碳排放", "100% 绿色可再生电力生产"],
    ]
    _add_slide(
        prs,
        "宝马第五代与第六代动力电池技术代际指标对比",
        ["Pack-to-Chassis (P2C) 电池车身一体化：将电池包作为车身主要承载结构部件", "数字化全景视界 (BMW Panoramic Vision)：贯穿整个挡风玻璃的革命性抬头投影"],
        notes_text="演讲者备注: 突出宝马沈阳大东工厂与匈牙利德布勒森工厂的大圆柱电池本地化投产计划。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 12. Fangchengbao Bao8 DMO Offroad Launch Deck
def generate_fangchengbao_bao8_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Fangchengbao_Bao8_DMO_Offroad_Launch_Deck.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "方程豹 豹8 旗舰硬派越野 SUV 官方产品技术推介",
        ["全球首发 DMO 电驱越野平台与华为乾崑 ADS 3.0 高阶智驾强强联合", "云辇-P 标准版智能液压车身控制系统：高度调节行程达 140 mm", "非承载式高强度大梁架构与 CTC 电池底盘一体化防护"],
        notes_text="演讲者备注: 展现方程豹在兼顾硬派越野非凡通过性与城市公路舒适智驾的双重统治力。",
    )

    tbl = [
        ["动力与底盘配置", "关键性能技术参数", "越野实战价值"],
        ["2.0T 纵置越野专用发动机", "最大功率 200 kW / 380 N·m", "保障高海拔重负荷下的持续供电能力"],
        ["前后双电机电四驱", "前 200kW + 后 300kW (系统超 700 匹马力)", "沙漠刷锅与冲坡瞬间爆发峰值动力"],
        ["云辇-P 液压悬架", "四轮联动刚度自适应 / 140mm 升降", "涉水深度提升至 890mm，杜绝越野交叉轴托底"],
        ["智驾系统总成", "华为乾崑 ADS 3.0 (激光雷达)", "首款搭载华为高阶无图智驾的硬派越野车"],
    ]
    _add_slide(
        prs,
        "方程豹 豹8 核心硬件配置与硬核越野参数清单",
        ["标配前后电子差速锁与能量中锁，100% 极限爬坡能力", "支持 6kW 对外大功率放电与 2.5 吨国家认证拖挂资质"],
        notes_text="演讲者备注: 强调方盒子造型美学与全功能硬派越野工具属性的结合。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 13. Geely Galaxy Starship AI Powertrain Deck
def generate_geely_starship_pptx(out_dir: Path) -> Path:
    file_path = out_dir / "Geely_Galaxy_Starship_AI_Powertrain_Deck.pptx"
    prs = pptx.Presentation()
    prs.slide_width = PPT_Inches(13.33)
    prs.slide_height = PPT_Inches(7.5)

    _add_slide(
        prs,
        "吉利银河星舰原型车全球首发 • AI 驱动的下一代电混架构",
        ["吉利控股集团新能源旗舰力作：全尺寸智慧豪华 SUV 原型车", "雷神电混 46.5% 全球最高量产热效率专用发动机", "11合1 智能电驱系统与全场景 AI 数字化交互座舱"],
        notes_text="演讲者备注: 向汽车媒体与技术评审专家展示吉利在混动热效率与汽车大模型领域的领先突破。",
    )

    tbl = [
        ["核心动力系统", "关键突破技术指标", "行业纪录与定位"],
        ["新一代雷神电混发动机", "最高热效率 46.5%", "全球量产汽油机热效率第一"],
        ["11合1 超高集成智能电驱", "综合效率 90.04% / 功率密度提升 20%", "超高集成度节省机舱空间 15%"],
        ["分布式电驱轮边转向", "四轮独立电驱动与原地掉头", "吉利 AI 数字底盘自主决策控制"],
        ["银河 Flyme Auto 座舱", "高通 8295 芯片 + 星睿 AI 大模型", "手车无感互联与全场景端到端语音"],
    ]
    _add_slide(
        prs,
        "银河星舰核心三电系统与热效率标杆参数",
        ["满油满电综合续航突破 2000 公里大关，百公里馈电油耗仅 2.62 升", "GEA 新能源专属架构全面兼容纯电、混动、增程与绿色甲醇动力"],
        notes_text="演讲者备注: 突出吉利二十年动力总成全栈自研积累与全球化供应链整合能力。",
        table_data=tbl,
    )

    prs.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_all_new_pptx_datasets(out_dir: Path) -> List[Path]:
    """Generate all 13 new PowerPoint benchmark presentations."""
    generators = [
        generate_xiaomi_su7_pptx,
        generate_yangwang_u9_pptx,
        generate_huawei_hima_pptx,
        generate_tesla_cybertruck_pptx,
        generate_nio_swap5_pptx,
        generate_xpeng_x9_pptx,
        generate_maextro_s800_pptx,
        generate_avatr_12_pptx,
        generate_porsche_vs_tesla_pptx,
        generate_mercedes_mbos_pptx,
        generate_bmw_battery_pptx,
        generate_fangchengbao_bao8_pptx,
        generate_geely_starship_pptx,
    ]
    results = []
    for g in generators:
        results.append(g(out_dir))
    return results
