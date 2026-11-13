# Claude Desktop 网关模式汉化（Linux）

可重复构建、注入和撤销的本地中文界面补丁。解决网关模式在 `en-US` 下跳过本地语言包的问题：在最终 Intl 消息提供层注入翻译，覆盖启动消息和实验文案的英文回退。

不包含 Claude 程序本体，不上传文案，不处理密钥或网关地址，不修改聊天正文、用户输入和模型回复。

## 支持范围

- Linux，官方 `.deb` 版 Claude Desktop，资源位于 `/usr/lib/claude-desktop/resources`。
- 当前已在 Ubuntu 24.04 x86_64、Claude Desktop **5.11492.2** 上构建、注入、撤销并重新注入。
- Python **3.11+**，Node.js **20.19+** 与 npm，sudo 或 pkexec。
- 不支持 Windows/macOS；ARM64 和其他发行版尚未实际测试。

脚本不绑定用户名或克隆目录。更新后会从本机现有程序重新构建；如果新版改变运行时结构，脚本会停止，不承诺所有未来版本自动兼容。

## 克隆后安装

先安装官方 Linux Claude Desktop，以及 Python、Node.js 和 npm。然后克隆本项目，在仓库目录执行：

```bash
bash install.sh
```

安装脚本通过锁定文件下载依赖，创建 `~/.local/bin/claude-zh` 符号链接，不会立即修改 Claude。请保留克隆的仓库目录。若当前终端的 PATH 不含 `~/.local/bin`，重新登录后生效，或使用完整路径。

想让命令直接安装到系统 PATH 中：

```bash
bash install.sh --system
```

此步骤需要 sudo；现有同名快捷命令会先保留。请以普通用户运行安装脚本。

## 一条命令汉化

先结束 Claude / Cowork 正在进行的工作，然后执行：

```bash
claude-zh
```

默认构建并通过 sudo 安装。完成后重新打开 Claude。

不安装快捷命令也能用：

```bash
bash ./claude-zh
```

若希望使用图形认证：

```bash
claude-zh apply --auth pkexec
```

## 更新和重新注入

官方更新会覆盖补丁。更新 Claude 后，再运行：

```bash
claude-zh
```

更新本工具：在克隆目录执行以下命令，再运行汉化命令。

```bash
git pull --ff-only
npm ci --ignore-scripts --no-audit --no-fund
```

翻译按英文原文匹配，不会直接套用含义已改变的旧消息 ID。新文案保留英文，并写入构建目录的 `untranslated.json`。补充翻译可修改 `ui-overrides.json`。

## 状态、构建与撤销

```bash
claude-zh status
claude-zh build
```

恢复注入前的官方资源（在仓库目录运行）：

```bash
sudo python3 -I ./inject.py restore --state "$HOME/.local/state/claude-gateway-zh"
```

如果官方资源已升级，撤销会拒绝用旧资源覆盖新版本。可改用系统包管理器重新安装官方 Claude 包。

构建、补丁状态和撤销所需的原程序资源保存在 `~/.local/state/claude-gateway-zh`；不是用户配置备份。仓库和发行压缩包不应包含 `.asar`、构建输出、会话、账号配置或密钥。

## 验证与限制

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm test
python3 -I -m unittest discover -s tests
```

每次构建额外校验 ICU 参数/标签/选择分支、修改后的 JavaScript 语法、ASAR 每个成员，以及从实际模块提取的最终 Intl provider。

5.11492.2 覆盖 41926/44218 条网关词条、51/51 条动态词条（映射到 52 个属性）、1129/1310 条原生桌面词条。新增文案、独立网页和代码中写死的字符串仍可能显示英文。

运行时保留原 locale，避免改变网关协议和语言协商；日期、数字及复数规则可能仍按英语处理。实际 Claude 登录窗口已确认可启动且显示中文；真实网关账号页面仍需完成网关配置后确认，离线 provider 测试不等于完整网关 UI 测试。

## 许可

工具代码为 MIT；翻译数据适用 CC BY-NC-SA 4.0，来源和归属见 [NOTICE.md](NOTICE.md)。本项目非 Anthropic 官方项目，Claude Desktop 的原有许可不变。
