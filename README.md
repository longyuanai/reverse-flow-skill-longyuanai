# reverse-flow-skill

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
reverse-flow-skill/
  README.md
  LICENSE
  .gitignore
  skills/
    reverse-flow/
      SKILL.md
      README.md
      agents/openai.yaml
      references/
      scripts/
```

## 安装

复制技能目录到 Codex 技能目录：

```powershell
Copy-Item -Recurse ".\skills\reverse-flow" "$env:USERPROFILE\.codex\skills\reverse-flow"
```

## 使用示例

```text
使用 $reverse-flow 分析这个样本。真心为你
```

```text
真心为你，进入逆向模式，分析我上传的 crackme，帮我找到 flag 校验逻辑。
```

## 脚本示例

```powershell
python ".\skills\reverse-flow\scripts\create_case.py" --case-name sample-audit --goal "local CTF reverse analysis" --out ".\work"
python ".\skills\reverse-flow\scripts\triage_artifact.py" ".\sample.bin" --out ".\work\sample-audit\triage"
python ".\skills\reverse-flow\scripts\tool_audit.py" --profile native --out ".\work\sample-audit\tools\native-tool-audit.md"
python ".\skills\reverse-flow\scripts\report_from_triage.py" ".\work\sample-audit\triage\*.json" --out ".\work\sample-audit\reports\initial-report.md"
```

## License

- ## 交流群聊发布页
- <QQ> 252452778 (非本人运营）



- <发布分享频道> https://t.me/zxwnai



- <闲聊技术交流吹水群聊> https://t.me/zxwnaisui


## 赞助和打赏喵
 -爱发电 https://ifdian.net/a/zxwn520



MIT License



