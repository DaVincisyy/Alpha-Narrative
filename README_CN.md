# 📊 AlphaNarrative

> **将财报电话会议转化为量化交易信号的 LLM 驱动系统**

一个生产级的量化 NLP 管道，从财报电话会议中提取情绪因子，将管理层叙事转化为可操作的交易信号。

[English](README.md) | 简体中文

---

## 🎯 为什么重要

在量化金融中，**另类数据**是新的 Alpha 来源。传统量化模型依赖价格和成交量，而**财报电话会议的文本分析**提供独特洞察：

- **管理层信心**：前瞻性陈述和信念强度
- **风险意识**：公司如何承认和沟通风险
- **战略转变**：股价变动前的重大转型

**问题**：人工分析无法规模化。每季度阅读数百份财报不可能。

**解决方案**：自动化、可复现的管道：
1. ✅ 从多个来源抓取财报文本
2. ✅ 使用 Claude Sonnet 4.6 提取 3 个量化情绪因子
3. ✅ 完整数据追溯（模型、Prompt 版本、时间戳）
4. ✅ 交互式仪表盘用于因子探索
5. ✅ 可直接用于回测和策略部署

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/yourusername/quant-NPL.git
cd quant-NPL
pip install -r requirements.txt

# 设置 API 凭证
export ANTHROPIC_AUTH_TOKEN='your-token-here'
export ANTHROPIC_BASE_URL='https://xuedingtoken.com'
```

### 5 分钟教程

```bash
# 1. 抓取财报
python demo_scraper.py

# 2. 处理数据
python src/pipeline.py

# 3. 提取因子
python src/sentiment_extractor.py --limit 10

# 4. 分析
python src/factor_analysis.py

# 5. 启动仪表盘
streamlit run app.py
```

---

## 🧠 因子定义

系统提取 **3 个量化情绪因子**（1-10 分）：

### 1. 📈 信心分数 (Confidence Score)

**衡量内容**：管理层对未来业绩的信念和确定性

**评分标准**：
- **1-3**：防御性、不确定的语言（"可能"、"也许"、"挑战"）
- **4-6**：中性、事实性陈述
- **7-10**：强烈信念（"将会"、"有信心"、"预期"）

**交易信号**：高信心 → 潜在超预期

---

### 2. ⚠️ 风险意识 (Risk Awareness)

**衡量内容**：管理层讨论风险和不确定性的明确程度

**评分标准**：
- **1-3**：最小风险讨论，过度乐观
- **4-6**：平衡的风险承认
- **7-10**：强调风险、逆风、不确定性

**交易信号**：
- 极低 (1-2) → 隐藏风险，潜在下行
- 极高 (8-10) → 保守指引，潜在超预期

---

### 3. 🔄 战略转变 (Strategic Shift)

**衡量内容**：战略变化或业务转型的幅度

**评分标准**：
- **1-3**：一切照旧，无重大变化
- **4-6**：渐进式调整
- **7-10**：重大转型、新举措、显著变化

**交易信号**：高转变 → 波动率增加，潜在重估

---

## 📊 架构

```
财报文本 → 爬虫 → 数据处理 → LLM 提取 → 因子分析 → 仪表盘
  (Web)   (Stage1)  (Stage2)   (Stage3)   (Stage4)   (Stage5)
```

**5 个阶段**：
1. **爬虫**：从 Motley Fool 等网站抓取
2. **处理**：清洗、分块（段落/Token 模式）
3. **提取**：Claude Sonnet 4.6 提取因子
4. **分析**：统计分析 + 9 个可视化
5. **仪表盘**：Streamlit 交互式探索

---

## 📈 性能

| 数据集 | Chunks | 时间 | 成本 | 吞吐量 |
|--------|--------|------|------|--------|
| 1 家公司 | 6 | 24秒 | $0.05 | 15 chunks/分钟 |
| 10 家公司 | 60 | 4分钟 | $0.50 | 15 chunks/分钟 |
| 100 家公司 | 600 | 40分钟 | $5.00 | 15 chunks/分钟 |

---

## 🗺️ 路线图

### ✅ 已完成 (v1.0)
- [x] 多源财报爬虫
- [x] 灵活数据管道
- [x] LLM 因子提取
- [x] 统计分析套件
- [x] 交互式仪表盘
- [x] 29 个单元测试

### 🚧 进行中 (v1.1)
- [ ] 更多数据源（SeekingAlpha、IR 网站）
- [ ] 更多因子（前瞻指引、竞争定位）
- [ ] 真实市场数据集成
- [ ] 因子标准化

### 🔮 未来 (v2.0)
- [ ] 回测引擎（IC、Sharpe、最大回撤）
- [ ] 高级 NLP（NER、主题建模）
- [ ] 生产部署（Docker、Airflow）
- [ ] 多语言支持（中文、日文）

---

## 📚 文档

- [安装指南](docs/installation.md)
- [使用教程](docs/tutorial.md)
- [API 参考](docs/api.md)
- [因子解释](docs/factors.md)
- [常见问题](docs/faq.md)

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 📞 联系

- **Issues**: [GitHub Issues](https://github.com/yourusername/quant-NPL/issues)
- **讨论**: [GitHub Discussions](https://github.com/yourusername/quant-NPL/discussions)

---

<div align="center">

**为量化社区用 ❤️ 构建**

⭐ 如果这个项目对你有帮助，请给个 Star！

</div>
