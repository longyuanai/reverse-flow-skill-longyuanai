# REA 运行与复现

## 连接检查

1. 先看当前会话实际工具目录，选择需要的工具；名称和输入 schema 是权威。
2. 工具不可见时，检查 REA 可执行程序和版本，再检查当前 Codex 主机的 MCP 注册。不要读取或输出整个环境变量和配置文件里的认证信息。
3. 配置有服务器不代表当前聊天已加载它。配置变更后可能需要在应用中重启 MCP/重连；不要自行终止用户会话。
4. CLI 可用即可先做已授权的静态分析，明确记录通过哪个接口取得结果。

示意命令，使用实际的绝对路径：

```powershell
node <rea-package>/scripts/rea.mjs --version
node <rea-package>/scripts/rea.mjs doctor --client codex --json
node <rea-package>/scripts/rea.mjs inspect-managed-artifact <assembly> --json
node <rea-package>/scripts/rea.mjs inspect-managed-members <assembly> --json
```

`doctor` 是注册与环境检查，不是活跃聊天工具调用证明。没有 Ghidra/IDA 时，静态 .NET/JavaScript 路线仍可能可用；只报告实际成功的能力。

检查 CLI 退出码、MCP `isError`、工具数据中的 `error` 和覆盖状态。REA 6.4.0 的某些 CLI 输出模式可能在外层 `ok: true` 内携带分析失败；外层封装表示请求已处理，不代表样本分析成功。PowerShell 管道后写文件的命令退出码也不能替代先前的 REA `$LASTEXITCODE`。

## 版本与来源

- 同时记录仓库 URL/提交、npm 版本/锁文件/integrity、实际工具版本与平台。
- 仓库 main 可能超前于已发布包；不能把 main 文档中的参数套在旧版本上。先看本机 `--help` 或实际 MCP schema。
- 只安装 Skill 不会注册 MCP，也不会安装反编译引擎。
- 配置变更先预览，保留原文件备份，添加目标 MCP 条目并保留无关配置；用户已授权的安装流程不需要反复请求同一批准。
- 固定已验证版本；升级之后重新运行目标能力测试，而不是只看版本号。

## 已验证安装的查找

本技能不把某台电脑的用户名和运行目录写死。先从 `[mcp_servers.rea]` 的 `command`/`args` 找到实际启动器；若无注册，询问或定位用户明确安装的路径。不要自动全盘扫描。

历史安装报告只代表相应机器与版本；重新使用时以当前配置、工具目录及真实调用结果为准。

## 复现时的三个层次

分别记录：

1. 配置已写入且 TOML 能解析。
2. 本地独立 MCP 客户端能 initialize、列工具并对样本调用成功。
3. 当前 Codex 聊天实际调用到已注册工具。

没有完成第 3 层时，写“需重连后核验”，不要用第 2 层代替。
