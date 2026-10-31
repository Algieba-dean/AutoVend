"""
Word Dataset Builders for AutoVend Enterprise Benchmark.
Generates 17 high-quality, realistic automotive Word documents (.docx) across leading OEMs.
"""

import logging
from pathlib import Path
from typing import List

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT

logger = logging.getLogger("enterprise_dataset_gen.word")


def _add_meta(doc, doc_id: str, classification: str, vehicle: str):
    p = doc.add_paragraph()
    p.add_run(f"文件编号: {doc_id} | 密级: {classification} | 适用车系: {vehicle}").italic = True


def _create_styled_table(doc, headers: List[str], rows: List[List[str]]):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
    for row in rows:
        r_cells = t.add_row().cells
        for i, val in enumerate(row):
            r_cells[i].text = str(val)
    return t


# 1. Xiaomi SU7 High Voltage Safety Rescue SOP
def generate_xiaomi_rescue_word(out_dir: Path) -> Path:
    file_path = out_dir / "Xiaomi_SU7_High_Voltage_Safety_Rescue_SOP.docx"
    doc = docx.Document()
    doc.add_heading("小米 SU7 高压电气系统应急救援与消防断电破拆规范 (SOP)", level=1)
    _add_meta(doc, "MI-EV-SOP-2026-009", "企业绝密/应急指引", "小米 SU7 / SU7 Pro / SU7 Max / SU7 Ultra")

    doc.add_heading("1. 事故现场高压断电前置准备与绝缘判定", level=2)
    doc.add_paragraph(
        "在处理涉及小米 SU7 系列高压事故车辆时，救援人员必须首先穿戴 1000V 防护等级绝缘手套与绝缘胶靴。"
        "通过观察仪表盘或手机端应急 App 确认高压接触器吸合状态。若车辆处于涉水或起火状态，严禁直接触碰裸露金属车身。"
    )

    doc.add_heading("2. 紧急断电回路 (Emergency Cut Loop) 与物理断电开关", level=2)
    doc.add_paragraph(
        "车辆配备双重硬线物理断电保护：\n"
        "1. 前备箱应急拉环：位于前机舱右侧蓄电池盖板下方，剪断标有高压急停警示标签的低压控制回路硬线；\n"
        "2. 后排中央座椅下方 Manual Service Disconnect (MSD) 高压维修开关拔脱插座。"
    )

    headers = ["部件位置", "接线颜色", "额定工作电压", "救援破拆要求", "危险等级"]
    rows = [
        ["前机舱动力总成区", "橙色绝缘编织护套", "871V DC", "严禁直接使用液压剪切断", "极高危 (致命电击)"],
        ["底盘中置动力电池包", "全密封铝合金壳体", "871V DC", "严禁穿刺、撞击或钻孔", "极高危 (热失控风险)"],
        ["B柱低压气囊传感器", "黄色/黑色控制线", "12V DC", "切割前必须先断开蓄电池负极", "中危 (意外弹开发生)"],
        ["电动升降尾翼执行电机", "黑色线束套管", "12V DC", "可正常切割，不含高压电", "低危 (常规机械结构)"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.add_heading("3. 现场消防处置与持续降温规程", level=2)
    doc.add_paragraph(
        "> 危险警告: 动力电池起火时必须使用大量连续清水进行持续喷淋降温，降温时间不得少于 60 分钟，"
        "防止因内部三元锂电芯局部积热导致二次复燃。"
    )

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 2. Huawei ADS3 LiDAR Calibration Procedure
def generate_huawei_lidar_word(out_dir: Path) -> Path:
    file_path = out_dir / "Huawei_ADS3_LiDAR_Calibration_Procedure.docx"
    doc = docx.Document()
    doc.add_heading("华为乾崑 ADS 3.0 192线车规级激光雷达动态与静态光学标定规范", level=1)
    _add_meta(doc, "HW-ADS-CAL-2026-03", "受控工艺标准", "华为乾崑智驾合作全系车型 (问界/智界/享界/阿维塔)")

    doc.add_heading("1. 标定场地与光照环境基准要求", level=2)
    doc.add_paragraph(
        "标定作业必须在标准四轮定位工位进行，地面平整度误差在 5 米范围内不得大于 2mm。"
        "环境光照度需控制在 150 lux 至 450 lux 之间，避免阳光直射标定靶标板造成激光点云信噪比恶化。"
    )

    doc.add_heading("2. 标定靶标几何参数与公差容限表", level=2)
    headers = ["标定轴向与参数", "设计标称值", "允许安装误差", "补偿计算算法", "标定完成判定标准"]
    rows = [
        ["偏航角 (Yaw Angle)", "0.00°", "±0.05°", "点云特征边缘匹配滤波", "三次重投影残差 < 0.02°"],
        ["俯仰角 (Pitch Angle)", "+1.25°", "±0.08°", "地平面法向量反投影", "三次重投影残差 < 0.03°"],
        ["翻滚角 (Roll Angle)", "0.00°", "±0.10°", "水平基准线霍夫变换", "三次重投影残差 < 0.02°"],
        ["X轴水平偏移 (Tx)", "0 mm", "±3.0 mm", "车身中轴线对称约束", "定位误差 < 1.5 mm"],
        ["Z轴垂直离地高度 (Tz)", "1420 mm", "±5.0 mm", "底盘悬挂标准高度复核", "空载气动弹簧标准高度"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.add_heading("3. 动态路试自学习验证流程", level=2)
    doc.add_paragraph(
        "静态标定通过后，车辆需以 40-80 km/h 速度在车道线清晰的结构化道路上行驶不少于 15 公里，"
        "ADS 3.0 神经感知网络将自动完成车道线及周边静态路沿的高精点云自适应闭环对齐。"
    )

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 3. Zeekr Golden Battery Puncture Test Report
def generate_zeekr_battery_word(out_dir: Path) -> Path:
    file_path = out_dir / "Zeekr_Golden_Battery_Puncture_Test_Report.docx"
    doc = docx.Document()
    doc.add_heading("极氪自研金砖电池 (Golden Battery) 800V 磷酸铁锂超快充极端针刺与火烧测试技术报告", level=1)
    _add_meta(doc, "ZK-BATT-TR-2026-08", "技术研发评测", "极氪 007 / 极氪 001 / 极氪 7X")

    doc.add_heading("1. 试验标准与极端工况环境设定", level=2)
    doc.add_paragraph(
        "本试验严格执行国家标准 GB 38031-2025 并叠加极氪企业苛刻测试：\n"
        "采用 Ф8mm 耐高温钨钢针，以 25 mm/s 速度完全垂直贯穿满电状态 (100% SOC) 电池包三个相邻电芯，并在电芯内部停留 120 分钟。"
    )

    doc.add_heading("2. 试验热失控测点瞬态温度与电压监测表", level=2)
    headers = ["针刺持续时间", "刺入电芯表面最高温 (℃)", "相邻电芯最高温 (℃)", "单体电芯开路电压 (V)", "绝缘阻抗监测 (MΩ)", "安全状态评估"]
    rows = [
        ["0 秒 (刺入瞬间)", "25.0 ℃", "25.0 ℃", "3.45 V", "> 1000 MΩ", "结构完整"],
        ["30 秒", "148.5 ℃", "38.2 ℃", "1.12 V (发生短路)", "850 MΩ", "泄压阀微启，无明火"],
        ["60 秒 (峰值温度)", "198.0 ℃", "45.0 ℃", "0.05 V", "720 MΩ", "云母隔热层阻隔，无热扩散"],
        ["5 分钟", "135.0 ℃", "42.1 ℃", "0.00 V", "750 MΩ", "温度稳定快速衰退"],
        ["60 分钟", "38.0 ℃", "28.5 ℃", "0.00 V", "920 MΩ", "完全恢复环境平衡，零起火零爆炸"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.add_heading("3. 试验评测结论", level=2)
    doc.add_paragraph(
        "金砖电池在金砖专属超聚能复合材料与多维立体绝缘热阻障层防护下，"
        "未发生热失控起火、未发生爆炸，高压绝缘阻抗保持正常，完全通过极限安全验证。"
    )

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 4. Li Auto Air Suspension Recall Remedy Guide
def generate_li_suspension_word(out_dir: Path) -> Path:
    file_path = out_dir / "Li_Auto_Air_Suspension_Recall_Remedy_Guide.docx"
    doc = docx.Document()
    doc.add_heading("理想汽车魔毯空气悬架下摆臂球销衬套技术排查与召回更换作业指导书", level=1)
    _add_meta(doc, "LI-SB-2026-004", "召回维修公告", "理想 L7 / 理想 L8 / 理想 L9")

    doc.add_heading("1. 涉及召回范围与故障现象描述", level=2)
    doc.add_paragraph(
        "针对在恶劣非铺装路面长期行驶的车辆，前下控制臂球头衬套在极限冲击力作用下可能存在微裂纹演化。"
        "授权服务中心需针对批次内车辆进行游标卡尺球头脱出间隙排查与强化总成免费更换。"
    )

    doc.add_heading("2. 悬架各关键连接螺栓紧固力矩技术规范", level=2)
    headers = ["部件连接位置", "紧固螺栓规格", "标称紧固力矩 (N·m)", "旋转角度附加要求", "更换备件要求"]
    rows = [
        ["前下控制臂连接副车架", "M14×1.5 10.9级", "145 N·m", "额外顺时针旋转 90°", "每次拆卸必须更换新自锁螺母"],
        ["前转向节连接下球销", "M12×1.25 10.9级", "95 N·m", "额外顺时针旋转 45°", "更换新尼龙防松螺母"],
        ["空气弹簧减振器上支座", "M10 8.8级", "55 N·m", "无额外角度要求", "原装螺栓涂抹中强度螺纹锁固胶"],
        ["前横向稳定杆连杆接头", "M12 10.9级", "85 N·m", "无额外角度要求", "必须使用双套筒对向锁紧"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.add_heading("3. 交付前道路测试与四轮定位复核", level=2)
    doc.add_paragraph(
        "完成更换后，必须在标准四柱举升机上将空气悬挂置于标称工况高度，紧固所有橡胶衬套螺栓，"
        "并执行前束角 (Toe-in) 与前轮外倾角 (Camber) 重新标定。"
    )

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 5. XPeng G9 XPower3 800V Charging Safety SOP
def generate_xpeng_charging_word(out_dir: Path) -> Path:
    file_path = out_dir / "XPeng_G9_XPower3_800V_Charging_Safety_SOP.docx"
    doc = docx.Document()
    doc.add_heading("小鹏汽车 S4 超快充桩与 G9 800V 高压平台高功率充电安全防护及检修 SOP", level=1)
    _add_meta(doc, "XP-CHG-SOP-2026-01", "车间服务规约", "小鹏 G9 / 小鹏 X9 / 小鹏 G6")

    doc.add_heading("1. S4 液冷充电枪回路阻抗与液冷回路巡检", level=2)
    doc.add_paragraph(
        "小鹏 S4 液冷超充桩最高支持 480kW 功率输出，充电枪内嵌轻量化液冷循环回路。"
        "每日首检必须使用专用绝缘电阻测试仪检测 DC+ 与 DC- 对大地绝缘阻抗 (标准值 ≥ 20 MΩ)。"
    )

    doc.add_heading("2. 充电中断故障代码速查与应急处置表", level=2)
    headers = ["故障代码 (DTC)", "故障现象描述", "底层触发阈值", "保护动作机制", "现场处置操作"]
    rows = [
        ["ERR-HV-01", "高压直流绝缘告警", "阻抗 < 500 Ω/V", "0.02秒切断直流接触器", "拔下充电枪，检查插座水渍污物"],
        ["ERR-TEMP-04", "液冷枪温超温告警", "端子温度 > 85.0 ℃", "自动将电流限制在 120A 以下", "检查冷却液泵扬程与液位"],
        ["ERR-COMM-09", "BMS握手通信超时", "CAN报文丢包 > 3帧", "停止充电流程并释放电子锁", "重新插拔充电枪并重启充电机CCU"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 6. BYD Blade Battery Cell Disassembly Manual
def generate_byd_blade_word(out_dir: Path) -> Path:
    file_path = out_dir / "BYD_Blade_Battery_Cell_Level_Disassembly_Manual.docx"
    doc = docx.Document()
    doc.add_heading("比亚迪刀片电池 (Blade Battery) 售后服务站电芯级梯次利用与安全拆解手册", level=1)
    _add_meta(doc, "BYD-BLD-MNL-2026-002", "售后工程手册", "比亚迪汉 / 唐 / 宋 / 海豹 / 腾势 D9")

    doc.add_heading("1. 电池包深冷放电与钝化预处理规程", level=2)
    doc.add_paragraph(
        "进入拆解工位的电池包总成，必须先连接大功率放电负载柜将端电压释放至安全阈值 (整包电压 < 60V)。"
        "拆解区域必须保持微正压通风，地面铺设防静电环氧树脂地坪。"
    )

    doc.add_heading("2. 刀片电芯拆解工装与绝缘防护工具矩阵", level=2)
    headers = ["作业步骤序号", "工艺名称", "专用工装设备", "防护等级要求", "技术工艺参数"]
    rows = [
        ["工步 1", "上盖密封胶激光切削", "高精度六轴工业机器人切胶机", "激光护目镜 + 防毒面具", "切削进给深度 3.2 mm ±0.1 mm"],
        ["工步 2", "铜铝复合母排剥离", "专用母排超声波焊点剥离夹具", "1000V VDE 绝缘手套", "静态剥离拉力 > 450 N"],
        ["工步 3", "单体刀片电芯脱模抽取", "负压真空吸盘矩阵抓手", "防爆工作服", "电芯最大弯曲挠度 < 1.0 mm"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 7. Porsche Macan EV Dual Motor Service Manual
def generate_porsche_macan_word(out_dir: Path) -> Path:
    file_path = out_dir / "Porsche_Macan_EV_Dual_Motor_Service_Manual.docx"
    doc = docx.Document()
    doc.add_heading("保时捷 Macan EV 双永磁同步电机与后桥两挡变速箱维修技术规范", level=1)
    _add_meta(doc, "PAG-MACAN-EV-2026", "车间维修手册", "Porsche Macan 4 / Macan Turbo")

    doc.add_heading("1. 800V 碳化硅脉冲逆变器维修环境", level=2)
    doc.add_paragraph(
        "Macan EV 后桥电驱系统集成保时捷最新碳化硅 (SiC) 逆变器，最高系统输出功率可达 470 kW。"
        "在拆卸逆变器母线连接前，必须使用专用万用表测量中间直流支撑电容残余电压确认 < 10V。"
    )

    doc.add_heading("2. 电驱减速箱润滑油与密封件技术规范", level=2)
    headers = ["润滑加注点", "推荐油品牌号", "标准加注量 (L)", "更换周期", "螺塞紧固扭矩"]
    rows = [
        ["前桥同轴减速器", "Porsche EV Drivetrain Fluid FE", "1.10 L", "每 60,000 km 或 4 年", "35 N·m"],
        ["后桥两挡电控变速箱", "Porsche High Performance ATF", "1.65 L", "每 60,000 km 或 4 年", "38 N·m"],
        ["逆变器水冷密封O圈", "耐高温氟橡胶 (FKM)", "4 件套", "每次分解必须更换", "涂抹专用硅脂"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 8. BMW iX Carbon Cage Collision Repair Manual
def generate_bmw_ix_word(out_dir: Path) -> Path:
    file_path = out_dir / "BMW_iX_Carbon_Cage_Collision_Repair_Manual.docx"
    doc = docx.Document()
    doc.add_heading("宝马 iX Carbon Cage 碳纤维复合材料车身结构碰撞后无损检测与结构胶粘接修复规范", level=1)
    _add_meta(doc, "BMW-IX-CFRP-2026", "钣喷与车身工艺", "BMW iX xDrive40 / xDrive50 / M60")

    doc.add_heading("1. CFRP 碳纤维增强复合材料分层损伤检测", level=2)
    doc.add_paragraph(
        "BMW iX 侧围框架、车顶横梁与后窗框采用创新 Carbon Cage 架构。"
        "在经历侧面碰撞或翻滚事故后，必须采用超声波相控阵探伤仪 (A-scan) 探测碳纤维层压板是否存在内部空洞或脱粘。"
    )

    doc.add_heading("2. 结构粘接胶与补强片技术指标", level=2)
    headers = ["修复工序", "结构胶型号", "工作环境温度", "红外固化加热时间", "最小搭接剪切强度"]
    rows = [
        ["侧围A柱加强件搭接", "Betamate 2090 环氧双组份胶", "20 ℃ - 25 ℃", "80 ℃ 恒温烘烤 45 分钟", "≥ 25.0 MPa"],
        ["后尾门碳纤维内框粘接", "SikaPower 498 高抗冲结构胶", "18 ℃ - 28 ℃", "自然静置固化 24 小时", "≥ 22.5 MPa"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 9. Mercedes Vision EQXX Thermal Management Bulletin
def generate_mercedes_eqxx_word(out_dir: Path) -> Path:
    file_path = out_dir / "Mercedes_Vision_EQXX_Thermal_Management_Bulletin.docx"
    doc = docx.Document()
    doc.add_heading("梅赛德斯-奔驰 Vision EQXX 仿生多源热泵热管理系统与风阻优化技术通告", level=1)
    _add_meta(doc, "MB-EQXX-TB-2026", "前瞻技术通报", "Mercedes-Benz 纯电研发样车与下一代 MMA 平台")

    doc.add_heading("1. 多源热泵系统在极寒工况下的余热利用", level=2)
    doc.add_paragraph(
        "Vision EQXX 实现了实测百公里能耗仅 8.3 kWh 的工程奇迹。其核心在于利用电机、逆变器及阳光顶棚散逸的多源余热，"
        "在 -25℃ 极低温环境下依然维持热泵系统综合效能比 (COP) 达到 2.3 以上。"
    )

    doc.add_heading("2. 膨胀阀与热管理水阀控制映射表", level=2)
    headers = ["环境温度区间", "主要吸热源", "电子膨胀阀开度 (%)", "压缩机目标转速 (rpm)", "乘员舱供暖功耗 (W)"]
    rows = [
        ["-20℃ 至 -10℃", "动力电驱余热 + PTC辅助", "45%", "4500 rpm", "1200 W"],
        ["-10℃ 至 5℃", "纯空气源多级膨胀", "60%", "3200 rpm", "850 W"],
        ["5℃ 至 25℃", "座舱自然通风热平衡", "0% (旁通)", "0 rpm (停机)", "150 W"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 10. Audi Q6 e-tron PPE Platform Workshop Guide
def generate_audi_q6_word(out_dir: Path) -> Path:
    file_path = out_dir / "Audi_Q6_etron_PPE_Platform_Workshop_Guide.docx"
    doc = docx.Document()
    doc.add_heading("奥迪 Q6 e-tron 基于 PPE 平台的新一代 E³ 1.2 域控制器架构售后诊断与通信排障指南", level=1)
    _add_meta(doc, "AUDI-PPE-E3-2026", "车间诊断规约", "Audi Q6 e-tron / SQ6 e-tron")

    doc.add_heading("1. 五大高性能计算平台 (HCP1-HCP5) 拓扑结构", level=2)
    doc.add_paragraph(
        "E³ 1.2 架构通过 1000BASE-T1 车载千兆以太网骨干环网连接五大核心域控制器："
        "HCP1 (动力总成与悬架)、HCP2 (高级辅助驾驶系统)、HCP3 (智能座舱与信息娱乐)、HCP4 (车身与舒适舒适系统)、HCP5 (诊断网关)。"
    )

    doc.add_heading("2. 域控制器休眠暗电流基准检测表", level=2)
    headers = ["控制器代码", "所属控制域", "正常待机工作电流", "整车闭锁15分钟后休眠电流", "异常唤醒排查路径"]
    rows = [
        ["HCP1", "动力与底盘域", "350 mA", "< 3.0 mA", "排查电池管理系统唤醒引脚"],
        ["HCP2", "智驾感知域", "850 mA", "< 5.0 mA", "排查环视摄像头自检定时器"],
        ["HCP3", "座舱娱乐域", "1200 mA", "< 8.0 mA", "排查远程车联 T-Box 轮询"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 11. Avatr 07 Smart Cockpit OTA Rollout Manual
def generate_avatr_07_word(out_dir: Path) -> Path:
    file_path = out_dir / "Avatr_07_Smart_Cockpit_OTA_Rollout_Manual.docx"
    doc = docx.Document()
    doc.add_heading("阿维塔 07 鸿蒙座舱 HarmonyOS 4.5 与昆仑增程系统 OTA 固件升级与回滚作业规范", level=1)
    _add_meta(doc, "AVATR-OTA-07-2026", "软件升级SOP", "阿维塔 07 增程版 / 纯电版")

    doc.add_heading("1. A/B 双分区无感升级架构与安全回滚机制", level=2)
    doc.add_paragraph(
        "车机系统采用双系统分区 (Partition A 与 Partition B) 机制。后台在备用分区静默刷写镜像并校验 SHA-256 签名。"
        "若系统启动看门狗监测到连续 3 次引导失败，将在 30 秒内自动切换回原始主分区，杜绝车机变砖风险。"
    )

    doc.add_heading("2. OTA 升级前置自检条件清单", level=2)
    headers = ["自检监测项", "必要安全阈值", "传感器检测源", "不满足时的系统提示"]
    rows = [
        ["高压动力电池电量", "SOC ≥ 30%", "BMS 主控上报", "电量不足，请连接充电桩或补电后重试"],
        ["车辆挡位与刹车状态", "挂入 P 挡且电子手刹锁止", "TCU / EPB 控制器", "请在车辆安全驻车后开始升级"],
        ["蓄电池 12V 低压状态", "电压 ≥ 12.4 V", "智能电池传感器 (IBS)", "蓄电池电压偏低，请保持车辆唤醒"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 12. Denza Z9 GT Dual Rear Motor Alignment Guide
def generate_denza_z9_word(out_dir: Path) -> Path:
    file_path = out_dir / "Denza_Z9_GT_Dual_Rear_Motor_Alignment_Guide.docx"
    doc = docx.Document()
    doc.add_heading("腾势 Z9 GT 易三方 (e3) 后双电机独立转向动态定位与四轮对中校准作业指导书", level=1)
    _add_meta(doc, "DENZA-E3-Z9-2026", "底盘调校SOP", "腾势 Z9 GT 纯电版 / 插混版")

    doc.add_heading("1. 后轮双电机独立转向核心原理", level=2)
    doc.add_paragraph(
        "腾势 Z9 GT 搭载全球首创易三方整车智能控制平台。后轴由两台独立永磁同步电机驱动，"
        "并配备后轮独立双向转向机构，左右后轮转向角最高可达 ±10°，支持圆规掉头与极致蟹行。"
    )

    doc.add_heading("2. 后轮对中与前束角标准参数校准表", level=2)
    headers = ["车轮定位参数", "出厂标称基准值", "允许静态校准公差", "调整机构位置", "校准工装工具"]
    rows = [
        ["后轮单轮前束角", "+0.08°", "±0.02°", "后轮转向电机拉杆偏心螺栓", "高精红外四轮定位仪"],
        ["后轮外倾角 (Camber)", "-1.30°", "±0.05°", "后悬架上控制臂偏心螺栓", "专业底盘角度测量仪"],
        ["后轮最大偏转角对称性", "10.0°", "左右差 ≤ 0.05°", "电机旋转编码器零位重置", "易三方专用标定诊断仪"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 13. Haval Raptor Hi4 Intelligent 4WD Offroad Manual
def generate_haval_raptor_word(out_dir: Path) -> Path:
    file_path = out_dir / "Haval_Raptor_Hi4_Intelligent_4WD_Offroad_Manual.docx"
    doc = docx.Document()
    doc.add_heading("哈弗猛龙 Hi4 智能电混四驱系统脱困与越野驾驶操作规程", level=1)
    _add_meta(doc, "GWM-HAVAL-HI4-2026", "越野技术规程", "哈弗猛龙 Hi4 / 哈弗大狗 Hi4")

    doc.add_heading("1. 长城 Hi4 前后轴双电机分布式智能电四驱架构", level=2)
    doc.add_paragraph(
        "哈弗猛龙搭载全新 Hi4 智能电混四驱系统，由 1.5T 混动专用高热效率发动机、前轴 70kW 传动模块、"
        "以及后轴 150kW 高性能电机总成组成，系统综合最大功率 282 kW，综合峰值扭矩高达 750 N·m。"
        "通过智能扭矩矢量控制系统 (iTVC)，系统可在毫秒级时间内在前轴与后轴之间动态分配扭矩，实现全工况四驱性能。"
    )

    doc.add_heading("2. 后桥机械牙嵌齿式差速锁与几何通过性指标表", level=2)
    headers = ["越野系统项目", "技术指标规格", "工况触发条件", "越野脱困价值说明"]
    rows = [
        ["后桥差速锁结构", "机械牙嵌齿式差速锁 (电控锁止)", "车速 < 20km/h 且前后轮速差触发", "后轮单轮悬空或打滑时实现100%硬连接扭矩传递"],
        ["接近角 / 离去角", "接近角 24° / 离去角 30° / 纵向通过角 19°", "满载工况测试", "大坡度冲坡与下坡防止前后包围托底刮擦"],
        ["最小离地间隙", "空载 200 mm / 满载 170 mm", "额定载荷下实测", "保障坑洼泥泞路面与碎石路底盘电池包安全"],
        ["最大涉水深度", "560 mm (标配涉水进气高位设计)", "车速 5-8km/h 匀速涉水", "暴雨积水路段与浅滩穿越杜绝发动机进水"],
        ["7种全地形驾驶模式", "标准/经济/运动/雪地/沙地/泥地/四驱", "驾驶模式旋钮一键切换", "不同路况自动匹配最佳扭矩分配与防滑制动策略"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.add_heading("3. 越野脱困与涉水注意事项", level=2)
    doc.add_paragraph(
        "车辆在泥地或沙地发生严重打滑受困时，需挂入 N 挡，开启后桥差速锁开关，待仪表盘金色差速锁图标常亮后挂入 D 挡缓慢稳踩油门脱困。"
        "涉水作业完成后，需以慢速行驶轻踩制动踏板 3-5 次，通过摩擦生热蒸发刹车盘片表面附着的水膜，快速恢复制动效能。"
    )

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 14. Chery iCAR 03 All Aluminum Chassis Welding Spec
def generate_chery_icar_word(out_dir: Path) -> Path:
    file_path = out_dir / "Chery_iCAR_03_All_Aluminum_Chassis_Welding_Spec.docx"
    doc = docx.Document()
    doc.add_heading("奇瑞 iCAR 03 全铝电四驱车身冷连接 SPR 铆接与 CMT 弧焊维修工艺技术标准", level=1)
    _add_meta(doc, "CHERY-ICAR-WLD-2026", "车身钣金标准", "奇瑞 iCAR 03 / iCAR 03T")

    doc.add_heading("1. 多腔蜂窝全铝车身结构连接工艺", level=2)
    doc.add_paragraph(
        "iCAR 03 采用多腔笼式全铝车身结构，扭转刚度高达 31,812 N·m/deg。"
        "碰撞受损件严禁使用传统氧乙炔气焊或普通点焊机进行修复，必须严格采用冷连接自冲铆接 (SPR) 与 CMT 冷金属过渡弧焊。"
    )

    doc.add_heading("2. SPR 铆钉与连接板厚匹配参数表", level=2)
    headers = ["板件搭接组合", "材质牌号", "总搭接厚度 (mm)", "推荐 SPR 铆钉规格", "铆扣剩余底部厚度 (mm)"]
    rows = [
        ["前纵梁压铸铝 + 铝挤压件", "AlSi10MnMg + 6061-T6", "4.5 mm", "Ф5.3 × 7.0 mm (H4硼钢)", "1.25 mm ±0.15 mm"],
        ["门槛加强板 + 铝薄板", "6008-T6 + 5182-O", "3.2 mm", "Ф5.3 × 5.5 mm (H2碳钢)", "1.10 mm ±0.10 mm"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 15. GAC Aion Y Plus Battery Pack Immersion Test
def generate_gac_aion_word(out_dir: Path) -> Path:
    file_path = out_dir / "GAC_Aion_Y_Plus_Battery_Pack_Immersion_Test.docx"
    doc = docx.Document()
    doc.add_heading("广汽埃安弹匣电池 2.0 (Magazine Battery) 72小时高浓度盐水浸泡与极限绝缘评测报告", level=1)
    _add_meta(doc, "GAC-BATT-TR-2026-11", "试验检测报告", "广汽埃安 AION Y Plus / AION S MAX / 昊铂 GT")

    doc.add_heading("1. 浸泡测试试验条件与盐水配比", level=2)
    doc.add_paragraph(
        "试验严格按照 GB 38031 附录要求，调配 3.5% NaCl 质量分数海水模拟溶液。"
        "将处于 100% 充电状态的弹匣电池 2.0 整包浸没于水深 1.5 米处，连续浸泡 72 小时，全程在线监测高压绝缘阻抗与单体电芯压差。"
    )

    doc.add_heading("2. 浸泡全流程关键时段绝缘指标记录表", level=2)
    headers = ["浸泡观察时间", "绝缘电阻值 (正极对地)", "绝缘电阻值 (负极对地)", "包内湿度传感器读数", "外观密封检查结论"]
    rows = [
        ["入水前初始状态", "> 1500 MΩ", "> 1500 MΩ", "28% RH", "密封完好，无裂痕"],
        ["浸泡 24 小时", "1200 MΩ", "1250 MΩ", "30% RH", "无进水气泡，无异味"],
        ["浸泡 48 小时", "1100 MΩ", "1150 MΩ", "31% RH", "无漏液，电压恒定"],
        ["浸泡 72 小时 (测试结束)", "1050 MΩ", "1080 MΩ", "32% RH", "出水无进水，阻抗远超500Ω/V国标"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 16. IM LS6 Silicon Carbide Inverter TSB
def generate_im_ls6_word(out_dir: Path) -> Path:
    file_path = out_dir / "IM_LS6_Silicon_Carbide_Inverter_TSB.docx"
    doc = docx.Document()
    doc.add_heading("智己 IM LS6 准900V 超级性能平台碳化硅 (SiC) 电驱逆变器驱动波形优化技术服务通报", level=1)
    _add_meta(doc, "IM-TSB-LS6-2026-05", "技术服务通告", "智己 LS6 准900V 性能版")

    doc.add_heading("1. 涉及问题与高频工况下母线电压过冲消除", level=2)
    doc.add_paragraph(
        "部分车辆在赛道模式高频弹射起步瞬间，碳化硅 MOSFET 关断过冲峰值电压可能触碰安全冗余门限。"
        "本通告发布 MCU 软件驱动参数升级包，通过主动调节门极驱动电阻脉宽动态削弱浪涌电压。"
    )

    doc.add_heading("2. 驱动波形标定与固件版本对照表", level=2)
    headers = ["软件模块名称", "升级前版本号", "升级后推荐版本", "关断过冲峰值抑制 (V)", "电驱整体效率影响"]
    rows = [
        ["前驱逆变器控制固件", "MCU_FW_V2.1.4", "MCU_FW_V2.2.0", "由 980V 降至 895V", "效率提升 0.25%"],
        ["后驱主逆变器驱动层", "MCU_DRV_V4.0.8", "MCU_DRV_V4.1.2", "由 1020V 降至 910V", "效率提升 0.38%"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


# 17. Geely Galaxy E8 Aerodynamic Underbody Repair SOP
def generate_geely_galaxy_word(out_dir: Path) -> Path:
    file_path = out_dir / "Geely_Galaxy_E8_Aerodynamic_Underbody_Repair_SOP.docx"
    doc = docx.Document()
    doc.add_heading("吉利银河 E8 全平一体化气动底盘护板与主动进气格栅 (AGS) 损伤修复作业流程", level=1)
    _add_meta(doc, "GEELY-E8-AERO-2026", "车身底盘维修", "吉利银河 E8 纯电系列")

    doc.add_heading("1. 0.199 超低风阻气动底盘平整度指标", level=2)
    doc.add_paragraph(
        "银河 E8 实现了量产轿车极限的 0.199 超低风阻系数。底盘采用全平密封护板，护板接缝高低落差必须小于 1.5mm。"
        "任何松动或刮擦变形都将导致高速气流紊乱，显著增加高速能耗与车厢风噪。"
    )

    doc.add_heading("2. 底盘护板紧固件与定位卡扣分布表", level=2)
    headers = ["护板安装分区", "材质与功能", "固定螺栓规格", "规定安装力矩 (N·m)", "卡扣损耗更换策略"]
    rows = [
        ["前保气动导流前唇", "玻纤增强聚丙烯 (GMT)", "M6 带垫片防松螺栓", "9.5 N·m", "每次拆装必须全部更新尼龙膨胀扣"],
        ["动力电池底部防护板", "高强度热冲压钢板", "M8 高强度达克罗螺栓", "25.0 N·m", "按对角线交叉顺序逐步锁紧"],
        ["后悬架气动扩散器", "碳纤微孔气动导流板", "M6 自攻螺丝", "8.0 N·m", "定位凸耳必须完全滑入车身卡槽"],
    ]
    _create_styled_table(doc, headers, rows)

    doc.save(file_path)
    logger.info(f"Generated {file_path}")
    return file_path


def generate_all_new_word_datasets(out_dir: Path) -> List[Path]:
    """Generate all 17 new Word benchmark documents."""
    generators = [
        generate_xiaomi_rescue_word,
        generate_huawei_lidar_word,
        generate_zeekr_battery_word,
        generate_li_suspension_word,
        generate_xpeng_charging_word,
        generate_byd_blade_word,
        generate_porsche_macan_word,
        generate_bmw_ix_word,
        generate_mercedes_eqxx_word,
        generate_audi_q6_word,
        generate_avatr_07_word,
        generate_denza_z9_word,
        generate_haval_raptor_word,
        generate_chery_icar_word,
        generate_gac_aion_word,
        generate_im_ls6_word,
        generate_geely_galaxy_word,
    ]
    results = []
    for g in generators:
        results.append(g(out_dir))
    return results
