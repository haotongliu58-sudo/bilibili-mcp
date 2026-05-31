# bilibili-mcp 设计文档

- 日期：2026-05-30
- 状态：已实现（v1，2026-05-31）。见下方「实现修订」
- 所属：MCP 路线图 M3（跳过 M2，详见决策记录）

## 实现修订（2026-05-31，实测后用户拍板）

实现 + 端到端实测发现：**B站已把字幕 / AI总结接口限制为登录用户**（游客调 `player/wbi/v2` 拿到的 `subtitle.subtitles` 恒为空；`get_ai_conclusion` 直接返回 `-101 账号未登录`）。这与原设计「不碰 SESSDATA、纯游客」硬冲突，而字幕正是杀手锏。

**用户决定：加可选 SESSDATA（默认仍游客）。**
- `get_video_info` / `search_videos`：纯游客，无需登录（实测直连秒回，代理绕过成功）。
- `get_video_subtitle`：需要用户自己的 `BILI_SESSDATA` cookie（环境变量，仅本机用、不上传）。未配置时返回友好提示，不报错。
- 实现：`bili._load_credential()` 从 `BILI_SESSDATA`(+可选 `BILI_BILI_JCT`/`BILI_BUVID3`/`BILI_DEDEUSERID`) 构建 Credential；`server.get_video_subtitle` 先查 `bili.has_credential()`。
- 风险心智：本地工具 + 用户自己 cookie + 自己机器 → 风险归用户自身，与「本地跑零风险」一致。
- ⚠️ 待验证：带真实 SESSDATA 的字幕抽取链路尚未端到端实跑（无 cookie），代码按库 verify 通过路径写好，待用户提供 cookie 后补验。

## 背景与目标

把"读取 B站公开数据"的能力包成 MCP server，让任意 AI 客户端（Claude/Cursor）的用户能让 AI 读取并分析 B站视频。属于 MCP 路线图的 M3（中文平台蓝海试水）。

**Why 选 B站不选小红书**：小红书反爬地狱（x-s 签名、设备指纹、频繁封号、签名算法常变）。B站走的是"内部 Web JSON API（半官方）"，反爬温和，且签名/反爬已有成熟社区库解决。

**Why 这是低风险**：
- 本地工具，不是托管 SaaS —— 别人用是用他自己机器、自己游客身份去抓，算力/法律/封号都不由作者承担。
- v1 只读公开数据、不登录、低频，不触碰个人隐私数据。
- 合规底线：公开读取 + 合理频率 + 自用，不做批量采集、不转卖 B站数据。

## 核心打法：瘦封装（M1 同款）

```
AI客户端 --MCP/stdio--> bilibili-mcp(本项目,~200行) --调用--> bilibili-api库 --HTTP直连--> B站
```

MCP 层只做翻译：收 MCP 调用 → 调成熟的 `bilibili-api`（Nemo2011/bilibili-api）库函数 → 把结果整理成 AI 好读的精简结构返回。**WBI 签名、cookie、风控重试全交给库，本项目不自己实现。**

参考资料：接口语义可查社区文档 `SocialSisterYi/bilibili-API-collect`。

## v1 工具范围（聚焦 MVP，3 个）

只做游客公开读取。后续 v1.1 再加 get_popular / get_user_videos / get_comments（后两个风控等级高，故延后）。

| 工具 | 入参 | 返回 |
|---|---|---|
| `get_video_info` | `bvid`（也接受完整视频 URL，自动提取 BV 号） | 标题、UP主、播放/点赞/投币、时长、简介、发布时间、分区、标签 |
| `get_video_subtitle` | `bvid`，可选 `lang`（默认中文）；可选 `with_timestamp`（默认 false） | 字幕全文（纯文本）。**无字幕时明确返回"该视频无字幕"而非报错** |
| `search_videos` | `keyword`，可选 `page`（默认 1）、`limit`（默认 10） | 命中视频列表：bvid、标题、UP主、播放量、时长 |

辅助函数：`_extract_bvid(s)` —— 从纯 BV 号或完整 URL 中提取 bvid。

杀手锏链路：`search_videos` → `get_video_subtitle` → AI 总结，即"让 Claude 看完并总结 B站视频"。

## 关键技术处理

### 代理绕过（这台机器必调，作者来处理）
- 问题：B站是国内站；本机 Clash Verge 系统代理（7897，境外节点）会让请求被甩到境外 → 慢/被 B站当异常。
- httpx 在 `trust_env=True` 下会从**环境变量**和 **Windows 系统代理（注册表）**两处读到代理，需同时挡住。
- 方案：
  - 进程启动时清掉 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY`（及小写）环境变量；
  - 把底层 httpx 设为 `trust_env=False`（确切注入方式对着**装好的 `bilibili-api` 版本**的设置 API 现查现确认，不预先写死）。
- 逃生口：环境变量 `BILI_USE_PROXY=1` 时改为走系统代理（给境外用户）。
- 默认行为：直连（适合作者 + 国内用户）。

### 游客身份
- 启动自动领 `buvid3`，不登录、不碰 SESSDATA。

### 限流处理
- 轻度延时；遇 `-412/-799/-352` 等风控码 → 友好报错（"被临时限流，稍后再试"），不静默崩溃。

### 输入容错
- `bvid` 参数同时接受 `BV1xx...` 和完整视频 URL。

## 项目结构（镜像 anime-sd-mcp）

```
D:\mcp\bilibili-mcp\
├── pyproject.toml      # mcp + bilibili-api-python; 入口 bilibili-mcp; [dev]=pytest
├── README.md           # 安装/客户端配置/工具表/演示
├── LICENSE (MIT)
├── .gitignore
├── .venv\              # 独立 venv，不污染其它环境
├── docs\superpowers\specs\  # 本设计文档
└── src\bilibili_mcp\
    ├── __init__.py     # __version__ = "0.1.0"
    └── server.py       # FastMCP + 3 工具 + _extract_bvid
```

## 测试策略（同 M1）

- **单元测试** `tests/test_server.py`：mock `bilibili-api` 返回，测解析/格式化/URL 提取/无字幕分支/风控错误处理。不需真联网、不需 GPU。
- **端到端**：用一个已知有字幕的公开 BVID 真跑一次，三个工具都通。**代理直连是端到端第一个验证点**（拿到标题秒回=直连成功）。

## 发布

- 公开 GitHub 仓库，**干净日常身份**（haotongliu58-sudo），通用工具无 NSFW，利于个人技术品牌。
- 仓库不出现任何关联到 NSFW bot 的内容（身份隔离）。
- git 走 Clash 代理 7897（已知坑）。
- 配套内容：小红书/B站发"我做了让 Claude 读 B站视频并总结的 MCP"。

## 非目标（明确不做）

- ❌ 登录态/SESSDATA、管理自己稿件、发评论点赞（涉账号风险，留 v2）。
- ❌ get_user_videos / get_comments（高风控，留 v1.1）。
- ❌ 无字幕视频的语音转写（工程量大一档，留后续）。
- ❌ 托管 SaaS / 批量采集（合规风险，明确不做）。
