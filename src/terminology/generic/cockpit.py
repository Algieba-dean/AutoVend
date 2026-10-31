"""
Generic Smart Cockpit & Connectivity Technical Terminology (src/terminology/generic/cockpit.py).
Contains 16 comprehensive generic smart cockpit technologies (category="智能座舱").
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

GENERIC_COCKPIT_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. AR-HUD增强现实抬头显示
    TechnologyEntity(
        id="generic_ar_hud_display",
        name="AR-HUD增强现实抬头显示",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Augmented Reality Head-Up Display (AR-HUD)",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱显示技术/光学生态",
        aliases=[
            "ar-hud",
            "ar hud",
            "增强现实抬头显示",
            "ar抬头显示",
            "画幅抬头显示",
            "hud抬头显示",
        ],
        summary="利用光学投影将虚拟导航箭头、车道引导线、障碍物高亮框与真实道路物理实景完美融合的挡风玻璃增强现实抬头显示系统，驾驶员无需低头即可掌控全域路况。",
        description=(
            "传统W-HUD只能在挡风玻璃上投射一个巴掌大小的二维白色车速与图标。AR-HUD通过大口径自由曲面反射镜与高精度DLP/TFT光机，"
            "在驾驶员视线前方7.5至10米外的真实道路表面铺设超过50至70英寸的虚拟动态光毯。"
            "当需要拐弯时，动态3D转向箭头如同直接铺贴在对应路口地面上；遇到前车过近或变道加塞，虚拟警示红框紧密追踪前车轮廓，"
            "实现视线零偏离、导航零走错，大幅提升驾驶直观性与高速安全性。"
        ),
        technical_principles=[
            "离轴双反射自由曲面光学系统将虚像距离扩展至7.5m-10m以消除人眼对焦睫状肌疲劳",
            "车身姿态传感器高频防抖补偿算法与ADAS感知融合动态贴地渲染引擎",
        ],
        advantages=[
            "视线零转移：彻底告别低头看仪表或中控导航，眼睛时刻聚焦前方道路，高速行驶更安全",
            "路口引导直观至极：复杂多岔立交桥上直接在正确车道‘铺路标引导’，新手绝不走错匝道",
            "结合智驾系统实时高亮标出跟车目标与潜在行人，人机共驾信任感大幅提升",
        ],
        limitations=[
            "光机体积巨大（通常达10L至15L以上），对仪表台内部空间布局与结构横梁避让要求极高",
            "戴偏光太阳镜时可能存在虚像亮度变暗现象，且对强逆光阳光倒灌防烧蚀有严格要求",
        ],
        sub_variants={
            "TFT型AR-HUD": "成本适中，显示画幅中等（约50英寸），目前主流普及方案",
            "DLP / LCoS高分辨率AR-HUD": "亮度极高、画幅突破70-100英寸、对比度卓越的旗舰方案",
        },
        representative_vehicles=["小米SU7(56英寸AR-HUD)", "问界M9(75英寸AR-HUD)", "深蓝S07", "极氪001", "理想L系列(HUD先行者)"],
        standard_labels=["AR-HUD", "增强现实抬头显示", "贴地导航", "视线零偏离", "巨幕投影", "人机共驾互信"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "现场带客户试驾体验立交桥路口：‘看！前面的导航箭头就像直接画在柏油路面上一样，该走哪条道一目了然，再也不怕高架桥连环岔路口走错多绕半小时！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 2. 高通骁龙车规级座舱芯片平台 (8155/8295)
    TechnologyEntity(
        id="generic_cockpit_soc_8295_8155",
        name="高通骁龙车规级座舱芯片平台 (8155/8295)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Qualcomm Snapdragon Automotive Cockpit Platform (SA8155P / SA8295P)",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱计算平台/芯片底层",
        aliases=[
            "8295",
            "8155",
            "高通8295",
            "高通8155",
            "骁龙8295",
            "骁龙8155",
            "座舱芯片",
        ],
        summary="汽车行业事实标准的车规级高性能座舱SoC芯片家族，8155奠定了智能多屏交互流畅体验，最新5nm制程的8295更是拥有高达30 TOPS的AI算力，支撑端侧大模型秒级流畅运行。",
        description=(
            "智能汽车座舱从单块小屏演变为多屏联动、3D沉浸渲染与AI大模型交互，对车规计算平台的性能要求极高。"
            "高通8155（7nm）长期以来是20万级以上智能车流畅体验的标杆；新一代高通8295（5nm）CPU算力提升2倍、GPU提升3倍，"
            "并内置高达30 TOPS的独立NPU张量计算核心，单芯片即可同时驱动仪表屏、中控大屏、副驾娱乐屏、后排吸顶屏与AR-HUD等最多11块显示终端，"
            "同时在离线车端顺畅运行多模态语音大语言模型，系统操作丝滑如最新款旗舰手机。"
        ),
        technical_principles=[
            "车规级高低温制程与高可靠Kyro CPU、Adreno GPU以及Hexagon NPU异构计算架构",
            "Hypervisor硬件级虚拟机隔离实现仪表安全OS与座舱安卓娱乐OS硬隔离独立运行",
        ],
        advantages=[
            "车机滑动、缩放地图操作丝滑流畅毫无卡顿感，告别传统老旧车机迟钝体验",
            "支持多屏独立高帧率3D游戏与真3D车控渲染，视觉交互极为酷炫生动",
            "强大的车端NPU算力支持车端离线运行百亿级AI大模型，无网环境下语音助手依然秒回",
        ],
        limitations=[
            "高端车规芯片供应主要依赖全球头部半导体巨头，需要深厚软硬件联合适配周期",
            "整机高负荷工作功耗较大，需要精细的主动风冷或液冷散热设计",
        ],
        sub_variants={
            "骁龙8155平台 (SA8155P)": "主流高性价比成熟方案，支撑双屏或三屏日常丝滑交互",
            "骁龙8295平台 (SA8295P)": "旗舰新一代方案，5nm制程，30 TOPS AI算力，支持端侧大模型与3D引擎渲染",
        },
        representative_vehicles=["小米SU7(8295)", "极氪001/007(8295)", "小鹏X9/P7+(8295)", "理想L系列(8295/双8155)", "蔚来ET5/ES6"],
        standard_labels=["高通8295", "8155", "旗舰座舱芯片", "30TOPS算力", "车机丝滑如手机", "多屏流畅渲染"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向用户现场演示中控屏手势拖拽：‘我们车搭载的是目前全球最顶尖的5nm高通8295芯片，您像划手机一样快速滑动地图或者拖动3D车模，完全没有任何掉帧卡顿，用上五年依然顺畅如新！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 3. 座舱大语言模型与多模态AI语音助手
    TechnologyEntity(
        id="generic_voice_assistant_large_language_model",
        name="座舱大语言模型与多模态AI语音助手",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="In-Cabin LLM & Multimodal AI Voice Assistant",
        category=TechCategory.COCKPIT_OS,
        subcategory="智能人机交互/车载AI生态",
        aliases=[
            "座舱大模型",
            "语音大模型",
            "车载语音助手",
            "多模态语音助手",
            "可见即可说",
            "连续对话语音",
        ],
        summary="融入生成式大语言模型（LLM）的智能座舱语音交互系统，支持全车四音区独立识别、可见即可说、毫秒级连续对话，以及复杂多意图理解与用车百科百事通。",
        description=(
            "传统车载语音只能生硬识别预设指令（如‘打开空调’，一旦换成‘我有点冷’就无所适从）。"
            "结合大语言模型的新一代座舱语音助手具备极高情商与常识推理能力：车主随口说‘副驾觉得吹得头疼，而且帮我找一家附近评分高还能带宠物吃饭的川菜馆，中途顺便去加个电’，"
            "语音大模型能瞬间拆解出调温度、避开头部出风、选餐馆、规划补能路线4重意图并一键执行；同时车内支持全车四音区精准拾音定位，主驾说话不影响后排孩子听睡前故事。"
        ),
        technical_principles=[
            "全车四音区麦克风阵列波束成形（Beamforming）声源定位与回声降噪（AEC）",
            "车云协同大语言模型（LLM）自然语言理解与意图路由分发引擎",
        ],
        advantages=[
            "彻底解放双手：90%以上的车控按键均可通过自然口语控制，驾驶途中更专注更安全",
            "支持一句话多意图并发执行、无唤醒词连续自然对话，像跟真人助理聊天一样自然随性",
            "化身随车用车百科全书与育儿百科，长途自驾为全家提供百科问答、故事伴读与旅游向导",
        ],
        limitations=[
            "弱网或隧道无网络环境下，部分依赖云端超大模型的复杂推理功能需要回退至本地离线基础语音包",
            "全车多人同时大声喧哗时，极端工况下麦克风偶发交叉拾音干扰",
        ],
        sub_variants={
            "四音区精准识别": "主驾、副驾、左后、右后独立声场拾音，指令互不串门",
            "端云协同大模型": "本地小模型负责极速车控毫秒响应，云端大模型负责百科与逻辑创作",
        },
        representative_vehicles=["鸿蒙智行(小艺大模型)", "理想全系(Mind GPT大模型)", "小米SU7(小爱大模型)", "小鹏全系(小P大模型)", "蔚来NOMI"],
        standard_labels=["语音大模型", "全车四音区", "可见即可说", "连续对话", "一句话多意图", "情感化AI伙伴"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "现场邀请客户连续说一长串自然口语：‘您随便说话，比如把左边后视镜往上调一点、空调开到24度并给后排关上窗户，您看！一次性全给您办妥了，根本不用分次反复呼叫！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 4. 车载OLED / Mini-LED高色域中控大屏
    TechnologyEntity(
        id="generic_oled_mini_led_screen",
        name="车载OLED / Mini-LED高色域中控大屏",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Automotive High-Gamut OLED & Mini-LED Center Displays",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱显示技术/屏幕硬件",
        aliases=[
            "oled中控屏",
            "mini-led屏",
            "车载oled",
            "mini led",
            "高刷中控屏",
            "3k中控屏",
        ],
        summary="采用自发光OLED或多分区背光Mini-LED的车规级超高清显示大屏，具备百万比一超高对比度、千尼特以上强光可视峰值亮度与超窄极边框设计。",
        description=(
            "传统车载LCD屏幕由于背光常亮，黑夜驾驶时黑底画面总是灰蒙蒙一片，且大太阳直射下画面严重泛白看不清反光。"
            "车载OLED/Mini-LED显示屏拥有真正的像素级控光，纯黑画面像素点完全不发光，对比度突破1,000,000:1，黑夜中屏幕边缘与黑色内饰融为一体，毫无刺眼光晕；"
            "峰值亮度高达1000至1600nits，即便在夏日正午强烈的侧向直射阳光下，导航细节与倒车影像依然鲜艳清晰、一目了然。"
        ),
        technical_principles=[
            "OLED有机自发光双层串联架构（Tandem OLED）大幅延长使用寿命并抑制车规级烧屏风险",
            "Mini-LED千级微米级独立局部调光分区（Local Dimming）与抗眩光（AG/AR/AF）三防镀膜",
        ],
        advantages=[
            "纯粹深邃的黑色与极高动态范围（HDR），夜间开车不刺眼，观看大片色彩极其绚丽震撼",
            "烈日阳光下清晰可读，彻底解决传统大屏反光看不清导航路线的安全隐患",
            "边框可压缩至窄边框极值，屏占比超90%，车内视觉高级感与科技氛围拉满",
        ],
        limitations=[
            "车规级高低温与抗震耐久性要求极高，成本远超传统普通单背光LCD屏幕",
            "早期单层OLED在极端高温暴晒下可能存在寿命衰减考验，需采用双层Tandem串联结构保障",
        ],
        sub_variants={
            "Mini-LED背光屏": "超高亮度（可达1500+ nits），无任何烧屏隐患，日间可视性极强（如理想、蔚来）",
            "双层串联Tandem OLED": "色彩纯度与对比度巅峰，超薄低功耗（如问界M9、极氪007）",
        },
        representative_vehicles=["理想MEGA/L9(双Mini-LED三联屏)", "问界M9(光场屏/OLED)", "极氪001/007", "小米SU7(3K超清中控)", "蔚来ET7"],
        standard_labels=["Mini-LED", "车载OLED", "百万对比度", "阳光下清晰可见", "超窄边框", "家庭影院级画质"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "在阳光充足的展厅或户外带客户看屏幕：‘很多车在太阳底下一照屏幕反光全是白蒙蒙的，您看我们的Mini-LED/OLED大屏，在强光下不仅色彩依然鲜亮锐利，晚上开车也不会有灰蒙蒙的刺眼漏光！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 5. 杜比全景声与多声道车载空间音频系统
    TechnologyEntity(
        id="generic_dolby_atmos_surround_sound",
        name="杜比全景声与多声道车载空间音频系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="In-Cabin Dolby Atmos & Spatial Audio Surround System",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱影音工程/声学生态",
        aliases=[
            "杜比全景声",
            "空间音频",
            "车载音响",
            "7.1.4音响",
            "头枕音响",
            "车载全景声",
        ],
        summary="由15至25个以上高保真扬声器与独立功放组成的7.1.4多声道音响系统，结合杜比全景声空间音频算法，将车舱打造为声音随空间立体流转的移动音乐厅与私人影院。",
        description=(
            "传统车载音响仅在车门配置左右立体声声道，声场平淡扁平。多声道空间音频系统在车门、中控高位、前后顶棚（4个天空声道）以及主副驾座椅头枕内布置数十颗扬声器，"
            "总功率可达1000W至2000W以上。结合杜比全景声（Dolby Atmos）基于对象的音频渲染技术，能够精准定位雨滴从车顶滴落、赛车从左后方呼啸疾驰至右前方的三维立体轨迹；"
            "主驾头枕音响还支持独立私密导航播报与电话接听，副驾和后排听歌追剧完全不受打扰。"
        ),
        technical_principles=[
            "7.1.4物理声道布局（前左/中/右、环绕、后环绕、低音炮及4个车顶天空沉浸声道）",
            "座舱声学微型腔体仿真与车规级大功率D类DSP数字功放多通道主动分频",
        ],
        advantages=[
            "带来身临其境的三维立体沉浸感，高音通透、人声温润、低音下潜深沉有弹性",
            "主驾头枕专属私密声场：导航提醒和蓝牙电话只在驾驶员耳边响起，不打扰车内其他人休息",
            "搭配车载高清大屏，停车休憩时即刻变身豪华私人家庭巨幕影院",
        ],
        limitations=[
            "全套扬声器与大功率功放重量较大（增加数十公斤），对全车内饰门板防共振抑制有严苛要求",
            "发挥完整全景声震撼效果需要流媒体平台提供原生杜比高保真音源配合",
        ],
        sub_variants={
            "7.1.4声道标准全景声": "包含4个车顶天空声道的经典沉浸式方案",
            "双头枕私密空间音频": "主副驾双头枕集成扬声器，支持声场完全独立分区互不干扰",
        },
        representative_vehicles=["理想L系列(全系标配7.1.4杜比全景声)", "蔚来全系(标配23扬声器7.1.4)", "小鹏G9(5D音乐座舱)", "极氪001(雅马哈28扬声器)", "小米SU7(25扬声器)"],
        standard_labels=["杜比全景声", "7.1.4声道", "空间音频", "主驾头枕音响", "移动音乐厅", "千瓦级功放"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带客户坐进车内闭上眼放一段杜比全景声大片：‘您听这直升机从头顶飞过的轰鸣声、这大雨淅淅沥沥打在天窗上的声音，整辆车就是您的移动专属音乐厅，忙碌一天下班在车里静静坐半小时就是最好的解压！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 6. 车机多设备无缝手车互联生态 (CarPlay/HiCar/Carlink)
    TechnologyEntity(
        id="generic_cross_device_smartphone_connectivity",
        name="车机多设备无缝手车互联生态 (CarPlay/HiCar/Carlink)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Seamless Smartphone-to-Vehicle Connectivity Ecosystem",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱互联互通/软件生态",
        aliases=[
            "手车互联",
            "carplay",
            "hicar",
            "carlink",
            "手机车机互联",
            "无缝流转",
            "手机投屏",
        ],
        summary="支持将智能手机的算力、应用、导航与多媒体无感流转至中控大屏的互联技术体系，包含苹果无线CarPlay、华为HiCar、ICCOA Carlink以及原生手机生态跨端互联。",
        description=(
            "用户在手机上收藏的地点、正在听的歌曲或正在聊天的通话，传统车机往往无法共享同步。手车互联生态通过高速双频Wi-Fi与低功耗蓝牙实现上车即自动感应连接。"
            "手机上的导航路线自动流转至中控大屏并继续导航，正在播放的音乐无缝在全车音响接着播放；"
            "车主可以直接在大屏上触控操作手机App，甚至利用车身摄像头与麦克风直接接入手机视频会议，真正实现数字生活的无缝衔接。"
        ),
        technical_principles=[
            "Wi-Fi Direct点对点高速局域通道与音视频硬编码低延迟低压缩投屏协议",
            "跨终端分布式软总线协议实现硬件能力互相调用与状态无感同步",
        ],
        advantages=[
            "上车无感秒连，手机上的导航直接上屏，省去手动重新搜索地址的繁琐步骤",
            "应用生态无限扩展：手机有什么App，车机就能方便使用，彻底摆脱车机应用商店生态匮乏困境",
            "导航数据与路况始终是手机最新版，绝不落后老化",
        ],
        limitations=[
            "部分基于投屏的互联方案无法深度调用车辆核心三电数据与车身硬件（如无法通过投屏调节座椅空调）",
            "无线高码率投屏长时间运行可能导致手机发热，建议配合车载无线充电板使用",
        ],
        sub_variants={
            "无线Apple CarPlay": "苹果手机用户最青睐的极简纯净方案",
            "华为HiCar": "华为手机深度融合方案，支持分布式应用流转与畅连通话",
            "原生生态手车互联": "如小米澎湃OS手车互联、魅族Flyme Link，支持手机车机软硬件全打通",
        },
        representative_vehicles=["小米SU7(澎湃OS+CarPlay全兼容)", "问界/智界全系(华为鸿蒙HiCar/软总线)", "领克08(Flyme Auto)", "宝马全系(无线CarPlay)"],
        standard_labels=["手车互联", "无线CarPlay", "华为HiCar", "应用无缝流转", "上车即连", "手机生态上车"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向离不开手机的现代用户展示：‘上车前在微信里别人发来的餐厅定位，上车一发动，大屏立刻自动弹出来问您是否开始导航；戴着耳机听的音乐一开门车里接着唱，不需要您多按任何一个键！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 7. UWB超宽带微定位数字车钥匙
    TechnologyEntity(
        id="generic_uwb_digital_car_key",
        name="UWB超宽带微定位数字车钥匙",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="UWB (Ultra-Wideband) High-Precision Digital Car Key",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱进入与安防/无线定位",
        aliases=[
            "uwb车钥匙",
            "数字车钥匙",
            "手机钥匙",
            "uwb微定位",
            "无感解锁",
            "蓝牙车钥匙",
        ],
        summary="采用纳秒级超短脉冲无感测距的超宽带无线定位车钥匙技术，定位精度达厘米级并天然免疫中继攻击，车主只需手机放在裤兜，走近车辆自动迎宾解锁，远离自动闭锁升窗。",
        description=(
            "传统蓝牙钥匙通过信号强弱（RSSI）估算距离，遇到人体遮挡或天气变化经常出现‘人站在车门边拉不开门’或者‘人在家里车门在楼下莫名解锁’的尴尬，且易被窃贼通过信号放大器实施中继盗车。"
            "UWB超宽带技术利用飞行时间测距（ToF），在纳秒级时间尺度测量电磁波往返绝对物理距离，精度高达厘米级。"
            "车辆能精准知道主人位于车前、车尾还是车身左侧：走到2米外自动亮起迎宾光毯，走到门边自动弹开隐藏式门把手，人进车内瞬间踩刹车即走；离开车身3米自动锁车升窗，优雅从容无需掏出手机或物理钥匙。"
        ),
        technical_principles=[
            "纳秒级窄脉冲ToF飞行时间物理测距与全车3-5颗UWB高精度定位天线交汇计算",
            "符合CCC/ICCE国际联盟安全标准的AES-128加密时间戳滚动防中继重放攻击",
        ],
        advantages=[
            "感应灵敏稳定：真正实现‘无感进出’，无论手机放在口袋还是背包，拉门即开，绝不罚站",
            "绝对物理安全：飞行时间无法被信号中继放大器伪造欺骗，防盗安全级别与物理芯片钥匙相当",
            "支持亲友远程微信/短信一键分享临时数字钥匙，异地朋友借车或帮取后备箱快递极其方便",
        ],
        limitations=[
            "需要智能手机本身硬件内置UWB芯片支持（如iPhone 11以上、华为、小米近两代高端旗舰）",
            "全车需布置多个UWB定位基站锚点芯片与线束，成本高于单一低功耗蓝牙模块",
        ],
        sub_variants={
            "UWB+BLE+NFC三合一钥匙": "UWB负责主力厘米级无感进出，BLE负责远距离寻车，NFC负责手机没电关机时刷B柱应急解锁",
        },
        representative_vehicles=["小米SU7", "极氪001/007", "问界M9", "蔚来全系", "宝马iX/i7", "特斯拉Model 3/Y"],
        standard_labels=["UWB车钥匙", "无感解锁", "厘米级定位", "防中继盗车", "手机即钥匙", "离开自动锁车"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "让客户把手机装兜里体验上下车：‘您看，手里提着大包小包不用翻包找钥匙，走近车门车子自动亮灯开锁把手弹出，坐进去踩刹车就能开走；下车后直接转身走人，车子自动锁死升起车窗，彻底告别带钥匙的累赘！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 8. 零重力智能电控减压座椅
    TechnologyEntity(
        id="generic_electronically_controlled_active_seat",
        name="零重力智能电控减压座椅",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Zero-Gravity Electronically Controlled Active Seat",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱舒适系统/人机工学座椅",
        aliases=[
            "零重力座椅",
            "智能座椅",
            "座椅通风加热按摩",
            "主动侧翼支撑",
            "零重力副驾",
            "电动腿托座椅",
        ],
        summary="根据NASA失重姿态人机工学设计的全向电调多连杆座椅，通过将大腿、臀部与躯干调整至120度以上舒适夹角，使人体心脏与膝盖处于同一水平线，实现近乎零压力的极致躺卧放松。",
        description=(
            "普通汽车座椅靠背放倒后，臀部依然承受全身主要重量，腰部容易悬空酸痛。零重力座椅配备双滑轨多连杆机构与高行程电动腿托，"
            "一键开启零重力模式后，座垫整体后倾仰角抬高，靠背向后舒展，腿托平稳升起，让人体躯干与大腿夹角维持在113°至128°的最佳失重姿态。"
            "全身重力均匀分散至臀部、后背与小腿大面积区域，压强降低50%以上，促进静脉血液回流；"
            "同时集成16点气袋式座椅深层按摩、吸风式座椅通风、石墨烯快速加热以及过弯时主动向内侧充气夹紧的主动侧翼支撑，长途驾驶久坐不累。"
        ),
        technical_principles=[
            "NASA航天员失重状态中立姿态（Neutral Body Posture）人体压力拓扑分布仿真",
            "集成双电机联动升降机构、气动按摩泵阀矩阵与底盘横向G值联动的主动支撑气囊",
        ],
        advantages=[
            "极致舒适解压：服务区或午休小憩时一键变身头等舱卧铺，彻底消除腰椎与臀部疲劳",
            "过弯主动侧翼充气支撑：激烈驾驶或盘山路时自动夹紧腰部，身体不摇晃，驾驶更自信更有安全感",
            "通风、加热、石墨烯理疗按摩全功能拉满，冬暖夏凉四季如春",
        ],
        limitations=[
            "零重力完全躺平时占用较大的前后排轴向纵向空间，通常需要在后排无人或特定车位布局下舒展",
            "座椅骨架集成电机气囊多，座椅自重相对较大，对安全带集成方式（全内置安全带）要求更高",
        ],
        sub_variants={
            "副驾零重力座椅 (女王副驾)": "专为副驾驶打造，带电动折叠脚踏与超长一体式腿托",
            "二排双独立零重力座椅": "高端MPV与大型旗舰SUV专属豪华老板座",
        },
        representative_vehicles=["问界M7/M9(零重力座椅)", "理想MEGA/L9", "蔚来ES8/EC7(女王副驾)", "极氪009", "智己LS7"],
        standard_labels=["零重力座椅", "NASA失重姿态", "一键躺平", "全身减压", "主动侧翼支撑", "气囊深度按摩"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带用户家人体验一键零重力：‘平时工作累了或者中午想在车里睡个午觉，按一下按键座椅自动升起躺平，像浮在云端一样全身放松，腰部有满满的支撑，躺在上面闭上眼5分钟就能沉沉入睡！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 9. DMS驾驶员防疲劳与OMS后排乘客关爱监控系统
    TechnologyEntity(
        id="generic_dms_oms_in_cabin_monitoring",
        name="DMS驾驶员防疲劳与OMS后排乘客关爱监控系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="In-Cabin Driver (DMS) & Occupant (OMS) Monitoring System",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱安全感知/舱内视觉系统",
        aliases=[
            "dms",
            "oms",
            "疲劳监测",
            "驾驶员状态监测",
            "后排遗留检测",
            "座舱活体检测",
        ],
        summary="采用车规级近红外摄像头与生物识别AI视觉算法，实时追踪驾驶员眨眼频率、打哈欠、视线偏离防疲劳分心，并关照后排儿童遗留防窒息的舱内全域安全守护系统。",
        description=(
            "疲劳驾驶与低头看手机是引发高速致命车祸的主要隐患。DMS系统在方向盘转向柱或A柱布置940nm无形红外补光与专用红外摄像头，"
            "即使驾驶员戴着墨镜或在漆黑夜间，AI也能精准捕捉眼皮开合眨眼频率（PERCLOS）、眼球视线注视方向与频繁打哈欠动作。"
            "一旦发现低头超过2秒或闭眼打瞌睡，立刻通过安全带预紧震动、语音大声报警甚至释放提神香氛强制唤醒；"
            "OMS系统则利用顶棚广角红外镜头监测后排，若锁车后检测到有儿童或宠物遗留在车内，立刻鸣笛报警并推送到车主手机，同时自动开启空调通风，杜绝高温窒息惨剧。"
        ),
        technical_principles=[
            "940nm不可见近红外主动LED补光与IR-Cut红外光学滤波成像技术",
            "基于面部三维68个特征点实时追踪、视线向量估计（Gaze Estimation）与胸腔微呼吸微动感知",
        ],
        advantages=[
            "全天候防疲劳分心：夜间戴太阳镜依然穿透识别，将疲劳分心事故苗头扼杀在萌芽之中",
            "生命关爱防遗留：有效防止夏季粗心父母将孩子或宠物误留在暴晒车内的致命安全事故",
            "支持人脸识别自适应记忆：上车刷脸即自动切换专属后视镜角度、座椅位置与车机歌单",
        ],
        limitations=[
            "需要严格遵守用户隐私安全法规，舱内视觉数据必须全在车端边缘离线处理，严禁上传云端",
            "驾驶员若佩戴全黑遮挡型特种护目镜可能对眼睛视线判断产生轻微边缘遮挡",
        ],
        sub_variants={
            "DMS驾驶员监测系统": "专注驾驶员面部疲劳与视线偏离警示",
            "OMS全舱乘客关爱系统": "兼顾后排活体检测、儿童安抚与手势隔空交互",
        },
        representative_vehicles=["理想L系列", "小鹏G6/G9/X9", "问界全系", "蔚来全系", "特斯拉全系"],
        standard_labels=["DMS疲劳监测", "OMS乘客关爱", "红外夜视识别", "视线追踪", "儿童防遗留", "安全防线"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向注重家庭安全的客户介绍：长途开车最怕不知不觉打瞌睡，DMS比您自己还懂您的疲倦，稍有打盹就会立刻震动安全带提醒您进服务区；锁车后如果不小心把熟睡的孩子留在后排，手机会立刻急促报警并自动开空调，给全家人最高级别的贴心守护。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 10. 车载全生命周期OTA远程固件/软件升级 (FOTA/SOTA)
    TechnologyEntity(
        id="generic_ota_firmware_update",
        name="车载全生命周期OTA远程固件/软件升级 (FOTA/SOTA)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Full-Lifecycle Over-The-Air (OTA) Remote Update (FOTA / SOTA)",
        category=TechCategory.COCKPIT_OS,
        subcategory="整车软件架构/远程更新",
        aliases=[
            "ota",
            "ota升级",
            "fota",
            "sota",
            "远程升级",
            "整车ota",
        ],
        summary="支持无需前往4S店即可通过无线蜂窝网络远程为全车数十个ECU控制器更新算法与新增功能的整车级远程升级体系，让车辆实现‘常用常新、终身进化’。",
        description=(
            "传统燃油汽车出厂即定型，遇到变速箱逻辑Bug必须把车开到4S店插电脑刷机，车机软件更是数年不变。整车OTA分为应用软件升级（SOTA）与底层固件升级（FOTA）。"
            "SOTA支持中控App、导航地图、语音大模型与UI主题的静默下载更新；"
            "整车级FOTA更支持对动力电机逆变器算法、底盘空气悬架阻尼标定、ESP制动响应以及高阶智驾算法进行深层次重构与优化升级，"
            "车主每天早上醒来，车辆都可能新增了更聪明的自动泊车功能或更省电的续航算法，真正做到了‘汽车成为移动智能终端’。"
        ),
        technical_principles=[
            "双分区差分镜像备份（A/B Dual Partition Rollback）确保升级断电绝对防变砖",
            "端到端数字签名验签、TLS安全传输与全车车载以太网高速分布式ECU刷写调度",
        ],
        advantages=[
            "车辆终身持续进化：交付并不是终点，每年都能解锁新的酷炫功能与更好的驾乘体验",
            "免除奔波维保烦恼：软件算法缺陷在后台夜间全自动修复，无需车主请假专程去4S店",
            "保值率更高：几年过去车机功能依然紧跟潮流，不会过时老化",
        ],
        limitations=[
            "固件大版本FOTA升级期间（通常15-30分钟）整车高压下电不可行驶，需合理预约在夜间闲时执行",
            "对整车各ECU通信带宽、代码签名安全性与防黑客攻击网络安全防护提出极端严苛要求",
        ],
        sub_variants={
            "SOTA (应用软件级OTA)": "车机多媒体、UI界面、地图导航等车载App更新",
            "FOTA (整车固件级OTA)": "智驾大模型、底盘CDC调校、电机动力输出及电池BMS算法深层刷写",
        },
        representative_vehicles=["特斯拉全系(OTA行业开拓者)", "理想全系", "小鹏全系", "蔚来全系", "极氪全系", "小米SU7"],
        standard_labels=["整车OTA", "FOTA固件升级", "SOTA软件更新", "常用常新", "双分区防变砖", "越开越好开"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向用户讲解智能车的保值核心：买传统车是越开越旧，买我们的智能车是越开越新！每隔几个月我们就会推送一次大版本OTA升级，优化驾驶手感、增加新的大模型功能，让您三年后开起来依然像刚提的新车一样前卫！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 11. 电子外后视镜系统 (CMS)
    TechnologyEntity(
        id="generic_electronic_rearview_mirror_cms",
        name="电子外后视镜系统 (CMS)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Camera Monitor System (CMS) / Electronic Exterior Mirrors",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱视觉与感知/后视显示",
        aliases=[
            "电子外后视镜",
            "cms",
            "流媒体后视镜",
            "电子后视镜",
            "数字外后视镜",
        ],
        summary="采用车外小巧高清摄像头替代传统大块玻璃镜片，并在车门内侧A柱配备专用高刷液晶屏的新一代数字后视系统，兼具极佳雨夜穿透视野与超低风阻表现。",
        description=(
            "在倾盆暴雨的雨夜中，传统光学后视镜的镜片和侧窗玻璃常挂满水珠甚至起厚雾，加之后方远光灯强烈炫目，驾驶员变道时几乎‘全盲盲开’极易发生追尾事故。"
            "CMS（Camera Monitor System）电子外后视镜采用微型疏水自加热摄像头与舱内专用OLED屏联动。"
            "摄像头外形仅传统镜子三分之一大，减少风阻4%~7%；内部集成HDR强光抑制与雨雪透视算法，暴雨天无视水珠倒影，黑夜中自动提高暗部亮度看清后车车道，"
            "转向或变道时屏幕还会自动拉宽视野消除盲区，带来前所未有的开阔全天候视界。"
        ),
        technical_principles=[
            "车规级超低延迟（<50ms）图像ISP处理与以太网点对点差分视频传输",
            "电加热微型蓝宝石自清洁镜头与低风阻空气动力学外壳流线设计",
        ],
        advantages=[
            "全天候视野清晰：暴雨天无视水珠干扰，夜晚自动压制后车远光灯并提亮暗处车道",
            "显著降低风阻风噪：外壳迎风截面积大幅缩小，整车高速风噪更低且纯电续航提升10-20km",
            "智能动态盲区扩展：打转向灯或挂倒挡时，车内屏幕画面自动放大并旋转视角，盲区完全归零",
        ],
        limitations=[
            "驾驶员需要短时间适应视线向车门内侧A柱屏幕看的习惯调整",
            "硬件系统造价与损坏后更换成本高于传统普通机械玻璃镜片",
        ],
        sub_variants={
            "A柱内嵌式显示屏": "屏幕布置在车门两侧与A柱交界处，最符合人体视线自然习惯",
            "流媒体内后视镜": "专用于后车窗视线受阻时的中央数字流媒体车内后视镜",
        },
        representative_vehicles=["路特斯Eletre/Emeya", "极氪001/007(部分选装)", "北汽极狐阿尔法S", "奥迪e-tron(海外版)"],
        standard_labels=["电子外后视镜", "CMS", "雨夜无盲区", "防远光眩目", "超低风阻", "动态视野扩展"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向经常雨夜开车的客户做对比：下暴雨时侧窗玻璃全是雨水，传统镜子根本什么都看不见；电子后视镜的摄像头自带防雨水加热，车内屏幕上后方三条车道清清楚楚、明亮如昼，变道超车底气十足！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 12. 全景智能感光EC调光天幕
    TechnologyEntity(
        id="generic_panoramic_sunroof_ec_dimming",
        name="全景智能感光EC调光天幕",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Panoramic EC (Electrochromic) Smart Dimming Canopy Sunroof",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱环境与玻璃科技/光学变色",
        aliases=[
            "ec调光天幕",
            "调光玻璃",
            "全景天幕",
            "感光天幕",
            "电致变色天幕",
            "防晒天幕",
        ],
        summary="采用电致变色（EC）全固态电致变色薄膜技术的大面积全景玻璃天顶，无需传统物理遮阳帘即可通过施加低压电场实现玻璃在透明与深色墨镜间无级调光防晒隔热。",
        description=(
            "纯电动车为了追求头部开阔空间与超大通透感，普遍采用一体化全景天幕，但在盛夏酷暑烈日下，传统玻璃若无物理遮阳帘，车内乘客头顶往往被晒得滚烫无比。"
            "智能EC调光天幕在双层夹胶玻璃之间注入了纳米级电致变色功能层。在微弱电场控制下，内部离子发生可逆电化学变色反应，"
            "玻璃可在极高透光的无色透明状态与超深墨黑私密状态之间平滑过渡，紫外线隔绝率高达99.9%，红外线热量阻隔率超85%，"
            "既保留了纯粹通透的无遮挡星空视野，又彻底解决了烈日暴晒的“烤顶”痛点。"
        ),
        technical_principles=[
            "全固态电致变色三明治膜层结构（透明电极+离子储存层+电解质+电致变色薄膜）",
            "环境照度与车速联动自适应微调控电压控制器驱动",
        ],
        advantages=[
            "夏日绝不晒头：阻隔99.9%紫外线与绝大部分红外热量，车内清凉防晒",
            "省去沉重机械遮阳帘与电机导轨，车内乘员头部垂直空间释放2-3厘米，绝不压抑",
            "变色过程平滑柔和，支持多挡手动调节或自动根据外界阳光强弱智能变色",
        ],
        limitations=[
            "整块高品质EC调光夹胶玻璃的生产成本明显高于普通双层隔热玻璃",
            "从全透明完全渐变至最深墨色通常需要几十秒至1分钟的化学离子迁移时间",
        ],
        sub_variants={
            "第三代全固态EC调光玻璃": "工作电压极低（1.5-3V），耐候寿命超15年，无漏液分层风险",
            "分区独立调光天幕": "支持前后排独立调节天顶明暗度",
        },
        representative_vehicles=["极氪001/007(EC调光天幕)", "蔚来ET7/EC7", "比亚迪海豹", "问界M9", "保时捷Taycan"],
        standard_labels=["EC调光天幕", "电致变色", "99.9%隔绝紫外线", "烈日不晒头", "无物理遮阳帘", "星空通透全景"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向担心夏天全景天幕太晒的客户演示：‘很多电车夏天头顶像顶着个火炉，逼得车主戴草帽开车；我们的EC天幕轻轻一按按键或者一句话，玻璃立刻变成深邃的墨镜色，阳光热量全被挡在车外，既凉爽防晒又享受超大通透视野！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 13. 车载压缩机冷暖双用智能冰箱
    TechnologyEntity(
        id="generic_in_car_refrigerator_cooling_heating",
        name="车载压缩机冷暖双用智能冰箱",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="In-Cabin Smart Compressor Dual-Zone Heating & Cooling Refrigerator",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱生活舒适科技/车载家电",
        aliases=[
            "车载冰箱",
            "压缩机冰箱",
            "冷暖冰箱",
            "车载小冰箱",
            "智能保温箱",
        ],
        summary="采用车规级直流变频独立压缩机的车载冷暖恒温箱，制冷温控范围达-6℃至50℃，夏天冰镇可乐冷饮、冬天温热婴儿母乳与热咖啡，支持离车24小时持续保温保鲜。",
        description=(
            "早期部分车型配备的是低成本半导体电子制冷片，制冷速度极其缓慢且最低只能降至十几度，夏天根本冰不透饮料。"
            "现代高端车载冰箱配备车规级高能效直流变频微型压缩机，制冷功率强劲，短时间内即可迅速将温度降至零下6℃（实现真正结冰冻感）；"
            "同时支持反向加热模式（最高50℃），满足冬天随时喝到暖胃热饮或新手宝妈外出给婴儿温奶的需求。"
            "依托新能源动力电池充沛电量，即便停车熄火锁车离开，冰箱依然可在后台静默恒温运行24至48小时，露营食品与生鲜牛排持久保鲜不化冻。"
        ),
        technical_principles=[
            "耐高低温抗颠簸专用直流变频微型旋转式压缩机与环保环保冷媒回路",
            "独立低温风道循环与BMS离车低电量自动切断双重保护机制",
        ],
        advantages=[
            "真正强效制冷：温控范围宽广（-6℃至50℃），冷饮真冰镇，热饮真保温",
            "锁车持续工作：逛街、露营、自驾途中离车数小时，生鲜食材与饮料始终处于冰爽最佳状态",
            "隐蔽集成于中央扶手箱或后排座椅下方，不占用后备箱宝贵的行李装载空间",
        ],
        limitations=[
            "压缩机与制冷管路相比半导体片占用一定中控扶手箱内部纵深容积",
            "虽然功耗极低（每天耗电约0.5-1度），但在动力电池亏电极端状态下系统会主动断电保护",
        ],
        sub_variants={
            "中央扶手箱嵌入式冰箱": "前排主副驾随手可取，容量约4.5L-8L",
            "后排抽屉式电动滑轨大冰箱": "后排尊享豪华配置，容积可达8L-12L（如理想L9、极氪009、腾势D9）",
        },
        representative_vehicles=["理想L9/L8/MEGA", "极氪009/001 FR", "问界M9", "腾势D9", "小米SU7(选装拓展车载冰箱)"],
        standard_labels=["车载压缩机冰箱", "冷暖双用", "零下6度真正冰镇", "离车恒温保鲜", "自驾露营神器", "宝妈温奶必备"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "打开扶手箱拿出一罐冰镇可乐递给客户：‘大夏天开车口干舌燥，车里随时能拿出一罐零下6度透心凉的冰镇汽水；家里有宝宝的，出门带母乳直接保温50度拿出来就能喂，幸福感简直爆棚！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 14. 路噪主动降噪系统 (RNC / ANC)
    TechnologyEntity(
        id="generic_active_noise_cancellation_rnc",
        name="路噪主动降噪系统 (RNC / ANC)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Road Noise Cancellation (RNC) & Active Noise Cancellation (ANC)",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱声学工程/NVH消噪科技",
        aliases=[
            "主动降噪",
            "rnc",
            "anc",
            "路噪降噪",
            "车载主动降噪",
            "声学消噪",
        ],
        summary="通过在底盘悬架关键节点布置加速度传感器采集路面粗糙震动，并在车内车载扬声器毫秒级反相发射抵消声波的路噪主动消除技术，中低频粗糙轰鸣路噪大幅降低3分贝以上。",
        description=(
            "纯电动车取消了内燃机轰鸣声之后，高速行驶时轮胎碾压粗糙沥青柏油路面产生的‘轰隆隆’中低频路噪（100-300Hz）变得尤为突兀，传统堆砌被动隔音棉方案增重明显且无法彻底吸收低频波。"
            "路噪主动降噪（RNC）在前后底盘悬架副车架上布置4至8颗高灵敏加速度振动传感器，在轮胎刚刚接触颠簸路面的几毫秒内提前预测车内将要产生的噪声波形；"
            "车规级DSP数字功放瞬间驱动车门与顶棚扬声器发射振幅相同、相位相反（180度反向）的声波，在乘客耳朵处直接发生干涉相消，车厢瞬间变得静谧如深海图书馆。"
        ),
        technical_principles=[
            "底盘高带宽三轴加速度计与车内顶棚误差拾音麦克风阵列",
            "自适应滤波算法（Filtered-X LMS）在毫秒级极窄时间窗口内完成反相声波计算与发射",
        ],
        advantages=[
            "精准定向消除最折磨人耳的100-300Hz低频粗糙路噪，长途高速行驶绝不耳鸣轰头",
            "相比传统死板堆砌几十公斤笨重沥青阻尼板隔音垫，实现轻量化主动静音",
            "极大提升车内语音通话清晰度与音乐欣赏的纯净声底",
        ],
        limitations=[
            "对算法运算延迟要求达到毫秒级极限，系统调校标定极其复杂",
            "主要针对周期性或可预测中低频路噪，对突发尖锐的高频风噪消噪效果有限",
        ],
        sub_variants={
            "ENC/ANC发动机主动降噪": "针对发动机转速基波振动的主动降噪（混动车常见）",
            "RNC底盘路面主动降噪": "专克粗糙路面胎噪与底盘轰鸣的顶尖静音科技",
        },
        representative_vehicles=["理想L9/MEGA", "蔚来ET7/ES8", "极氪001", "问界M9", "凯迪拉克全系"],
        standard_labels=["主动降噪", "RNC路噪消除", "反相声波", "毫秒消噪", "图书馆级静音", "高速不耳鸣"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带客户在粗糙水泥路或减速带路面上试驾对比：‘很多车在粗糙路上开底盘会有很烦躁的嗡嗡轰鸣声，听久了脑袋疼；我们的RNC路噪主动降噪能发射反向声波把噪音抵消掉，高速巡航车里安静得像图书馆，聊天完全不用扯嗓子！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 15. 多屏联动与副驾独立娱乐互联系统
    TechnologyEntity(
        id="generic_multi_screen_interaction_passenger",
        name="多屏联动与副驾独立娱乐互联系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Multi-Screen Cross-Seat Interaction & Independent Co-Driver Entertainment",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱交互架构/多联屏系统",
        aliases=[
            "多屏联动",
            "副驾娱乐屏",
            "后排吸顶屏",
            "三联屏",
            "双联屏",
            "多屏互动",
        ],
        summary="支持主驾仪表、中控导航、副驾专属影音娱乐屏及后排大屏之间进行三指飞屏、视频无缝拖拽互传与独立双蓝牙耳机声道的多屏互联交互体系。",
        description=(
            "过去的汽车只有中间一块屏幕，副驾想看剧会分散主驾看导航视线，甚至带来严重安全隐患。"
            "多屏联动系统为副驾驶配备了专属独立娱乐触控屏，采用专用防窥贴膜光学偏光设计（主驾从侧面看过去是全黑一片，驾驶不分心）。"
            "副驾可以戴上独立蓝牙耳机看院线大片、刷抖音，也可以帮主驾查找沿途好吃的餐厅，找到后只需三个手指往左轻轻一划（三指飞屏），"
            "路线瞬间‘飞’到了中控大屏并自动开启导航；后排吸顶屏更可与前排同屏共享游戏画面，让全家旅途其乐融融。"
        ),
        technical_principles=[
            "单SoC多屏异构渲染虚拟化管线（Multiple DRM Planes Display Pipeline）",
            "百兆车载以太网流媒体跨座舱节点低延迟推流协议与副驾光学防窥偏光微结构",
        ],
        advantages=[
            "主副驾各取所需：主驾安心看路看导航，副驾沉浸式刷剧看综艺，彼此互不干扰",
            "三指飞屏操作极度丝滑：副驾查好的路线或视频一划即传，人车互动极具仪式感",
            "防窥技术杜绝夜间副驾屏幕光线反射干扰主驾右侧视线，保障行车本质安全",
        ],
        limitations=[
            "屏幕数量增多会增加内饰仪表台的线束复杂度与整体结构自重",
            "副驾在行驶中长时间近距离看动态视频，部分敏感体质乘客可能产生轻微眩晕",
        ],
        sub_variants={
            "贯穿式大联屏": "主驾、中控、副驾连为一体的超长一体式大连屏（如理想、银河）",
            "分体式独立副驾屏+后排吸顶折叠屏": "前后排独立娱乐生态，兼具尊享商务与奶爸带娃",
        },
        representative_vehicles=["理想L7/L8/L9(双15.7寸三联屏+后排屏)", "小鹏G9/X9", "问界M9(三联屏+后排投影)", "领克08", "智己LS6/LS7"],
        standard_labels=["多屏联动", "副驾娱乐屏", "三指飞屏", "防窥屏幕", "后排吸顶大屏", "家庭移动客厅"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向带爱人一起看车的客户展示副驾功能：‘副驾座椅就是太太的专属VIP影院，戴上耳机看剧追综艺，屏幕有防窥设计绝不影响您看导航；她搜到了好玩的景点，手指轻轻一滑直接甩给中控帮您带路，长途开车路上再也不无聊！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
    # 16. 多色自适应氛围灯与光瀑式律动系统
    TechnologyEntity(
        id="generic_ambient_lighting_system",
        name="多色自适应氛围灯与光瀑式律动系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Adaptive Multi-Color Dynamic Ambient Light & Waterfall Lightfall System",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱视觉与氛围/智能灯光科技",
        aliases=[
            "车载氛围灯",
            "氛围灯",
            "律动氛围灯",
            "流光氛围灯",
            "光瀑氛围灯",
            "256色氛围灯",
        ],
        summary="由数百颗独立可寻址RGB LED组成的环抱式智能光瀑灯带，不仅提供256色音乐节拍律动与流光变幻，更能与开门防撞预警、盲区变道及空调调温进行红蓝闪烁视觉联动警报。",
        description=(
            "传统氛围灯只有单色或几种简单固定颜色，亮度低且无法动态交互。"
            "新一代多色动态智能氛围灯采用点阵式数字可寻址LED灯珠与高透光匀光导光条，支持256色无级色彩调节与多色渐变呼吸光瀑。"
            "它不仅是烘托浪漫车内情调的利器（随着音乐旋律跌宕起伏追光律动），更是车内重要的主动安全警示通道："
            "开门时如果侧后方有电动车驶来，对应侧车门灯带立刻剧烈闪烁刺眼红光警告；盲区有车强行并线时灯带同步警示，调高空调温度时灯带由蓝变红，光影流转生动直观。"
        ),
        technical_principles=[
            "LIN/CAN-FD总线高速寻址微型数字LED驱动芯片，单灯珠独立PWM色彩灰度控制",
            "微棱镜双色共挤均光导光条实现无颗粒感的高漫反射均匀发光",
        ],
        advantages=[
            "情调拉满：夜间点亮整个座舱被柔和流光环抱，科技感与豪华高级感媲美百万级豪车",
            "主动安全视觉提醒：开门盲区警示、前向碰撞预警以红色光瀑直观警告，比单纯蜂鸣声更及时",
            "与空调、驾驶模式、音乐深度联动，让整个座舱具有动态呼吸般的生命感",
        ],
        limitations=[
            "极高亮度若夜间不加控制可能在侧窗玻璃形成轻微倒影，需要具备自动随环境光无级调暗算法",
            "劣质导光条长期日晒暴晒后存在轻微发黄老化的材料要求考验",
        ],
        sub_variants={
            "单色/64色静态氛围灯": "经典基础方案，仅支持简单颜色切换",
            "256色动态交互光瀑氛围灯": "数字寻址独立控制，支持音乐律动、安全红光闪烁告警与光瀑流动",
        },
        representative_vehicles=["奔驰S级/E级(主动式环境氛围灯)", "小米SU7", "极氪001/007", "问界M9", "小鹏P7+/G9", "蔚来全系"],
        standard_labels=["智能氛围灯", "256色光瀑", "音乐节拍律动", "开门红光防撞警示", "环抱式光影", "豪华座舱标配"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "在展厅调暗灯光向客户展示灯光律动与开门警示：‘放上您最爱的歌，全车流光随着节拍起伏流动，就像坐在私人奢华清吧里；下车开门如果有后车开过来，门板上的灯带会立刻爆闪红光提醒您先别推门，既浪漫又救命！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智能座舱",
    ),
]
