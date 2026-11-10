# reverse-flow-skill

[![CI](https://github.com/longyuanai/reverse-flow-skill-longyuanai/actions/workflows/ci.yml/badge.svg)](https://github.com/longyuanai/reverse-flow-skill-longyuanai/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-52%20passed-brightgreen.svg)](#自动化测试与-ci)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://github.com/longyuanai/reverse-flow-skill-longyuanai)
[![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-orange.svg)](LICENSE)
[![Commercial](https://img.shields.io/badge/commercial-available-success.svg)](COMMERCIAL.md)

> 面向 AI Agent / Codex 的本地 CTF 逆向工程流程技能。加载后通过 **“真心为你”** 进入逆向模式，默认在本地沙盒、CTF、crackme、wargame 或训练靶场环境中工作，按 **分析 → 报告 → 逆向 → 深度逆向 → 漏洞研判 → 用户选择下一步** 的流程推进。

## 项目简介

`reverse-flow` 是一个给 AI Agent 使用的逆向工程技能。它把逆向任务拆成稳定流程，让智能体在本地沙盒中完成样本分诊、工具链检查、静态分析、深度逆向、漏洞研判和报告输出。

项目采用 **英文内核提示词 + 中文用户交互**：

- 内部执行规则、工具选择和流程控制使用英文，提升模型稳定性。
- 启动词、报告结构和下一步菜单默认使用中文。
- 用户表达不清时，技能会先做意图恢复，而不是直接停止。

## 启动词

需要围绕单个行为做更深入、可核验的分析时，使用新增的 [破甲 Skill](skills/pojia/SKILL.md)：`$pojia` 或“破甲”。它保留原始证据、竞争假设、反例和独立核验，不更改原有 `reverse-flow`。设计题目与验收方法见 [破甲设计](docs/pojia-design.md)，本机安装和真实样本实测见 [实测报告](docs/pojia-validation-2026-10-26.md)。

```text
真心为你
```

启动后提示：

```text
已进入逆向模式。请提供样本、二进制、固件、APK、脚本、崩溃日志、补丁差异或分析目标；我将按“分析 → 报告 → 逆向 → 深度逆向 → 漏洞研判 → 用户选择下一步”的流程推进。
```

## 默认上下文

该技能默认用户处于：

- 本地 CTF 环境
- crackme / wargame
- 本地训练靶场
- 授权沙盒逆向实验
- 离线样本分析环境

用户不需要每轮重复说明“这是 CTF”或“这是本地靶场”。

## 口语化需求归一化

| 用户表达 | 技能理解 |
|---|---|
| 解锁 XX | 定位 feature gate / validation branch，解释逻辑，给出本地 patch 或正确输入思路 |
| 去除 XX | 定位 check routine，记录证据，在副本上给出 patch / 调试方案 |
| 绕过反调试 | 分析 anti-debug 逻辑，给出本地调试配置或 patch 选项 |
| 让它通过 / make it pass | 恢复校验逻辑，推导期望输入、状态转移或 flag 格式 |
| 拿 flag | 分析验证流程、编码/加密逻辑和触发条件 |

## 工作流

```text
分析 → 报告 → 逆向 → 深度逆向 → 漏洞研判 → 用户选择下一步
```

## 项目结构

```text
reverse-flow-skill-longyuanai/
  README.md
  LICENSE                           # PolyForm Noncommercial 1.0.0 开源许可
  COMMERCIAL.md                     # 商业授权说明与企业采购通道
  SECURITY.md                       # 负责任的安全漏洞通报政策
  install.ps1                       # Windows PowerShell 一键极速部署向导
  install.sh                        # Linux & macOS Bash 一键极速部署向导
  install.bat                       # Windows CMD 双击一键启动脚本
  demo_quickstart.py                # 30 秒自动化全流程极速演示与算法差分核验
  run_tests.py                      # 全量自动化测试运行器 (52 项测试)
  tests/                            # 自动化单元测试套件
  scripts/
    craft_pojia_bridge.py           # Craft Anything 净室复刻融合桥接引擎与双轨核验
    purge_friction.py               # 宿主交互摩擦清除与免扰白名单注入工具
    pack_skills.py                  # 自动化便携技能包打包与 SHA256 校验生成器
    generate_license.py             # 商业客户授权证书与数字签名生成工具
  docs/
    commercial/                     # 商业化签约、合规与营销材料
      PRICING.md                    # 官方授权版本报价矩阵
      ENTERPRISE-SOLUTION.md        # 企业级私有化部署与 ROI 商业解决方案白皮书
      PROMOTION-WECHAT-ARTICLE.md   # 微信公众号 / FreeBuf 宣发与引流推文稿件
      LICENSE-AGREEMENT-TEMPLATE.md # 商业采购合同标准协议模板
      LICENSE-CERTIFICATE-SAMPLE.md # 官方商业授权证书样张
      PURCHASE-FAQ.md               # 商业采购与开票常见问答
  skills/
    reverse-flow/                   # 逆向引导与自动化分诊技能
      SKILL.md
      README.md
      agents/openai.yaml
      references/
      scripts/
        create_case.py              # Case 创建与样本哈希/清单自动固化
        triage_artifact.py          # 离线文件分诊与 PE/ELF 二进制结构解析
        tool_audit.py               # 本地逆向工具链与 Python 模块真实审计
        report_from_triage.py       # 自动化初筛 Markdown 报告生成
    pojia/                          # 深度破甲与闭环验证技能
      SKILL.md
      references/
      scripts/
        inspect_cil.py              # 零外部依赖 .NET CIL 原生反汇编器
        diff_verifier.py            # 原生可执行文件与 Python 还原代码的差分核验器
        evidence.py                 # 样本证据快照与防篡改验证器
  validation/                       # 基准测试用例与固化验证材料
```

## 安装与多平台部署

本技能支持 **Claude Code CLI** 与 **OpenAI Codex** 双平台，并提供一键式无扰极速安装向导：

### 一键极速部署（推荐，30秒全自动同步与免扰白名单注入）

- **Windows (PowerShell)**:
  ```powershell
  .\install.ps1
  ```
- **Windows (CMD / 双击运行)**:
  ```cmd
  install.bat
  ```
- **Linux / macOS (Bash)**:
  ```bash
  bash install.sh
  ```
*向导会自动校验 Python 3.10+ 环境、将技能同步至双平台、注入非破坏性执行白名单（消除反复弹窗提权）、并运行全量自检测试。*

### 手动安装方式
```powershell
# 1. 安装至 Claude Code CLI
Copy-Item -Recurse ".\skills\reverse-flow" "$env:USERPROFILE\.claude\skills\reverse-flow" -Force
Copy-Item -Recurse ".\skills\pojia" "$env:USERPROFILE\.claude\skills\pojia" -Force

# 2. 安装至 OpenAI Codex
Copy-Item -Recurse ".\skills\reverse-flow" "$env:USERPROFILE\.codex\skills\reverse-flow" -Force
Copy-Item -Recurse ".\skills\pojia" "$env:USERPROFILE\.codex\skills\pojia" -Force
```

## 使用示例

### 触发 reverse-flow（全局分诊与引导）
```text
使用 $reverse-flow 分析这个样本。真心为你
```
```text
真心为你，进入逆向模式，分析我上传的 crackme，帮我找到 flag 校验逻辑。
```

### 触发 pojia（深度破甲与算法还原）
```text
破甲，针对 sample.exe 中的核心算法进行还原，并生成可重跑的差分验证报告。
```

## 30 秒自动化全流程极速演示 (Quickstart Demo)

克隆项目后无需任何配置，直接运行自包含演示脚本，即可在 5 秒内直观体验 Case 隔离、静态分诊、CIL 反汇编与 100% 差分核验全流程：

```powershell
python demo_quickstart.py
```

## 自动化测试与自检

项目内置完整的自动化测试套件，开箱即检：

```powershell
python run_tests.py
```

## 典型脚本工作流

```powershell
# 1. 创建隔离 Case 并自动摄入、哈希固化样本
python skills/reverse-flow/scripts/create_case.py --case-name my-crackme --goal "recover flag check" --artifact ./sample.exe --out ./cases

# 2. 离线多维静态分诊（PE/ELF 节区、信息熵、指标清洗、工具推荐）
python skills/reverse-flow/scripts/triage_artifact.py ./sample.exe --out ./cases/my-crackme/triage

# 3. 针对 .NET/CIL 目标执行零外部依赖反汇编与 Token 解析
python skills/pojia/scripts/inspect_cil.py ./sample.exe --method Transform --format text

# 4. 针对 Native 原生目标 (PE32/PE32+/ELF32/ELF64) 执行零外部依赖入口点解析与汇编解码
python skills/pojia/scripts/inspect_native.py ./sample.exe --json

# 5. 算法还原后的自动化差分测试（边界值 + 随机测试 + 负对照）
python skills/pojia/scripts/diff_verifier.py --target ./sample.exe --py ./reconstructed.py --func transform --count 100 --out ./cases/my-crackme/reports/diff.json

# 6. Craft Anything + Pojia 双轨净室复刻融合桥接
python scripts/craft_pojia_bridge.py audit                         # 审计逆向与复刻环境就绪状态
python scripts/craft_pojia_bridge.py triage ./sample.exe           # 执行联合静态多维分诊
python scripts/craft_pojia_bridge.py verify ./sample.exe --py ./reconstructed.py --func transform
```

## Craft Anything 净室复刻与双轨闭环核验 (Clean-Room Recreation)

针对目标软件/固件/Crackme 的 1:1 净室复刻需求，套件通过 `scripts/craft_pojia_bridge.py` 深度整合了 **Craft Anything (v0.6.0)** 纯 Rust 320-Tool 引擎与 Pojia 原生反汇编核验内核，形成 **“联合分诊 → 行为建模 → 净室重构 → 双轨核验”** 的工业级逆向与复刻闭环：

```text
       [原始二进制 / 网页 / 固件 / Crackme 目标]
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
    [Pojia 原生轻量分诊]        [Craft Anything 320-Tool]
    - PE/ELF/BSJB 元数据解析     - 界面 DOM/视觉特征捕捉
    - 加壳/混淆器轻量特征识别   - 协议接口与网络流量录制
            └─────────────┬─────────────┘
                          │ 联合生成分诊洞察 (hybrid_triage)
                          ▼
            [Clean-Room 净室代码重构]
        (基于黑盒可观测行为构建，无侵权版权污染)
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
      【轨道 1: 算法差分核验】     【轨道 2: 界面/行为保真】
    - diff_verifier 极限边界注入   - Multi-viewport 视觉对比
    - 0, 1, 2^n, 0xFFFFFFFF       - 行为交互流自动化回放
    - 杜绝 AI 逆向幻觉 (置信度100%) - Likeness 保真度评分
            └─────────────┬─────────────┘
                          ▼
             [颁发 Clean-Room 净室认证证书]
```

### 触发净室复刻指令
在 Claude Code CLI 或 OpenAI Codex 中直接输入：
```text
净室复刻，针对 sample.exe 开展黑盒行为建模与算法重构，并通过 pojia 运行双轨闭环验证。
```

## 开源许可与商业授权 (License & Commercial)

本项目采用 **双轨许可模式 (Dual-Licensing Model)**：

- **非商业用途 (Noncommercial)**：遵循 [PolyForm Noncommercial License 1.0.0](LICENSE)，对个人学习、学术研究、非营利性安全实验及 CTF 竞赛演练完全免费开放。
- **商业用途 (Commercial)**：任何营利性实体在生产环境部署、产品集成、商业安全评估或付费培训，请参阅 [商业授权说明书 (COMMERCIAL.md)](COMMERCIAL.md) 采购官方商业许可证。

### 商业采购快捷导航
- 🏢 **企业解决方案**：[企业私有化部署与 ROI 白皮书 (ENTERPRISE-SOLUTION.md)](docs/commercial/ENTERPRISE-SOLUTION.md)
- 💰 **官方报价与权益**：[授权版本报价矩阵 (PRICING.md)](docs/commercial/PRICING.md)
- 📄 **采购合同模板**：[商业授权标准协议 (LICENSE-AGREEMENT-TEMPLATE.md)](docs/commercial/LICENSE-AGREEMENT-TEMPLATE.md)
- 🏅 **合规凭据样张**：[商业授权证书样张 (LICENSE-CERTIFICATE-SAMPLE.md)](docs/commercial/LICENSE-CERTIFICATE-SAMPLE.md)
- ❓ **采购开票问答**：[商业采购常见 FAQ (PURCHASE-FAQ.md)](docs/commercial/PURCHASE-FAQ.md)
- 📢 **宣发推广软文**：[公众号/FreeBuf 推广推文稿件 (PROMOTION-WECHAT-ARTICLE.md)](docs/commercial/PROMOTION-WECHAT-ARTICLE.md)
- 📮 **在线采购申请**：[提交商业采购 Issue](https://github.com/longyuanai/reverse-flow-skill-longyuanai/issues/new?template=commercial_inquiry.yml) 或发信至 `1507205727@qq.com`

### 商业证书签发工具 (License Issuer)
针对采购商业授权的客户，开发者可通过内置工具一键生成防伪电子证书与采购凭证：

```powershell
python scripts/generate_license.py --client "某某企业攻防实验室" --tier enterprise --email "client@corp.com" --out ./dist/licenses
```

---

## 一键技能打包 (Release Packaging)

通过内置的打包工具，可一键生成用于分发与离线加载的标准 `.skill` 压缩包和 SHA256 校验和：

```powershell
python scripts/pack_skills.py --out ./dist
```

---

## 免责声明与合规使用规范 (Disclaimer & Acceptable Use Policy)

1. **合法授权前提**：本项目及其相关工具仅供计算机科学教学、学术研究、授权安全评估、CTF 竞赛演练及恶意代码防御性分诊使用。使用者在分析任何目标二进制文件前，必须确保已取得权利人的明确合法授权，或属于《计算机软件保护条例》第十七条规定的合理使用范畴。
2. **禁止非法破坏与侵权**：严禁将本项目用于侵犯他人知识产权、规避或破坏正版商业软件版权技术保护措施（DRM / 授权锁）、制作或传播恶意破解补丁、未经授权的网络入侵、恶意软件传播或任何违反所在国/地区法律法规的活动。
3. **技术中立与责任限制**：本项目作为中立的技术分析与逆向工程辅助工具提供。因使用者违反法律、未授权分析受保护商业软件或滥用工具所引发的任何直接或间接法律纠纷与责任，均由使用者自行承担，本项目作者及贡献者概不承担任何连带责任。

---

## 商务合作与交流

- **商务采购与咨询邮箱**：`1507205727@qq.com`
- **公众号 / 知识库**：微信公众号【龙渊手记】
- **GitHub**：[@longyuanai](https://github.com/longyuanai)




