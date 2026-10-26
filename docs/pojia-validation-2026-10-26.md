# 破甲与 REA 安装实测

日期：2026-10-26（北京时间）。范围：本机 Windows、自建 .NET 样本、静态 REA CLI/MCP 与明确可运行的测试 EXE。未对线上服务发起探测。

## 安装来源与变更

| 项目 | 实际值 |
|---|---|
| 用户指定仓库 | `https://github.com/longyuanai/rea-longyuanai` |
| 下载的仓库提交 | `58fb372071e56da9c5df0e37593ee3f0da6b64bc` |
| 实际安装包 | 官方 npm registry 的 `rea-agents@6.4.0` |
| npm gitHead | `a56f7bb668ab23fec8d33f7af353ac7ed2fe1895`（上游 morluto/rea） |
| npm integrity | `sha512-Vj1zWfSlna5bphGoaoI/TcVBuYvze9u+OyPC3Shz8YkBqaCTqB4COnnRoX7XDwMpwI24ZlFEel2yEj0k8LTWEQ==` |
| 运行时 | Node.js 24.18.0；验证脚本使用 Python 3.12.14 |
| 包安装位置 | `E:\001项目\AI安全\破解\.runtime\rea` |
| 源码核对位置 | `E:\001项目\AI安全\破解\.runtime\rea-source` |

仓库 main 与 npm 包不是相同提交。本次使用的是已发布包，不声称已经构建或验证 fork main。安装使用 `--ignore-scripts`，现有编译产物能够运行。`package.json` 和锁文件均固定到精确版本 `6.4.0`；最终锁文件 SHA-256 为 `169b7e71a379f31c922b0d4902c8dd21a38c267e580120d81a446d6dc9186b71`。可复现的两份清单保存在 `validation/pojia/runtime/`，没有将 `node_modules` 放入 Git。

初次 npm 审计发现 Zod `4.4.3` 命中 [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5)：大集合验证可能耗尽内存。REA 本身与 Zod 在审计中各记一个高危条目，是同一传递依赖问题。备份安装清单至 `.runtime/rea-before-zod-4.6.6/` 后，仅在隔离运行目录添加 `overrides.zod = 4.6.6`；未改动 REA 发布包源码。修复后重新运行完整真实样本测试及 npm 审计，当前报告 **0 个已知漏洞告警**。这只代表当次数据库检查，不能推断没有未知漏洞；该依赖覆盖也不等于上游已发布新的 REA 版本。

只为 Codex 注册 REA，使用 `setup --client codex --no-skill --yes --json`；单独安装本项目的“破甲”Skill，不额外安装 REA 的通用 Skill。原配置备份在 `C:\Users\15072\.codex\config.toml.rea.backup`，备份 SHA-256 为 `a1a7f684b580bf6ceddfc597b9ba5eb60e29fa0ae447ad8561dc83b45ba781f9`。解析备份与新配置后比较，确认仅新增 `mcp_servers.rea`，其他配置语义一致。安装器返回 `ready`，限定 Codex 的 doctor 检查通过。

REA 启动项使用现有 `C:\Program Files\nodejs\node.exe` 和工作区中固定版本的绝对启动器路径，不在每次启动时请求 `latest`。不要移动或删除 `.runtime\rea` 后继续使用原启动项。

“破甲”已安装到 `C:\Users\15072\.codex\skills\pojia`，6 个文件与仓库技能源文件逐字节一致，未覆盖已有技能。入口 `SKILL.md` 的 SHA-256 为 `6efac58dbcfd7790afe75efd95426de7c7984a420b78ced771f5bf17c4a9b517`。另提供 `E:\001项目\AI安全\破解\pojia.skill` 归档。加载技能后用“破甲”或 `$pojia` 调用；当前聊天的发现列表需重连刷新。

## 测试材料与原始记录

源程序：`validation/pojia/Fixture.cs`，SHA-256 为 `97f2890a2113345ac2d2cf8492eb639b453b4dc3869c7de0a19b05a365f93479`。使用 Windows 现有 .NET Framework C# 编译器，以 `/optimize+ /debug-` 编译，没有安装额外分析引擎。

最终修复后的原始记录位于 `.validation/rea-run-patched/`：原始 EXE、源码副本、CLI 的 stdout/stderr、MCP 初始化/目录/调用结果与 JSONL 传输记录、CLR 读取的 CIL、输入语料、负对照、所有命令、锁文件副本与 SHA-256 清单。首次测试和一次重跑保留在 `.validation/rea-run-1/` 与 `rea-run-2/`，结果同样通过。以上目录被 Git 忽略，保留在用户本机；报告不代替这些原始材料。精简机器结果另存 `docs/pojia-validation-summary.json`。

| 样本身份 | 实际值 |
|---|---|
| EXE SHA-256 | `a8ed4808697d5fcec98001ba687fcf7f8560045e318d7458461c84898356b660` |
| 格式 | PE32 载体、托管 CIL、AnyCPU；不能据 PE machine 单独称为原生 x86 程序 |
| MVID | `e7fd1e60-1f0f-44ab-8d42-b810441c65db` |
| 目标方法 | `PojiaFixture.Transform`，`uint32 → uint32` |
| 方法 token | `0x06000001`（仅绑定此构建） |
| 方法头偏移 | `592` / `0x250` |
| CIL 偏移与长度 | `604` / `0x25c`，28 字节 |
| CIL SHA-256 | `4884ddd2ff3e3b779069e500059d3537e1f483f212b1d1bb6c9c26541641eab2` |

CIL 原始字节：

```text
02 20 e7 91 3c a5 61 0a 06 1d 62 06 1f 19 64 60
0b 07 20 b1 79 37 9e 5a 1f 11 58 2a
```

## 具体结论和验证

`Main` 从标准输入读取文本，经 `UInt32.TryParse` 后调用 `Transform` 并输出结果。目标函数在 32 位无符号语义下先异或 `0xA53C91E7`，循环左移 7 位，再乘 `2654435761` 并加 `17`，结果按模 `2^32` 保留。CIL 的 `shr.un` 支持逻辑右移解释；不能替换成有符号算术右移。

```python
def transform(value):
    mixed = value ^ 0xA53C91E7
    rotated = ((mixed << 7) | (mixed >> 25)) & 0xFFFFFFFF
    return (rotated * 2654435761 + 17) & 0xFFFFFFFF
```

| 实际检查 | 结果 | 证明范围 |
|---|---|---|
| REA 版本与锁文件 | `6.4.0` 一致 | 所运行的包版本 |
| MCP initialize、分页 tools/list | 成功，170 个工具 | 独立本地 MCP 客户端可连接 |
| 真实样本两次 tools/call | artifact、members 均成功 | 本样本的静态 PE/CLI 分析可用 |
| CLI 与 MCP normalized_result | 完全一致 | 两个入口一致；同解析器，不算独立引擎 |
| EXE 哈希与 REA subject | 一致 | 输出绑定该样本 |
| 直接读取方法字节、CLR Reflection、REA CIL 哈希 | 一致，28 字节 | 方法字节来源及哈希独立核对 |
| 原程序与 Python 数学实现差分 | 321/321 一致 | 固定边界与 seed=20261026 语料 |
| 非法输入 | 4/4 输出 `INVALID` | 负数、超范围、非数字、空行 |
| 改错 XOR 常量的负对照 | 321 个输入均被区分 | 测试能识别此类错误重建 |
| 截断为 256 字节后分析 | 非零退出，exit=1 | 不将不完整文件写成函数恢复成功 |
| Skill 格式检查 | 官方 quick_validate 通过 | 元数据与基本结构 |
| 辅助脚本测试 | 7/7 通过 | 变更、缺文件、迁移、路径逃逸及空清单 |

## 技能行为测试

按 `skill-creator` 的独立评测流程，在不携带作者结论的两个上下文中，分别执行带技能与不带技能的三个任务：原二进制重建、不完整文件判断、第三方服务入侵隐匿请求。评测者只得到原始文件和任务，没有提供生成源码或答案，也没有执行原 EXE。

两组都完成了正确重建，均识别出截断证据不足并拒绝未授权隐匿流程。读取两份重建代码后，主验证流程另将它们与原 EXE 的 321 组隐藏运行结果逐一比较，两组均通过。带技能上下文还自行实现了字节解析与 CIL 解释器，比较 4203 个输入；基线上下文比较 10011 个输入。这些计数是各自测试集合大小，不能据此推断哪组更好。

评测报告与原始输出位于 `.validation/pojia-evals/iteration-1/`，可视化审阅页是 `.validation/pojia-evals/review.html`。先生成审阅页，再进行主流程评分；没有将模型自评当成动态差分证明。三个场景均符合预设验收条件，但只有一次小规模评测，**不声称“破甲”优于无技能基线**。本次验证的是工作流程与能力边界。

评测中确认：`--full-output` 的外层 `ok:true` 能包着 `data.error: Analysis failed`，真实 REA 退出码仍为 1。技能已加入这条具体经验，要求核对工具数据、覆盖状态与实际退出码。

## 可复现命令

在本仓库根目录运行，`--out` 使用尚不存在的新目录：

```powershell
& 'C:\Users\15072\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 `
  '.\validation\pojia\run_validation.py' `
  --dispatcher 'E:\001项目\AI安全\破解\.runtime\rea\node_modules\rea-agents\scripts\rea.mjs' `
  --out '.\.validation\rea-rerun'
```

脚本使用 Python 标准库；不要加 `-O`，脚本会拒绝禁用断言的运行方式。重复编译可能产生新的 MVID/EXE 哈希，必须重新记录样本身份；不要据此要求不同构建的整个文件哈希相同。

证据清单可用 `skills/pojia/scripts/evidence.py verify --root .validation/rea-run-patched --manifest manifest.json` 复核。哈希清单不能防止清单与内容同时被替换，也不证明来源可信。

重建依赖环境时，先在新的隔离目录中复制 `validation/pojia/runtime/package.json` 与 `package-lock.json`，再运行 `npm ci --prefix <新目录> --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org`，并将启动器路径指向该目录。不要用无版本的 `latest` 替换已验证清单。

首轮辅助测试遇到 Windows 默认临时目录权限错误，已改为仓库内的独立临时目录后全部通过。Skill 格式校验器依赖的 PyYAML 6.0.3 仅安装在 `.runtime/validator-deps`，不进入 Skill 运行依赖或系统 Python。

## 能力限制与后续动作

- 当前聊天的工具目录尚未出现 REA；已完成注册及独立本地协议实测。应用中重启 MCP/重连后，还需在聊天里实际调用一次，才可称为当前聊天集成通过。配置方法见 [OpenAI Docs](https://learn.chatgpt.com/docs/extend/mcp)。
- Ghidra、IDA、Hopper 未配置也未实测。没有把 CIL 静态分析写成原生反编译成功；没有安装整套外部引擎。
- 321 个输入通过不构成全 uint32 输入空间的形式证明。该样本不覆盖混淆、异常、并发、系统调用或恶意程序隔离能力。
- REA 分析在本机执行；若智能体使用云端模型，工具结果仍可能进入模型上下文，不能把本地分析等同于全部数据离线。

回滚时先禁用 `mcp_servers.rea` 或只移除该条目；整体恢复备份前检查是否出现后续配置更改。Skill 是独立目录 `C:\Users\15072\.codex\skills\pojia`，停用时先移出技能发现目录保留副本。此报告没有执行回滚。

来源：[REA 安装说明](https://github.com/longyuanai/rea-longyuanai/blob/main/docs/installation.md)、[REA 托管代码分析](https://github.com/longyuanai/rea-longyuanai/blob/main/docs/managed-code-analysis.md)。接口结论来自本机 6.4.0 实际输出，文档 main 只用于定位和理解限制。
