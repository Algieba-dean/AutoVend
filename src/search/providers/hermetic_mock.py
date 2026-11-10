"""
Hermetic Mock Automotive Search Provider (src/search/providers/hermetic_mock.py).

Provides deterministic, offline, high-fidelity market data for leading automakers and
models, with automatic dynamic fallback generation for any arbitrary car model query.
Guarantees 100% hermetic reproducibility in CI and test environments without network calls.
"""

import re
import time
from typing import Dict, List, Optional

from src.search.models import (
    AutomotiveNewsItem,
    DiscountPromotionData,
    MarketSearchResult,
    SalesVolumeData,
    SearchType,
)
from src.search.providers.base import BaseSearchProvider
from src.search.sanitizer import SearchSanitizer


# TOY IMPLEMENTATION: Hardcoded mock intelligence database written for deterministic CI/demos.
# Manually crafted for top Chinese & global vehicle models; not a real-time web/market crawler.
# PRODUCTION REPLACEMENT: Replace with a distributed web scraper worker pool (Scrapy / Playwright on Celery)
# integrating real automotive market feeds (e.g., Autohome, Dongchedi, CPCA sales volume APIs)
# and store in a partitioned caching database (Redis / PostgreSQL) with TTL-based freshness invalidation.
# High-fidelity automotive intelligence repository for mainstream Chinese & global vehicles
MOCK_AUTOMOTIVE_DATABASE: Dict[str, Dict[str, any]] = {
    "小米su7": {
        "car_model": "小米SU7",
        "sales": SalesVolumeData(
            car_model="小米SU7",
            latest_monthly_sales=21580,
            sales_period="2025年1月",
            total_annual_delivery=138600,
            segment_rank="20万以上中大型纯电轿车销量第一名",
            overall_rank="中国新能源中大型轿车年度榜单第一名",
            yoy_growth="+125.4%",
            mom_growth="+7.8%",
            rankings_summary="连续4个月月交付量突破2万台大关，产能持续爬坡，锁单排队周期约15-20周，交付热度行业顶尖。",
        ),
        "discount": DiscountPromotionData(
            car_model="小米SU7",
            official_guide_price_range="21.59万 - 29.99万元",
            terminal_discount="暂无现金优惠（订单火爆保价销售）",
            trade_in_subsidy="享受国家以旧换新补贴最高20,000元，部分城市追加5,000元地方补贴",
            financial_policy="年化费率低至2.5%，首付15%起，最长支持60期低息分期",
            limited_time_rights=[
                "限时赠送价值8,000元Nappa真皮座椅",
                "限时免费赠送小米智能驾驶增强功能终身使用权",
                "免费赠送7kW智能家用充电桩及30米基础安装服务",
                "首任车主整车5年或10万公里质保，三电核心部件8年或16万公里质保",
            ],
            valid_until="2025-06-30",
            summary="小米SU7目前终端供不应求无现金直降，但限时下定赠送Nappa真皮与终身智驾权益，叠加国家置换补贴后综合权益价值超3.5万元。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="小米SU7 Ultra量产版纽北赛道刷圈实测，极速超350km/h引发全球热议",
                source="汽车之家",
                publish_date="2025-02-12",
                category="实测口碑",
                summary="小米SU7 Ultra在德国纽博格林北环赛道展开深度极限调校，三电机超千匹马力与碳纤维空气动力学套件表现惊艳，赛道圈速进入6分台区间。",
                url="https://autohome.com.cn/news/202502/xiaomi_ultra.html",
            ),
            AutomotiveNewsItem(
                title="小米汽车工厂二期扩产提速，2025年交付目标剑指30万辆",
                source="懂车帝",
                publish_date="2025-02-05",
                category="行业快报",
                summary="北京经开区小米汽车智能制造基地二期工厂结构封顶，预计2025年中投产，届时SU7与全新SUV车型提车交付周期将大幅缩短至4周内。",
                url="https://dongchedi.com/article/xiaomi_capacity_2025",
            ),
        ],
    },
    "比亚迪汉": {
        "car_model": "比亚迪汉",
        "sales": SalesVolumeData(
            car_model="比亚迪汉",
            latest_monthly_sales=23200,
            sales_period="2025年1月",
            total_annual_delivery=228000,
            segment_rank="B+C级新能源轿车全品类销量冠亚军",
            overall_rank="中国B级以上轿车常年销量排名前三",
            yoy_growth="+18.2%",
            mom_growth="+3.5%",
            rankings_summary="2025款换装后五连杆悬架并升级激光雷达版后，月销量稳超2.2万台，EV纯电与DM-i插混双线开花。",
        ),
        "discount": DiscountPromotionData(
            car_model="比亚迪汉",
            official_guide_price_range="16.58万 - 23.58万元",
            terminal_discount="部分在售车系限时下定直降8,000元至12,000元现金优惠",
            trade_in_subsidy="比亚迪官方置换补贴本品最高8,000元/他品最高6,000元，叠加国家报废置换补贴最高20,000元",
            financial_policy="首付低至15%，支持0首付起，最高享24期0息金融贴息",
            limited_time_rights=[
                "首任非营运车主三电系统终身保修（免工时与配件费）",
                "终身免费OTA系统升级及2年免费车机车联网流量（5GB/月）",
                "免费赠送原厂随车充电枪及家用充电桩安装权益",
            ],
            valid_until="2025-05-31",
            summary="2025款比亚迪汉性价比拉满，终端优惠加置换补贴累计可省近3万元，是20万内中大型混动与纯电标杆选型。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="2025款比亚迪汉全面上市：标配后五连杆独立悬架，高配搭载激光雷达与云辇-C",
                source="懂车帝",
                publish_date="2025-01-20",
                category="改款上市",
                summary="新款汉EV/DM-i补齐底盘最后一块短板，全系告别三连杆升级五连杆，驾驶质感显著跃升，智驾版高阶NOA支持全国城市导航。",
                url="https://dongchedi.com/article/byd_han_2025",
            ),
        ],
    },
    "问界m9": {
        "car_model": "问界M9",
        "sales": SalesVolumeData(
            car_model="问界M9",
            latest_monthly_sales=16800,
            sales_period="2025年1月",
            total_annual_delivery=152000,
            segment_rank="50万以上豪华大型SUV全品类销量冠军（超越宝马X5、奔驰GLE）",
            overall_rank="中国豪华汽车市场现象级爆款第一名",
            yoy_growth="+180.2%",
            mom_growth="+5.1%",
            rankings_summary="连续10个月蝉联中国50万以上豪车销量榜首，增程与纯电双版本累计大定突破18万辆，豪车格局彻底被重塑。",
        ),
        "discount": DiscountPromotionData(
            car_model="问界M9",
            official_guide_price_range="46.98万 - 56.98万元",
            terminal_discount="享价值30,000元鸿蒙智行购车权益礼包，现金降幅微小",
            trade_in_subsidy="华为鸿蒙智行置换补贴10,000元，叠加国家置换补贴最高20,000元",
            financial_policy="年化费率2.49%，首付两成起，可享华为专属金融低息贷款",
            limited_time_rights=[
                "免费赠送价值20,000元华为乾崑ADS 3.0高阶智驾全功能包",
                "价值10,000元外观内饰豪华选配金（支持选装双拼车色或星空顶棚）",
                "赠送原装21英寸多辐运动轮毂及电动脚踏板",
                "首任车主终身免费基础流量及三电质保",
            ],
            valid_until="2025-06-30",
            summary="问界M9无大幅直接降价，但附赠的华为ADS 3.0高阶智驾包（原价2万）与选配基金极具含金量，折合综合权益超4万元。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="问界M9玄武车身双卡车前后夹击真实事故测试：乘员舱完好车门轻松打开",
                source="太平洋汽车",
                publish_date="2025-02-10",
                category="实测口碑",
                summary="中保研与多家权威媒体重测证实，问界M9玄武车身2000MPa热成型钢闭环结构在极端追尾工况下展现出惊人的防护能力，乘员生存空间完好。",
                url="https://pcauto.com.cn/news/aito_m9_safety.html",
            ),
        ],
    },
    "理想l6": {
        "car_model": "理想L6",
        "sales": SalesVolumeData(
            car_model="理想L6",
            latest_monthly_sales=26400,
            sales_period="2025年1月",
            total_annual_delivery=195000,
            segment_rank="25万级家庭中大型增程SUV销量第一名",
            overall_rank="造车新势力单一车型月销量冠军",
            yoy_growth="+210.0%",
            mom_growth="+4.2%",
            rankings_summary="理想汽车旗下最畅销车型，稳居月销2.5万辆俱乐部，凭借大五座、全系标配四驱与豪华配置成为奶爸家庭首选。",
        ),
        "discount": DiscountPromotionData(
            car_model="理想L6",
            official_guide_price_range="24.98万 - 27.98万元",
            terminal_discount="限时定单立减10,000元现金直降",
            trade_in_subsidy="理想官方置换补贴5,000元，叠加国家置换补贴最高20,000元",
            financial_policy="首付5万元起，3年0息贴息方案，或5年超低月供",
            limited_time_rights=[
                "价值5,000元特殊车漆选装基金（如小象灰、绿色特别版）",
                "免费赠送7kW家用充电桩及安装服务",
                "首任车主终身质保升级包优惠购",
            ],
            valid_until="2025-05-31",
            summary="理想L6终端现金优惠1万元，配合3年免息与置换补贴，23万多即可全款提双电机四驱大五座中大型SUV，性价比极高。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="理想OTA 6.5版本全量推送：端到端+VLM双系统上车，车位到车位智驾体验倍增",
                source="汽车之家",
                publish_date="2025-01-28",
                category="行业快报",
                summary="理想L系列全面升级端到端架构，复杂环岛通行与无保护左转果断拟人，城市代驾与自动泊车成功率大幅提升。",
                url="https://autohome.com.cn/news/lixiang_ota_65.html",
            ),
        ],
    },
    "极氪001": {
        "car_model": "极氪001",
        "sales": SalesVolumeData(
            car_model="极氪001",
            latest_monthly_sales=12800,
            sales_period="2025年1月",
            total_annual_delivery=112000,
            segment_rank="纯电豪华猎装轿跑销量冠军（市占率超80%）",
            overall_rank="25-35万级纯电豪华车销量排名前列",
            yoy_growth="+45.0%",
            mom_growth="+2.1%",
            rankings_summary="全新极氪001凭借全系全栈800V、激光雷达标配及双腔空悬升级，在猎装轿跑细分市场保持绝对统治地位。",
        ),
        "discount": DiscountPromotionData(
            car_model="极氪001",
            official_guide_price_range="25.90万 - 32.90万元",
            terminal_discount="限时购车权益直减现金10,000元至15,000元",
            trade_in_subsidy="极氪官方老车主置换立减10,000元，国家补贴最高20,000元",
            financial_policy="年化利率1.99%超低息金融贷款，支持超长60期分期",
            limited_time_rights=[
                "免费升级价值20,000元双腔空气悬架系统套装",
                "免费升级价值6,000元21英寸多辐运动轮毂",
                "赠送ZAD全场景智能驾驶辅助系统终身免费使用权",
                "首任车主终身免费充电权益与三电终身质保",
            ],
            valid_until="2025-06-30",
            summary="极氪001当前促销力度极大，不仅直接降价还免费赠送双腔空悬与21寸轮毂，综合优惠价值超4.5万元。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="全新极氪001极寒冬测表现出色：800V神行电池-20℃快充仅需20分钟",
                source="易车网",
                publish_date="2025-01-15",
                category="实测口碑",
                summary="在牙克石零下25度严寒实测中，极氪001热管理系统与全栈800V架构低温续航达成率突破65%，双电机冰雪漂移姿态极其稳健。",
                url="https://yiche.com/news/zeekr001_winter_test.html",
            ),
        ],
    },
    "特斯拉modely": {
        "car_model": "特斯拉Model Y",
        "sales": SalesVolumeData(
            car_model="特斯拉Model Y",
            latest_monthly_sales=38500,
            sales_period="2025年1月",
            total_annual_delivery=456000,
            segment_rank="中国及全球乘用车单车型销量绝对冠军",
            overall_rank="2024-2025全品类乘用车销量榜榜首",
            yoy_growth="+12.0%",
            mom_growth="-3.2%",
            rankings_summary="中国乘用车市场无可匹敌的单车销量霸主，无论燃油还是新能源全品类销量第一，单月销量长期突破3.5万至4万台。",
        ),
        "discount": DiscountPromotionData(
            car_model="特斯拉Model Y",
            official_guide_price_range="24.99万 - 35.49万元",
            terminal_discount="限时5年0息金融方案（折合变相优惠超25,000元息费）",
            trade_in_subsidy="享受特斯拉官方以旧换新置换礼包，国家补贴最高20,000元",
            financial_policy="全系支持首付7.99万元享5年0息贷款，月供低至2,833元",
            limited_time_rights=[
                "限时特选车漆（星空灰免费、冷光银等立减）",
                "90天增强版自动辅助驾驶（EAP）免费试用体验",
                "车主引荐积分可兑换超充额度与车载配件",
            ],
            valid_until="2025-05-31",
            summary="特斯拉Model Y主打‘5年0息’金融杀手锏，相当于直接省下2万多元利息，大幅降低购车月供压力。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="特斯拉FSD入华进展提速：中国车主即将推送端到端V12监督版实测",
                source="懂车帝",
                publish_date="2025-02-14",
                category="行业快报",
                summary="特斯拉中国数据中心算力扩容完毕，最新国内测试车在上海路况展现出强大的纯视觉端到端规控能力，预计上半年开启全面推送。",
                url="https://dongchedi.com/article/tesla_fsd_china_2025",
            ),
        ],
    },
    "蔚来es6": {
        "car_model": "蔚来ES6",
        "sales": SalesVolumeData(
            car_model="蔚来ES6",
            latest_monthly_sales=8900,
            sales_period="2025年1月",
            total_annual_delivery=88000,
            segment_rank="30万以上高端纯电SUV销量领跑者",
            overall_rank="蔚来汽车主力交付支柱车型（占比超45%）",
            yoy_growth="+22.5%",
            mom_growth="+4.8%",
            rankings_summary="蔚来品牌最畅销的走量SUV，双电机四驱标配与BaaS租电模式助力其在30万级豪华纯电市场稳定输出。",
        ),
        "discount": DiscountPromotionData(
            car_model="蔚来ES6",
            official_guide_price_range="33.80万 - 39.60万元（整车买断） / 26.80万元起（BaaS电池租用）",
            terminal_discount="展车限时下定直减15,000元至20,000元",
            trade_in_subsidy="蔚来置换补贴10,000元选装基金，国家置换补贴最高20,000元",
            financial_policy="BaaS方案首付低至15%，享2年免息或5年超低利率",
            limited_time_rights=[
                "BaaS电池租用‘付4送1’（租电账单每满4个月减免1个月）",
                "免费赠送价值10,000元NOMI Mate 2.0及舒享套装",
                "赠送60张免费全自动换电券（价值超6,000元）",
                "终身免费质保及道路救援",
            ],
            valid_until="2025-06-30",
            summary="选择BaaS车电分离方案裸车价仅需26.8万，叠加置换补贴和免费换电券，综合购车门槛和用车成本大幅降低。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="蔚来第四代换电站全国布局突破800座：3分钟全自动极速换电体验无敌",
                source="汽车之家",
                publish_date="2025-02-01",
                category="实测口碑",
                summary="四代换电站配备4颗激光雷达与英伟达Orin芯片，支持车辆离车自动泊入换电，单次换电耗时仅2分24秒，长途返乡服务区排队效率翻倍。",
                url="https://autohome.com.cn/news/nio_power_swap_gen4.html",
            ),
        ],
    },
    "智己l6": {
        "car_model": "智己L6",
        "sales": SalesVolumeData(
            car_model="智己L6",
            latest_monthly_sales=6800,
            sales_period="2025年1月",
            total_annual_delivery=52000,
            segment_rank="20万级中大型纯电轿车前五名",
            overall_rank="上汽集团高端新能源支柱车型",
            yoy_growth="+88.5%",
            mom_growth="+6.2%",
            rankings_summary="全系标配灵蜥数字底盘与后轮转向，凭借蟹行泊车与准900V高压平台，订单稳步攀升。",
        ),
        "discount": DiscountPromotionData(
            car_model="智己L6",
            official_guide_price_range="21.99万 - 34.59万元",
            terminal_discount="限时特惠定金2,000元抵扣17,000元购车尾款（直降1.5万元）",
            trade_in_subsidy="上汽本品置换补贴10,000元，国家以旧换新补贴最高20,000元",
            financial_policy="0首付起，最高享3年0息金融贴息或5年低月供",
            limited_time_rights=[
                "限时免费升级价值22,000元IM AD高阶智驾全功能包终身免费使用权",
                "免费升级四轮转向系统与超长续航三元锂/半固态电池选装优惠",
                "赠送7kW家充桩及基础安装服务",
            ],
            valid_until="2025-06-30",
            summary="智己L6终端现金直降1.5万元并赠送终身高阶智驾，全系标配后轮转向性价比突出。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="智己L6灵蜥数字底盘深度体验：蟹行模式侧方位一步入库震惊车主",
                source="汽车之家",
                publish_date="2025-01-25",
                category="实测口碑",
                summary="灵蜥数字底盘将后轮转向、CDC电控阻尼减振器与电驱闭环联合控制，转弯半径仅4.99米，狭窄老小区倒车调头灵活如紧凑微型车。",
                url="https://autohome.com.cn/news/im_l6_lizard_review.html",
            ),
        ],
    },
    "广汽埃安aions": {
        "car_model": "广汽埃安AION S",
        "sales": SalesVolumeData(
            car_model="广汽埃安AION S",
            latest_monthly_sales=18500,
            sales_period="2025年1月",
            total_annual_delivery=198000,
            segment_rank="10-15万级纯电A级轿车常年销量排名前三",
            overall_rank="中国新能源乘用车销量常青树",
            yoy_growth="+12.0%",
            mom_growth="+1.8%",
            rankings_summary="家用车与出行市场双轮驱动，搭载弹匣电池2.0系统，拥有超百万台无自燃优秀安全口碑。",
        ),
        "discount": DiscountPromotionData(
            car_model="广汽埃安AION S",
            official_guide_price_range="13.98万 - 17.98万元",
            terminal_discount="全系限时享最高18,000元现金直降",
            trade_in_subsidy="埃安品牌置换补贴最高8,000元，叠加国家置换补贴最高20,000元",
            financial_policy="3年10万0息贷款，首付低至0元起",
            limited_time_rights=[
                "弹匣电池首任私家车主终身三电免费质保",
                "赠送全套原厂充电桩及免费安装",
                "终身免费车联网基础流量",
            ],
            valid_until="2025-05-31",
            summary="AION S直降近2万，叠加置换后裸车门槛下探至10万内，弹匣电池安全可靠、大空间高续航，性价比卓越。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="广汽埃安弹匣电池2.0通过枪击与整包热失控严苛测试：零起火零蔓延",
                source="懂车帝",
                publish_date="2025-02-08",
                category="实测口碑",
                summary="埃安弹匣电池2.0采用超稳电芯纳米涂层与速冷消防系统，在极限电芯起火测试中实现整包不起火，安全防护达行业顶尖水平。",
                url="https://dongchedi.com/article/aion_magazine_battery_test",
            ),
        ],
    },
    "坦克400": {
        "car_model": "坦克400 Hi4-T",
        "sales": SalesVolumeData(
            car_model="坦克400 Hi4-T",
            latest_monthly_sales=5200,
            sales_period="2025年1月",
            total_annual_delivery=48000,
            segment_rank="中大型硬派越野新能源插混销量冠亚军",
            overall_rank="中国机甲风硬派SUV标杆车型",
            yoy_growth="+55.0%",
            mom_growth="+3.5%",
            rankings_summary="凭借Hi4-T机械纵置四驱+三把锁硬核配置与机甲硬派造型，在硬派越野圈层具备极高认可度。",
        ),
        "discount": DiscountPromotionData(
            car_model="坦克400 Hi4-T",
            official_guide_price_range="28.58万 - 28.98万元",
            terminal_discount="享限时6,000元定金抵扣12,000元（现金直减6,000元）",
            trade_in_subsidy="长城车主置换补贴最高10,000元，他品置换7,000元，国家补贴最高20,000元",
            financial_policy="首付20%起，提供最长5年低息分期金融方案",
            limited_time_rights=[
                "首任非营运车主发动机/变速器/三电核心部件终身质保",
                "赠送便携充电枪与7kW家用智能充电桩",
                "5年免费娱乐流量与基础道路救援保障",
            ],
            valid_until="2025-06-30",
            summary="坦克400 Hi4-T综合优惠超2万元，既能市区纯电通勤又能长途重度越野穿越，无里程焦虑。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="长城Hi4-T硬核越野实测：沙漠冲坡与连续攀爬电池不馈电不失速",
                source="汽车之家",
                publish_date="2025-01-18",
                category="实测口碑",
                summary="Hi4-T采用纵置并联P2混动架构，发动机始终保留直接动力输出，杜绝了解耦电四驱长时间高负荷过热保护与打滑失控风险。",
                url="https://autohome.com.cn/news/gwm_hi4t_desert_test.html",
            ),
        ],
    },
    "奇瑞风云t9": {
        "car_model": "奇瑞风云T9",
        "sales": SalesVolumeData(
            car_model="奇瑞风云T9",
            latest_monthly_sales=8600,
            sales_period="2025年1月",
            total_annual_delivery=72000,
            segment_rank="15万级中型插混SUV热销榜前四",
            overall_rank="奇瑞新能源风云序列销量担当",
            yoy_growth="+130.0%",
            mom_growth="+5.0%",
            rankings_summary="搭载鲲鹏超能混动C-DM系统，凭借高热效率发动机与超长综合续航，迅速在家用中型SUV市场站稳脚跟。",
        ),
        "discount": DiscountPromotionData(
            car_model="奇瑞风云T9",
            official_guide_price_range="12.99万 - 16.99万元",
            terminal_discount="限时下定享受10,000元现金直降",
            trade_in_subsidy="奇瑞官方置换补贴至高10,000元，叠加国家置换补贴至高20,000元",
            financial_policy="0首付或至高24期0息金融贴息方案",
            limited_time_rights=[
                "整车及三电系统终身免费质保（首任非营运车主）",
                "免费赠送家用充电桩及基础安装",
                "终身免费道路救援及基础流量",
            ],
            valid_until="2025-05-31",
            summary="风云T9直降后起售价仅11.99万，大七座可选，综合续航超1400km，是家庭刚需超高性价比首选。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="奇瑞鲲鹏超能混动C-DM实测油耗低至3.8L：热效率44.5%表现惊艳",
                source="懂车帝",
                publish_date="2025-02-03",
                category="实测口碑",
                summary="风云T9搭载第五代ACTECO 1.5TGDI高效混动专用发动机，在跨省长途续航实测中跑出1480公里极限成绩，亏电油耗极具竞争力。",
                url="https://dongchedi.com/article/chery_cdm_t9_test",
            ),
        ],
    },
    "尊界s800": {
        "car_model": "尊界S800",
        "sales": SalesVolumeData(
            car_model="尊界S800",
            latest_monthly_sales=1200,
            sales_period="2025年1月",
            total_annual_delivery=4500,
            segment_rank="百万级超豪华行政轿车中国品牌第一名",
            overall_rank="华为鸿蒙智行顶奢旗舰",
            yoy_growth="+260.0%",
            mom_growth="+15.0%",
            rankings_summary="中国百万级超豪华轿车划时代力作，5.48米恢弘车长，大定锁单超预期，对标迈巴赫S级与保时捷帕拉梅拉。",
        ),
        "discount": DiscountPromotionData(
            car_model="尊界S800",
            official_guide_price_range="100.00万 - 150.00万元",
            terminal_discount="超豪华旗舰保价销售，无直接现金优惠",
            trade_in_subsidy="鸿蒙智行专属超豪置换礼遇20,000元，国家补贴最高20,000元",
            financial_policy="尊享华为白金私人订制金融方案，首付30%起",
            limited_time_rights=[
                "终身尊享国宾级管家服务与免费接送机礼遇",
                "免费升级全车星空顶棚与定制专属徽标",
                "华为全栈顶级软硬件生态终身免费升级（乾崑智驾旗舰版+鸿蒙座舱）",
            ],
            valid_until="2025-12-31",
            summary="尊界S800定位中国顶奢旗舰，搭载途灵龙行底盘与玄武安全车身，尊享国宾级专属出行礼遇。",
        ),
        "news": [
            AutomotiveNewsItem(
                title="尊界S800途灵龙行底盘实测：全轮转向与主动防倾带来如履平地顶级平稳",
                source="汽车之家",
                publish_date="2025-02-15",
                category="实测口碑",
                summary="5.48米旗舰D级车转弯半径低至5.5米，四轮主动液压控制在连续S弯道中车内酒杯红酒滴水不洒，极致诠释国宾行政豪华。",
                url="https://autohome.com.cn/news/maextro_s800_roadtest.html",
            ),
        ],
    },
}


class HermeticMockSearchProvider(BaseSearchProvider):
    """Hermetic deterministic search provider satisfying all test and offline queries."""

    def __init__(self):
        self.db = MOCK_AUTOMOTIVE_DATABASE

    def _normalize_car_key(self, text: str) -> str:
        """Normalize vehicle name query for dictionary matching."""
        if not text:
            return ""
        lowered = text.lower().replace(" ", "").replace("-", "").replace("_", "")
        # Remove common auxiliary keywords
        lowered = lowered.replace("多少钱", "").replace("销量", "").replace("优惠", "").replace("新闻", "")
        lowered = lowered.replace("降价", "").replace("补贴", "").replace("口碑", "").replace("价格", "")
        return lowered

    def _find_exact_or_prefix_entry(self, clean_query: str, car_model: Optional[str] = None):
        """Locate closest matched car model in database."""
        target_keys = []
        if car_model:
            norm_m = self._normalize_car_key(car_model)
            if len(norm_m) >= 2:
                target_keys.append(norm_m)
        if clean_query:
            norm_q = self._normalize_car_key(clean_query)
            if len(norm_q) >= 2:
                target_keys.append(norm_q)

        if not target_keys:
            return None

        # 1. Exact match in DB keys
        for key in target_keys:
            if key in self.db:
                return self.db[key]

        # 2. Key contains db_key (query mentions model, e.g. "我想问小米su7怎么样")
        for key in target_keys:
            for db_key, data in self.db.items():
                if db_key in key:
                    return data

        # 3. db_key contains key only when key is specific (>= 3 chars)
        for key in target_keys:
            if len(key) >= 3:
                for db_key, data in self.db.items():
                    if key in db_key:
                        return data

        # 4. Check vehicle display name substrings
        for key in target_keys:
            for db_key, data in self.db.items():
                model_name = data["car_model"].lower().replace(" ", "")
                if model_name in key or (len(key) >= 3 and key in model_name):
                    return data
        return None

    def _synthesize_fallback_entry(self, car_name: str) -> Dict[str, any]:
        """Synthesize realistic, formatted automotive market intelligence for unlisted models."""
        display_name = car_name.strip() if car_name else "目标车型"
        return {
            "car_model": display_name,
            "sales": SalesVolumeData(
                car_model=display_name,
                latest_monthly_sales=8200,
                sales_period="2025年1月",
                total_annual_delivery=65000,
                segment_rank="同级别新能源细分市场销量排名前五",
                overall_rank="细分乘用车市场主流畅销阵营",
                yoy_growth="+24.5%",
                mom_growth="+4.1%",
                rankings_summary=f"{display_name}近期市场关注度与成交量保持稳健增长，全国各大销售门店客流充沛，处于主流热销梯队。",
            ),
            "discount": DiscountPromotionData(
                car_model=display_name,
                official_guide_price_range="价格请以当地官方经销门店公布为准",
                terminal_discount="终端可享限时定金抵扣或8,000至15,000元综合权益优惠",
                trade_in_subsidy="支持国家以旧换新置换补贴最高20,000元，品牌专项置换补贴最高8,000元",
                financial_policy="提供首付15%起、2-3年免息或5年超低费率金融分期贷款方案",
                limited_time_rights=[
                    "限时赠送原厂精品配件礼包或充电桩安装权益",
                    "首任车主享有核心零部件长效原厂质保与免费道路救援",
                    "基础车机车联网流量终身免费",
                ],
                valid_until="2025-06-30",
                summary=f"{display_name}目前综合优惠政策包含金融低息补贴、限时选装权益及国家以旧换新补贴，进店试驾下定综合权益价值显著。",
            ),
            "news": [
                AutomotiveNewsItem(
                    title=f"{display_name}最新改款动态与行业评测口碑全面出炉",
                    source="懂车帝",
                    publish_date="2025-02-10",
                    category="实测口碑",
                    summary=f"多方专业媒体针对{display_name}的续航达成率、智能化车机及底盘动态滤震展开深度长测，整体综合口碑评价优良，家庭实用属性获广泛认可。",
                    url="https://dongchedi.com/auto_review/latest.html",
                ),
            ],
        }

    def search(
        self,
        query: str,
        search_type: SearchType = SearchType.ALL,
        car_model: Optional[str] = None,
    ) -> MarketSearchResult:
        """Deterministic search execution."""
        sanitized_query = SearchSanitizer.sanitize_query(query)
        entry = self._find_exact_or_prefix_entry(sanitized_query, car_model)

        if not entry:
            fallback_name = car_model
            if not fallback_name and sanitized_query:
                cleaned_subject = re.sub(
                    r"(我想了解|我想看|查一下|请问|帮我查|最近|最新|销量|排行榜|优惠|降价|行情|新闻|实测|口碑|补贴|权益|多少钱|怎么样|有哪些|好不好|对比|推荐|车型|汽车)",
                    "",
                    sanitized_query,
                ).strip()
                if 2 <= len(cleaned_subject) <= 25 and not any(w in cleaned_subject for w in ["?", "？", "怎么", "什么"]):
                    fallback_name = cleaned_subject
                else:
                    fallback_name = "主流热销车型"
            fallback_name = fallback_name or "主流热销车型"
            entry = self._synthesize_fallback_entry(fallback_name)

        model_name = entry["car_model"]
        sales_data = entry["sales"] if search_type in (SearchType.SALES_VOLUME, SearchType.ALL) else None
        discount_data = entry["discount"] if search_type in (SearchType.DISCOUNTS_PROMOTIONS, SearchType.ALL) else None
        news_items = entry["news"] if search_type in (SearchType.NEWS_REVIEWS, SearchType.ALL) else []

        # Build clean conversational briefing
        briefing_parts = [f"### 🚗 【{model_name}】实时市场行情情报速递\n"]
        if sales_data:
            briefing_parts.append(
                f"**📊 销量与交付排名**：\n"
                f"- 最新月销量：约 **{sales_data.latest_monthly_sales:,}** 台（{sales_data.sales_period}）\n"
                f"- 榜单地位：{sales_data.segment_rank}\n"
                f"- 市场动向：{sales_data.rankings_summary}\n"
            )
        if discount_data:
            briefing_parts.append(
                f"**💰 终端优惠与购车权益**：\n"
                f"- 官方指导价：{discount_data.official_guide_price_range}\n"
                f"- 现金优惠：{discount_data.terminal_discount}\n"
                f"- 置换补贴：{discount_data.trade_in_subsidy}\n"
                f"- 金融政策：{discount_data.financial_policy}\n"
                f"- 限时权益：{'；'.join(discount_data.limited_time_rights[:3])}\n"
                f"- 综合点评：{discount_data.summary}\n"
            )
        if news_items:
            briefing_parts.append(f"**📰 最新热点与媒体实测口碑**：\n")
            for item in news_items[:2]:
                briefing_parts.append(
                    f"- **{item.title}**（来源：{item.source} | {item.publish_date}）：{item.summary}\n"
                )

        summary_markdown = "\n".join(briefing_parts)

        return MarketSearchResult(
            query=sanitized_query,
            car_model=model_name,
            search_type=search_type,
            sales_volume=sales_data,
            discount_promotion=discount_data,
            news_reviews=news_items,
            provider="hermetic_mock",
            sanitized=True,
            retrieved_at=time.time(),
            summary_markdown=summary_markdown,
        )
