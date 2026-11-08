# 微信公众号 / FreeBuf 推广宣发文稿：告别逆向幻觉，首个 AI 逆向破甲套件开源

> **文稿说明**：本文专为微信公众号【龙渊手记】、FreeBuf、知乎、安全客及先知社区量身打造。语言风格兼具黑客技术极客感与商业落地专业度，文末无缝引导 GitHub Star、粉丝群交流与商业采购转化。
> **建议排版**：标题采用悬念+技术突破，正文穿插代码块与终端截图，文末放置二维码与采购链接。

---

## 【发布标题备选】
1. **《告别大模型逆向幻觉！首个零依赖自举 + 差分验证的 AI 逆向破甲引擎正式开源 (v1.0.0)》** *(推荐)*
2. **《做 CTF 还在人肉反编译？我用 Claude Code + 破甲技能 3 分钟秒解 Crackme》**
3. **《重磅：面向 AI Agent 的二进制逆向利器 reverse-flow 发布，附完整源码与工程实践》**

---

## 【正文内容】

大家好，我是龙渊。

过去一年里，大语言模型（LLM）在写代码、审计源码方面展现出了惊人的效率。但如果你曾尝试让大模型帮你去逆向一段编译后的二进制程序、分析恶意样本或者做一道 CTF 逆向题，你大概率经历过被**“逆向幻觉”**支配的恐惧：

- **幻觉灾难 1**：面对反汇编指令，模型看似胸有成竹，分析起算法来头头是道，结果写出来的 Python 还原代码一跑——全是错的；
- **幻觉灾难 2**：在干净的沙箱或轻量容器里，根本没有安装商业级的 IDA Pro、Ghidra 或者 ILSpy，模型立刻两手一摊：“环境缺少工具，无法分析”；
- **幻觉灾难 3**：分析过程全凭黑盒推理，没有任何证据快照和验证闭环，结论无法被独立核验。

为了彻底解决“AI 逆向不可信、无法落地”的顽疾，我们历时数月重构与打磨，正式开源了面向 AI Agent / Codex 的本地逆向工程双技能套件：**`reverse-flow-skill`** 与 **`pojia`（破甲）**，并在今天正式发布 **v1.0.0** 版本！

---

### 一、核心突破：如何用确定性代码“驯服”大模型？

我们坚信：**AI 负责敏捷探索与假设生成，确定性代码负责证据锁定与闭环核验。**

整个技能套件由两款协同技能组成：
1. **`reverse-flow`（全局分诊与流程控制）**：通过“真心为你”口令进入逆向模式。负责引导样本隔离、计算哈希指纹、执行 PE/ELF 节区多维静态分诊，并自动化生成符合安全审计规范的 Markdown 报告。
2. **`pojia`（深度破甲与算法还原）**：聚焦于核心复杂逻辑的“外科手术式”解剖与数学级复现。

#### 突破 1：零外部依赖自举解析引擎（`inspect_cil.py`）
在没有安装任何外部反编译器（没有 dnSpy、没有 ILSpy）的轻量沙箱中，我们利用 Python 纯标准库（`struct`、`hashlib`）纯手工实现了对 **ECMA-335 CLI 标准** 的完整解析！
- 原生解析 PE/COFF 头与 CLR BSJB 元数据流（`#~`、`#Strings`、`#US`、`#Blob`、`#GUID`）；
- 自动解码 Tiny/Fat Method Header，逆向提取 IL 字节码指令并准确还原 MemberRef / TypeRef Token；
- 具备强悍的畸形头与截断 PE 异常容错机制，杜绝恶意二进制引发的解析器崩溃。

#### 突破 2：黑盒差分核验器，100% 杜绝幻觉（`diff_verifier.py`）
大模型还原出来的 Python 算法对不对？别猜，让数据说话！
- 核验器自动向原生可执行文件与 Python 还原代码并发注入海量测试用例；
- 覆盖极端边界值（`0`, `1`, `2^n`, `0x7FFFFFFF`, `0xFFFFFFFF`）、海量伪随机 Corpus 以及畸形反例；
- 逐个比对二进制与 Python 的输出真值，实现**字节级一致性验证**。只要出现 1 个比特的偏差，立即勒令大模型修正假设，直到 100% 匹配！

---

### 二、工业级品质与全矩阵跨平台验证

我们深知安全工程师对工具稳定性的苛求。本项目已达到工业级交付标准：

- **37 项全自动化测试**：覆盖率 100%，自研测试运行器秒级响应。
- **Pyright 严格模式类型检查**：**0 errors, 0 warnings**。
- **GitHub Actions 全平台 CI 矩阵**：覆盖 **Ubuntu、Windows、macOS** 三大操作系统，在 **Python 3.10、3.11、3.12、3.13** 共 12 种运行环境中全部秒级绿色通过！
- **双平台部署**：原生兼容 **Claude Code CLI** 与 **OpenAI Codex**，一键分发安装。

---

### 三、开源协议与商业授权体系

本项目采用国际通行的 **双轨许可模式 (Dual-Licensing Model)**：

1. **开源非商业用途 (Free Open Source)**：
   遵循 **PolyForm Noncommercial License 1.0.0**。面向个人学习、学术教学、非营利性安全实验及 CTF 竞赛演练，**代码完全免费、无偿开放！**
2. **商业营利用途 (Commercial License)**：
   企事业单位 SOC 团队、商业渗透测试顾问或安全软硬件厂商，如需将本引擎部署在生产环境、集成到内部系统或 SaaS 产品中，我们提供正规商业授权支持：
   - **独立顾问版**：¥699 / 年（单人商用交付合规免责证明）
   - **企业团队版**：¥4,999 / 年 或 ¥9,999 永久买断（企业站点无限席位，支持私有化内网 DeepSeek / Qwen 部署，开具增值税专用发票）
   - **OEM / 白标集成版**：¥19,999 起（允许闭源再分发与产品嵌入）

---

### 四、如何快速上手？

#### 1. 克隆仓库与自检
```bash
git clone https://github.com/longyuanai/reverse-flow-skill-longyuanai.git
cd reverse-flow-skill-longyuanai
python run_tests.py
```

#### 2. 一键安装技能到你的 AI 助手
- **安装到 Claude Code**：
```powershell
Copy-Item -Recurse ".\skills\reverse-flow" "$env:USERPROFILE\.claude\skills\reverse-flow" -Force
Copy-Item -Recurse ".\skills\pojia" "$env:USERPROFILE\.claude\skills\pojia" -Force
```
- **安装到 OpenAI Codex**：
```powershell
Copy-Item -Recurse ".\skills\reverse-flow" "$env:USERPROFILE\.codex\skills\reverse-flow" -Force
Copy-Item -Recurse ".\skills\pojia" "$env:USERPROFILE\.codex\skills\pojia" -Force
```

#### 3. 开启逆向
在对话框输入口令：
> **真心为你**

AI 即可全自动接管分析流程，带你体验前所未有的“人机协同逆向”快感！

---

### 五、项目地址与交流福利

- 🌟 **开源项目仓库**：https://github.com/longyuanai/reverse-flow-skill-longyuanai
- 📦 **v1.0.0 正式发布页**：https://github.com/longyuanai/reverse-flow-skill-longyuanai/releases/tag/v1.0.0
- 商务咨询与授权采购邮箱：`1507205727@qq.com`

**福利互动**：
欢迎前往 GitHub 点亮我们的 ⭐️ **Star**！如果你在实际对抗中遇到了有趣的二进制样本或有特定的格式解析需求，欢迎在后台留言或提交 Issue。

关注微信公众号【**龙渊手记**】，后台回复【**破甲**】，即可免费领取打包好的 `.skill` 便携离线包与 AI 逆向实战电子指南！
