# 翻译与许可说明

本工具在用户本机修改 Claude Desktop 的界面资源，不包含应用程序本体，也不改变应用代码的原有许可。仅用于本地界面汉化；不改变网关、密钥、模型、账号或对话正文。

translations.json 来源于先前整理的 Claude Desktop 中文词典（按英文原文索引，合并并去重）。该词典结合应用自带翻译、ICERainbow666/claude-desktop-zh-cn 的社区词库以及先前的本地机器翻译和术语修订。社区词库按其声明的 CC BY-NC-SA 4.0 使用；本工具合并的翻译数据继续遵循该许可，不因仓库代码采用 MIT 而改变。

- 社区项目：https://github.com/ICERainbow666/claude-desktop-zh-cn
- CC BY-NC-SA 4.0：https://creativecommons.org/licenses/by-nc-sa/4.0/

本工具新增的中文词条见 ui-overrides.json。机器翻译可能不自然，新增版本可能保留部分英文，详见每次构建生成的 untranslated.json。脚本不会向外部翻译服务发送应用文案或用户数据。
