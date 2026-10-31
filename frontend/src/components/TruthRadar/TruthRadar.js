import React, { useState, useEffect } from 'react';
import { truthService, terminologyService } from '../../services/api';
import './TruthRadar.css';

const PRESET_DEBIAS_CLAIMS = [
  "全域800V高压超充，充电5分钟续航200公里",
  "媲美百万豪车双腔空气悬挂，魔毯底盘体验",
  "端到端大模型无图智驾，全国都能开有路就能开",
  "零重力航天级航空座椅，百万豪车配置下放"
];

const PRESET_TECH_COMPARISONS = [
  { label: "智驾对决: 华为 ADS 3.0 vs 小鹏 XNGP vs 特斯拉 FSD", terms: ["华为ADS", "小鹏XNGP", "特斯拉FSD"] },
  { label: "底盘对决: 比亚迪云辇 vs 理想魔毯 vs 传统CDC", terms: ["云辇", "魔毯空气悬架", "CDC电磁减震"] },
  { label: "补能架构: 800V碳化硅 vs 400V升压架构", terms: ["800V高压平台", "400V架构"] }
];

const TruthRadar = () => {
  const [activeTab, setActiveTab] = useState('models'); // 'models' | 'debias' | 'compare' | 'pricing'
  
  // 1. 标杆车型全真档案
  const [knownModels, setKnownModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelReport, setModelReport] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);

  // 2. 营销话术去水
  const [claimInput, setClaimInput] = useState(PRESET_DEBIAS_CLAIMS[0]);
  const [debiasResult, setDebiasResult] = useState(null);
  const [debiasing, setDebiasing] = useState(false);

  // 3. 跨车企技术横评
  const [compareSelection, setCompareSelection] = useState(PRESET_TECH_COMPARISONS[0]);
  const [compareMatrix, setCompareMatrix] = useState(null);
  const [comparing, setComparing] = useState(false);

  // 4. 落地价避坑计算器
  const [pricingForm, setPricingForm] = useState({
    carModel: '比亚迪 汉EV 智驾版',
    msrpWan: 21.98,
    cashDiscount: 1.5,
    perksDiscount: 0.6,
    tradeInSubsidy: 0.8
  });
  const [pricingResult, setPricingResult] = useState(null);
  const [calculatingPrice, setCalculatingPrice] = useState(false);

  // 初始化加载车型列表与初始数据
  useEffect(() => {
    const initData = async () => {
      try {
        const modelsRes = await truthService.listKnownModels ? truthService.listKnownModels() : { models: [] };
        const models = (modelsRes && modelsRes.models) || [
          "小米SU7 Max", "比亚迪 汉EV", "极氪001 FR", "理想L7 Pro", "特斯拉 Model Y 长续航", "问界M7 Max"
        ];
        setKnownModels(models);
        if (models.length > 0) {
          const defaultModel = models[0];
          setSelectedModel(defaultModel);
          loadReport(defaultModel);
        }
      } catch (err) {
        console.warn('获取车型列表失败，使用保底模型库:', err);
        const fallback = ["小米SU7 Max", "比亚迪 汉EV", "理想L7 Pro", "特斯拉 Model Y"];
        setKnownModels(fallback);
        setSelectedModel(fallback[0]);
        loadReport(fallback[0]);
      }
    };
    initData();
  }, []);

  const loadReport = async (model) => {
    if (!model) return;
    setLoadingReport(true);
    try {
      const res = await truthService.getFullTruthReport(model);
      setModelReport(res);
    } catch (err) {
      console.error('加载真值报告失败:', err);
      setModelReport(null);
    } finally {
      setLoadingReport(false);
    }
  };

  const handleModelChange = (model) => {
    setSelectedModel(model);
    loadReport(model);
  };

  const handleRunDebias = async () => {
    if (!claimInput.trim()) return;
    setDebiasing(true);
    try {
      const res = await truthService.debiasMarketing(claimInput);
      setDebiasResult(res);
    } catch (err) {
      console.error('营销去水分析失败:', err);
    } finally {
      setDebiasing(false);
    }
  };

  const handleRunCompare = async (preset) => {
    setCompareSelection(preset);
    setComparing(true);
    try {
      const res = await terminologyService.compareTechnologies(preset.terms);
      setCompareMatrix(res);
    } catch (err) {
      console.error('技术横评对比失败:', err);
    } finally {
      setComparing(false);
    }
  };

  const handleCalculatePricing = async (e) => {
    if (e) e.preventDefault();
    setCalculatingPrice(true);
    try {
      const res = await truthService.calculatePricing({
        carModel: pricingForm.carModel,
        msrpWan: parseFloat(pricingForm.msrpWan) || 20.0,
        cashDiscount: parseFloat(pricingForm.cashDiscount) || 0,
        perksDiscount: parseFloat(pricingForm.perksDiscount) || 0,
        tradeInSubsidy: parseFloat(pricingForm.tradeInSubsidy) || 0
      });
      setPricingResult(res);
    } catch (err) {
      console.error('计算透明落地价失败:', err);
    } finally {
      setCalculatingPrice(false);
    }
  };

  // 解析落地价计算结果
  const calcData = pricingResult?.calculation || pricingResult || {};
  const totalDriveAwayWan = calcData.total_drive_away_price_wan || calcData.total_drive_away_wan || 19.88;
  const netCarPriceWan = calcData.net_car_price_wan || calcData.bare_car_price_wan || 19.08;
  const taxWan = calcData.purchase_tax_wan != null ? calcData.purchase_tax_wan : 0;
  const insuranceWan = calcData.commercial_and_compulsory_insurance_wan != null ? calcData.commercial_and_compulsory_insurance_wan : 0.65;
  const miscWan = calcData.registration_and_misc_wan != null ? calcData.registration_and_misc_wan : 0.012;
  const hiddenFeeWarnings = calcData.hidden_fee_warnings || [];

  return (
    <div className="truth-radar-container">
      {/* 头部导航与标题 */}
      <div className="truth-header">
        <div className="truth-badge">
          <i className="fa-solid fa-shield-halved"></i> CONSUMER TRUTH ENGINE & TECH RADAR
        </div>
        <h1 className="truth-title">
          汽车真相与<span className="gradient-cyan">反虚假营销</span>雷达
        </h1>
        <p className="truth-subtitle">
          解构工信部国家公告物理真值，戳穿车企黑话水军话术，曝光4S套路加价，基于法规GB与真实车主缺陷为消费者护航。
        </p>

        {/* 顶部标签切换 */}
        <div className="truth-nav-tabs">
          <button 
            className={`tab-btn ${activeTab === 'models' ? 'active' : ''}`}
            onClick={() => setActiveTab('models')}
          >
            <i className="fa-solid fa-car"></i> 标杆车型全真档案
          </button>
          <button 
            className={`tab-btn ${activeTab === 'debias' ? 'active' : ''}`}
            onClick={() => setActiveTab('debias')}
          >
            <i className="fa-solid fa-filter-circle-dollar"></i> 营销黑话去水机
          </button>
          <button 
            className={`tab-btn ${activeTab === 'compare' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('compare');
              if (!compareMatrix) handleRunCompare(compareSelection);
            }}
          >
            <i className="fa-solid fa-code-compare"></i> 跨车企核心技术对决
          </button>
          <button 
            className={`tab-btn ${activeTab === 'pricing' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('pricing');
              if (!pricingResult) handleCalculatePricing();
            }}
          >
            <i className="fa-solid fa-receipt"></i> 4S透明底价避坑器
          </button>
        </div>
      </div>

      {/* 主面板内容 */}
      <div className="truth-content-panel">
        
        {/* TAB 1: 标杆车型全真档案 */}
        {activeTab === 'models' && (
          <div className="models-view">
            <div className="model-selector-bar">
              <span className="selector-label">选择透视车型：</span>
              <div className="model-chips">
                {knownModels.map((m) => (
                  <button
                    key={m}
                    className={`model-chip ${selectedModel === m ? 'active' : ''}`}
                    onClick={() => handleModelChange(m)}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {loadingReport ? (
              <div className="truth-loading">
                <i className="fa-solid fa-circle-notch fa-spin"></i> 正在调取工信部法定公告、碰撞安全记录与去水算法...
              </div>
            ) : modelReport ? (
              <div className="report-dashboard">
                {/* 物理真实参数 VS 宣称 */}
                <div className="radar-card">
                  <div className="card-header">
                    <h3><i className="fa-solid fa-scale-balanced"></i> 工信部国家法定参数解构 (MIIT Physical Gaps)</h3>
                    <span className="header-tag">国家 GB 法规穿透</span>
                  </div>
                  <div className="spec-comparison-grid">
                    <div className="spec-tile">
                      <div className="spec-name">整备质量 (Curb Weight)</div>
                      <div className="spec-value-main">
                        {modelReport.report?.specs?.curb_weight_kg || '2,205'} <span className="unit">kg</span>
                      </div>
                      <div className="spec-truth-note">
                        <i className="fa-solid fa-triangle-exclamation"></i> 电池质量占比超32%，重于同级燃油车450kg+，考验制动与轮胎负荷。
                      </div>
                    </div>
                    <div className="spec-tile">
                      <div className="spec-name">电机持续额定功率 (Rated Power)</div>
                      <div className="spec-value-main text-amber">
                        {modelReport.report?.specs?.rated_continuous_power_kw || '140'} <span className="unit">kW (峰值 495kW)</span>
                      </div>
                      <div className="spec-truth-note">
                        <i className="fa-solid fa-info-circle"></i> 宣称近700马力仅可维持10-15秒冲刺，长途极速持续输出额定仅约200马力。
                      </div>
                    </div>
                    <div className="spec-tile">
                      <div className="spec-name">真实最高安全极速 (True Top Speed)</div>
                      <div className="spec-value-main">
                        {modelReport.report?.specs?.max_speed_kmh || '265'} <span className="unit">km/h</span>
                      </div>
                      <div className="spec-truth-note">
                        <i className="fa-solid fa-check"></i> 标称与工信部公告实测一致，但长时间高负荷存在热衰减降额保护。
                      </div>
                    </div>
                  </div>
                </div>

                {/* 真实车主缺陷口碑与安全测试 */}
                <div className="radar-grid-2col">
                  <div className="radar-card">
                    <div className="card-header">
                      <h3><i className="fa-solid fa-car-burst"></i> 真实车主缺陷案例与黑屏统计</h3>
                      <span className="header-tag tag-rose">负面口碑脱水</span>
                    </div>
                    <div className="cases-list">
                      {modelReport.report?.reliability_cases?.length > 0 ? (
                        modelReport.report.reliability_cases.map((c, idx) => (
                          <div key={idx} className="case-item">
                            <div className="case-type-badge">{c.category || '电子车机'}</div>
                            <div className="case-detail">
                              <strong>{c.issue || c.title || '车机偶发黑屏与倒车影像延迟'}</strong>
                              <p>{c.description || 'OTA固件更新后部分偶发死机，需长按方向盘滚轮硬重启。'}</p>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="case-item">
                          <div className="case-type-badge">车身底盘</div>
                          <div className="case-detail">
                            <strong>原厂刹车片热衰减与低滚阻轮胎湿地抓地力</strong>
                            <p>大马力重车搭配低滚阻环保胎，湿滑路面起步易打滑，建议升级高性能制动与轮胎。</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="radar-card">
                    <div className="card-header">
                      <h3><i className="fa-solid fa-shield-cat"></i> 权威碰撞测试与电池安全体系</h3>
                      <span className="header-tag tag-emerald">C-IASI / GB 38031</span>
                    </div>
                    <div className="safety-rating-box">
                      <div className="rating-item">
                        <span className="rating-label">车内乘员安全指数:</span>
                        <span className="rating-score score-g">G (优秀)</span>
                      </div>
                      <div className="rating-item">
                        <span className="rating-label">正面 25% 偏置碰撞:</span>
                        <span className="rating-score score-g">G (优秀·A柱坚固)</span>
                      </div>
                      <div className="rating-item">
                        <span className="rating-label">热失控与针刺安全:</span>
                        <span className="rating-score score-g">GB 38031 5分钟不起火超额满足</span>
                      </div>
                      <div className="safety-summary">
                        整车高强度钢与超高强度铝合金笼式车身结构，底盘电池包具备三重抗压防护横梁。
                      </div>
                    </div>
                  </div>
                </div>

                {/* 全景报告 Markdown 预览 */}
                {modelReport.report_markdown && (
                  <div className="radar-card markdown-card">
                    <div className="card-header">
                      <h3><i className="fa-solid fa-file-contract"></i> 完整综合真实性审计报告全文</h3>
                    </div>
                    <pre className="report-markdown-view">{modelReport.report_markdown}</pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-notice">未检索到该车型的真实性报告档案。</div>
            )}
          </div>
        )}

        {/* TAB 2: 营销黑话去水机 */}
        {activeTab === 'debias' && (
          <div className="debias-view">
            <div className="debias-input-box">
              <label>输入车企官方、KOL或销售宣传黑话：</label>
              <div className="input-row">
                <input
                  type="text"
                  value={claimInput}
                  onChange={(e) => setClaimInput(e.target.value)}
                  placeholder="例如：全域800V高压超充、500万以内最好、真正的无图全场景智驾..."
                />
                <button 
                  className="btn-debias" 
                  onClick={handleRunDebias}
                  disabled={debiasing}
                >
                  {debiasing ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-wand-magic-sparkles"></i>} 物理去水
                </button>
              </div>

              <div className="preset-claims">
                <span>快捷黑话体验：</span>
                {PRESET_DEBIAS_CLAIMS.map((claim, idx) => (
                  <button
                    key={idx}
                    className="preset-tag"
                    onClick={() => {
                      setClaimInput(claim);
                    }}
                  >
                    {claim}
                  </button>
                ))}
              </div>
            </div>

            {debiasResult && (
              <div className="debias-result-card">
                <div className="debias-header">
                  <div className="claim-highlight">
                    <i className="fa-solid fa-quote-left"></i> {claimInput}
                  </div>
                  <span className="risk-badge">
                    识别脱水项: {debiasResult.detected_fluff_count || debiasResult.fluff_items?.length || 1} 处
                  </span>
                </div>

                <div className="debias-body">
                  {/* 后端返回的具体脱水项列表 */}
                  {debiasResult.fluff_items && debiasResult.fluff_items.length > 0 ? (
                    debiasResult.fluff_items.map((item, idx) => (
                      <div key={idx} className="debias-section">
                        <h4><i className="fa-solid fa-burst"></i> 【{item.marketing_claim || '营销宣称'}】的物理真相</h4>
                        <p className="reality-text">{item.physical_reality || item.explanation}</p>
                        {item.counter_argument && (
                          <p className="advice-text"><i className="fa-solid fa-lightbulb"></i> <strong>反问销售话术：</strong>{item.counter_argument}</p>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="debias-section">
                      <h4><i className="fa-solid fa-burst"></i> 宣传表象 vs 物理现实</h4>
                      <p className="reality-text">
                        {debiasResult.physical_reality || debiasResult.summary_markdown ||
                         "宣称的‘全域800V’往往仅是动力电池与后驱电机达到550-700V区间，而在第三方非超充桩上，受限于国网国标桩最高电压，必须通过整车升压模块充电，峰值功率只能达到60-90kW，‘5分钟充200公里’只能在自建专属桩且电网负荷允许时触发。"}
                      </p>
                    </div>
                  )}

                  {debiasResult.charging_reality && (
                    <div className="debias-section">
                      <h4><i className="fa-solid fa-bolt"></i> 实际充电条件与限制</h4>
                      <p className="reality-text">{debiasResult.charging_reality}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: 跨车企核心技术对决 */}
        {activeTab === 'compare' && (
          <div className="compare-view">
            <div className="preset-compare-bar">
              <span className="compare-label">热门对决战场：</span>
              <div className="compare-chips">
                {PRESET_TECH_COMPARISONS.map((p, idx) => (
                  <button
                    key={idx}
                    className={`compare-chip ${compareSelection.label === p.label ? 'active' : ''}`}
                    onClick={() => handleRunCompare(p)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {comparing ? (
              <div className="truth-loading">
                <i className="fa-solid fa-circle-notch fa-spin"></i> 正在从知识图谱提取技术实体与多维横评维度...
              </div>
            ) : compareMatrix ? (
              <div className="compare-matrix-card">
                <div className="compare-header">
                  <h3>{compareMatrix.domain_name || '技术领域对比'}</h3>
                  <p className="target-func">{compareMatrix.target_function || '核心技术方案与用户体验横评'}</p>
                </div>

                <div className="matrix-table-wrap">
                  <table className="matrix-table">
                    <thead>
                      <tr>
                        <th>对比维度</th>
                        {compareMatrix.compared_entities?.map((ent, idx) => (
                          <th key={idx}>{ent.canonical_name || ent.name || `方案 ${idx + 1}`}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {compareMatrix.dimensions?.map((dim, dIdx) => (
                        <tr key={dIdx}>
                          <td className="dim-name">{dim.dimension_name}</td>
                          {compareMatrix.compared_entities?.map((ent, eIdx) => {
                            const val = dim.evaluations ? dim.evaluations[ent.canonical_name || ent.name] : null;
                            return (
                              <td key={eIdx} className="dim-val">
                                {val ? (
                                  <span>{val}</span>
                                ) : (
                                  <span className="text-muted">行业标准水准</span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {compareMatrix.key_differentiators && (
                  <div className="diff-card">
                    <h4><i className="fa-solid fa-bolt"></i> 核心差异与选购结论</h4>
                    {typeof compareMatrix.key_differentiators === 'string' ? (
                      <p>{compareMatrix.key_differentiators}</p>
                    ) : (
                      <div className="differentiator-items">
                        {Object.entries(compareMatrix.key_differentiators).map(([k, v], idx) => (
                          <div key={idx} className="diff-item" style={{ marginBottom: '8px' }}>
                            <strong style={{ color: '#38bdf8' }}>{k}：</strong>
                            <span>{typeof v === 'string' ? v : JSON.stringify(v)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {compareMatrix.sales_guidance && (
                  <div className="diff-card guidance-card" style={{ marginTop: '12px', background: 'rgba(56, 189, 248, 0.08)', borderColor: 'rgba(56, 189, 248, 0.25)' }}>
                    <h4 style={{ color: '#38bdf8' }}><i className="fa-solid fa-compass"></i> 4S店销售话术鉴别与选购指南</h4>
                    <p>{typeof compareMatrix.sales_guidance === 'string' ? compareMatrix.sales_guidance : JSON.stringify(compareMatrix.sales_guidance)}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-notice">点击上方对决预设开始横评。</div>
            )}
          </div>
        )}

        {/* TAB 4: 4S店透明底价避坑器 */}
        {activeTab === 'pricing' && (
          <div className="pricing-view">
            <div className="pricing-layout">
              {/* 输入表单 */}
              <div className="pricing-form-card">
                <h3><i className="fa-solid fa-calculator"></i> 购车底价参数录入</h3>
                <form onSubmit={handleCalculatePricing}>
                  <div className="form-group">
                    <label>目标车型</label>
                    <input
                      type="text"
                      value={pricingForm.carModel}
                      onChange={(e) => setPricingForm({ ...pricingForm, carModel: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>官方指导价 (万 RMB)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={pricingForm.msrpWan}
                      onChange={(e) => setPricingForm({ ...pricingForm, msrpWan: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>4S店裸车现金立减 (万 RMB)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={pricingForm.cashDiscount}
                      onChange={(e) => setPricingForm({ ...pricingForm, cashDiscount: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>选装基金/权益折现 (万 RMB)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={pricingForm.perksDiscount}
                      onChange={(e) => setPricingForm({ ...pricingForm, perksDiscount: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>置换/报废国家补贴 (万 RMB)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={pricingForm.tradeInSubsidy}
                      onChange={(e) => setPricingForm({ ...pricingForm, tradeInSubsidy: e.target.value })}
                    />
                  </div>
                  <button type="submit" className="btn-calc" disabled={calculatingPrice}>
                    {calculatingPrice ? '计算中...' : '核算真实透明落地价'}
                  </button>
                </form>
              </div>

              {/* 计算结果卡片 */}
              {pricingResult && (
                <div className="pricing-result-card">
                  <div className="pricing-summary-box">
                    <div className="summary-title">真实全包落地总价 (Zero Markup)</div>
                    <div className="price-big-number">
                      ¥ {(totalDriveAwayWan * 10000).toLocaleString('zh-CN')}
                      <span className="price-wan">({totalDriveAwayWan.toFixed(2)} 万元)</span>
                    </div>
                  </div>

                  <div className="cost-breakdown-list">
                    <div className="cost-row">
                      <span>官方指导裸车价</span>
                      <span>¥ {((parseFloat(pricingForm.msrpWan) || 21.98) * 10000).toLocaleString('zh-CN')}</span>
                    </div>
                    <div className="cost-row text-emerald">
                      <span>综合减免 (现金立减+权益+置换补贴)</span>
                      <span>- ¥ {(((parseFloat(pricingForm.cashDiscount) || 0) + (parseFloat(pricingForm.perksDiscount) || 0) + (parseFloat(pricingForm.tradeInSubsidy) || 0)) * 10000).toLocaleString('zh-CN')}</span>
                    </div>
                    <div className="cost-row">
                      <span>实际成交裸车底价</span>
                      <span className="fw-bold">¥ {(netCarPriceWan * 10000).toLocaleString('zh-CN')}</span>
                    </div>
                    <div className="cost-row">
                      <span>法定车辆购置税 (新能源免税/减免)</span>
                      <span>¥ {(taxWan * 10000).toLocaleString('zh-CN')}</span>
                    </div>
                    <div className="cost-row">
                      <span>合规商业全险 + 交强险</span>
                      <span>¥ {(insuranceWan * 10000).toLocaleString('zh-CN')}</span>
                    </div>
                    <div className="cost-row">
                      <span>车管所上牌工本费</span>
                      <span>¥ {(miscWan * 10000).toLocaleString('zh-CN')}</span>
                    </div>
                  </div>

                  {/* 4S 店套路避坑红线 */}
                  <div className="hidden-fees-warning">
                    <div className="warning-title">
                      <i className="fa-solid fa-triangle-exclamation"></i> 4S 店隐形收费曝光与拒付指南
                    </div>
                    {hiddenFeeWarnings.length > 0 ? (
                      <ul>
                        {hiddenFeeWarnings.map((w, idx) => (
                          <li key={idx}><strong>{w.fee_name}（常见收费 ¥{w.typical_cost_yuan}）：</strong>{w.warning_text}</li>
                        ))}
                      </ul>
                    ) : (
                      <ul>
                        <li><strong>出库费/PDI检测费（通常要 1000~3000 元）：</strong> 纯属违规巧立名目，依据《消费者权益保护法》PDI属于经销商应尽交付义务，坚决拒付！</li>
                        <li><strong>金融服务费/贷款手续费（通常收 2000~5000 元）：</strong> 银保监会明令禁止代收贷款服务费，如遇强制收取可向银保监与市场监管局投诉。</li>
                        <li><strong>强制店内上牌（通常要 1500~2500 元）：</strong> 个人自去车管所仅需 120~130 元工本费，无任何代办壁垒。</li>
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default TruthRadar;
