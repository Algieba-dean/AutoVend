"""
Data schemas and taxonomy definitions for OEM Proprietary Terminology (src/terminology/schemas.py).
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TechCategory(str, Enum):
    """Core taxonomy category for automotive proprietary technologies."""

    CHASSIS_SUSPENSION = "chassis_suspension"          # 底盘、主动悬架与车身垂直控制
    POWERTRAIN_MOTOR = "powertrain_motor"              # 电驱总成、超级电机与混动系统
    BATTERY_CHARGING = "battery_charging"              # 电池电芯、高压架构与超快充体系
    AUTONOMOUS_DRIVING = "autonomous_driving"          # 高阶智驾系统、算法大模型与自研芯片
    PLATFORM_ARCHITECTURE = "platform_architecture"    # 整车平台架构与电子电气架构 (EEA)
    COCKPIT_OS = "cockpit_os"                          # 智能座舱操作系统与交互生态
    MANUFACTURING_SAFETY = "manufacturing_safety"      # 一体化大压铸与车身安全结构


class TechMaturity(str, Enum):
    """Maturity and commercialization stage of the technology."""

    MASS_PRODUCTION = "mass_production"  # 已批量量产交付
    PRE_RESEARCH = "pre_research"        # 前瞻预研或已发布未全面交付
    CONCEPT = "concept"                  # 概念阶段


class EquivalenceDomain(str, Enum):
    """Functional domain for cross-brand equivalence mapping."""

    ACTIVE_BODY_CONTROL = "active_body_control"                      # 智能车身控制/全主动底盘悬架
    HIGH_VOLTAGE_800V_PLATFORM = "high_voltage_800v_platform"        # 800V/900V高压碳化硅快充平台
    URBAN_NOA_AUTONOMOUS_DRIVING = "urban_noa_autonomous_driving"    # 无图端到端城市高阶辅助驾驶
    INTEGRATED_BATTERY_SAFETY = "integrated_battery_safety"          # 电池车身一体化与高安全电芯结构
    MULTI_MOTOR_TORQUE_VECTORING = "multi_motor_torque_vectoring"    # 多电机独立驱动与扭矩矢量控制
    INTELLIGENT_COCKPIT_OS = "intelligent_cockpit_os"                # 原生万物互联智能座舱全域系统
    GIGACASTING_STRUCTURE = "gigacasting_structure"                  # 超大吨位一体化压铸后地板/车身
    HYBRID_POWERTRAIN_SYSTEM = "hybrid_powertrain_system"            # 智能多挡混动与电四驱系统 (DM-i/Hi4/C-DM)
    SOLID_STATE_BATTERY_TECH = "solid_state_battery_tech"            # 半固态与全固态高能量密度电池
    INTELLIGENT_CHASSIS_STEERING = "intelligent_chassis_steering"    # 数字化智慧底盘与四轮转向/线控底盘


class TechnologyEntity(BaseModel):
    """Structured knowledge representation of an OEM proprietary technology or generic technical concept."""

    id: str = Field(..., description="Unique technical identifier, e.g. 'byd_disus'")
    name: str = Field(..., description="Canonical Chinese technology name, e.g. '云辇智能车身控制系统'")
    brand: str = Field(..., description="Standard OEM brand name, or '通用技术' for generic terms")
    brand_key: str = Field(..., description="Normalized brand identifier: byd, xiaomi, hima, tesla, li_auto, zeekr, nio, xpeng, im, gac_aion, gwm, chery, porsche, mercedes, bmw, generic")
    english_name: str = Field(..., description="English commercial/technical name, e.g. 'BYD DiSus'")
    category: TechCategory = Field(..., description="Primary taxonomy category")
    subcategory: str = Field("", description="Specific domain subcategory, e.g. '主动悬架/车身控制'")
    aliases: List[str] = Field(default_factory=list, description="Common aliases, informal names, typos, and abbreviations")
    summary: str = Field(..., description="Concise customer-facing summary")
    description: str = Field(..., description="Deep engineering and technical description")
    technical_principles: List[str] = Field(default_factory=list, description="Core physical or algorithmic principles")
    advantages: List[str] = Field(default_factory=list, description="Key functional advantages")
    limitations: List[str] = Field(default_factory=list, description="Known boundary limitations or cost tradeoffs")
    sub_variants: Dict[str, str] = Field(default_factory=dict, description="Variants hierarchy, e.g. {'云辇-C': '智能阻尼', '云辇-A': '智能空气'}")
    representative_vehicles: List[str] = Field(default_factory=list, description="Vehicle models equipped with this technology")
    standard_labels: List[str] = Field(default_factory=list, description="Formal generic tech keywords for RAG search enrichment")
    equivalence_group_id: Optional[EquivalenceDomain] = Field(None, description="Cross-brand equivalence group")
    sales_talking_points: List[str] = Field(default_factory=list, description="Sales pitch tactics and positioning guidance")
    maturity: TechMaturity = Field(default=TechMaturity.MASS_PRODUCTION, description="Production readiness stage")
    is_generic: bool = Field(default=False, description="Whether this entity represents a generic automotive technical concept")
    generic_category: str = Field(default="", description="Domain classification for generic terms (悬架形式, 电池形态, 智驾与算法, 补能与电气)")


class MatchedTerm(BaseModel):
    """Detailed record of a proprietary term detected in user query or context."""

    matched_text: str
    start_idx: int
    end_idx: int
    entity: TechnologyEntity
    match_type: str = Field("exact_name", description="'exact_name', 'exact_alias', 'fuzzy_alias', 'acronym'")
    confidence: float = 1.0
    matched_alias: str = ""


class ResolutionResult(BaseModel):
    """Comprehensive disambiguation and resolution output for a terminology query."""

    query: str
    primary_entity: Optional[TechnologyEntity] = None
    all_matched_entities: List[TechnologyEntity] = Field(default_factory=list)
    category: Optional[TechCategory] = None
    confidence: float = 0.0
    disambiguation_needed: bool = False
    alternative_entities: List[TechnologyEntity] = Field(default_factory=list)
    formal_explanation: str = ""
    conversational_pitch: str = ""
    standard_labels: List[str] = Field(default_factory=list)
    suggested_query_expansions: List[str] = Field(default_factory=list)


class TechComparisonDimension(BaseModel):
    """Comparison entry for a single engineering evaluation dimension."""

    dimension_name: str
    tech_evaluations: Dict[str, str] = Field(default_factory=dict)  # brand/entity -> evaluation snippet


class TechComparisonMatrix(BaseModel):
    """Structured matrix comparing equivalent proprietary technologies across brands."""

    equivalence_domain: Optional[EquivalenceDomain] = None
    domain_chinese_name: str = ""
    target_function: str = ""
    compared_entities: List[TechnologyEntity] = Field(default_factory=list)
    dimensions: List[TechComparisonDimension] = Field(default_factory=list)
    key_differentiators: Dict[str, str] = Field(default_factory=dict)
    sales_guidance: str = ""
    summary_markdown: str = ""
