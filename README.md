# LibreTV API 数据源

整理用户提供的 75 条影视 API 记录，提供经过接口检查的 LibreTV 数据源订阅。

最近检查：**2026-10-13 16:26 UTC+8**。主订阅保留 **17** 个接口；原名单有 **3** 条重复记录；通过检测的 HTTP/HTTPS 同接口合并 **1** 条；另有 **54** 个接口未通过完整检查，已从主订阅排除。

## 使用方法

在当前 [LibreSpark/LibreTV](https://github.com/LibreSpark/LibreTV) 中打开 **设置 → 源管理 → 数据源订阅**，粘贴下面的地址并点击「订阅」：

```text
https://raw.githubusercontent.com/ximishan/-LibreTV-api-source/main/sources.json
```

这是一份数据源订阅（LibreTV-SourceList JSON），应在「数据源订阅」中使用。该文件不包含偏好设置和观看历史。不同旧版或分支的导入界面可能不同；没有订阅入口时，可从下面表格逐项添加 API。

部署者还可使用 `default-sources.json` 的数组内容作为 `DEFAULT_SOURCES` 环境变量，或配置：

```text
DEFAULT_SUBSCRIPTIONS=["https://raw.githubusercontent.com/ximishan/-LibreTV-api-source/main/sources.json"]
```

## 文件

| 文件 | 用途 |
| --- | --- |
| [sources.json](sources.json) | 通过检查的主订阅，包含 sources 数组与空 liveSources 数组 |
| [default-sources.json](default-sources.json) | 相同数据源的裸数组，供 DEFAULT_SOURCES 使用 |
| [candidates.txt](candidates.txt) | 原始 75 条记录，保留 HTTP/HTTPS、不同路径和原始名称；仅去掉「点播」装饰 |
| [check-results.json](check-results.json) | 72 个唯一接口的检查时间、HTTP 状态、各阶段结果及失败接口的复测记录 |
| [excluded-sources.json](excluded-sources.json) | 排除、合并和重复记录，方便复查与恢复 |
| [check_sources.py](check_sources.py) | 接口检测脚本（Python 3 + curl，无第三方依赖） |
| [build_sources.py](build_sources.py) | 根据检查报告生成订阅文件 |

## 检查与清理规则

1. 地址去除末尾斜杠，完全相同的接口去重。不同路径保留；同主机同路径的 HTTP/HTTPS 两者均通过时优先 HTTPS。名称相同不作为合并依据。
2. `ac=list` 必须返回 Apple CMS JSON 列表，并含有效 `vod_id` 和 `vod_name`。
3. 取列表中的最多 3 个 ID 请求 `ac=detail&ids=...`，至少一个样本需要有带 `.m3u8` 的 HTTP(S) 分集播放地址。
4. 取样本标题片段请求 `ac=detail&wd=...`，必须返回有效搜索结果。
5. 初次未通过的接口再测一次；超时、403、5xx 等只说明本次未能验证，不能据此认定永久失效。404、XML 或普通网页等响应也记录在报告中，供复核。
6. 主订阅只收录三项都通过的接口。排除的原始记录保留在仓库中。

这是 API 响应检查，**没有实播或逐个验证视频流**。数据源可能随时变化，实际可用性取决于部署服务器的网络。通过检查不代表全站所有内容可播放。

格式依据：[source-list.ts](https://github.com/LibreSpark/LibreTV/blob/a24ad336a3f7c8a16ca93d1f1198e08ac6b7e943/src/lib/source-list.ts)、[cms-parser.ts](https://github.com/LibreSpark/LibreTV/blob/a24ad336a3f7c8a16ca93d1f1198e08ac6b7e943/src/lib/cms-parser.ts)。

## 保留接口

| 名称 | API 地址 |
| --- | --- |
| 紅牛資源 | http://hongniuzy2.com/api.php/provide/vod/from/hnm3u8 |
| 量子資源 | http://cj.lziapi.com/api.php/provide/vod/from/lzm3u8 |
| 金鹰资源 | http://jyzyapi.com/provide/vod/from/jinyingm3u8 |
| 光速资源 | http://api.guangsuapi.com/api.php/provide/vod/from/gsm3u8 |
| U酷 | https://api.ukuapi.com/api.php/provide/vod |
| 艾旦影视 | http://lovedan.net/api.php/provide/vod |
| 360 | https://360zy.com/api.php/provide/vod |
| 豪华 | https://hhzyapi.com/api.php/provide/vod |
| 极速 | https://jszyapi.com/api.php/provide/vod |
| 非凡 | http://cj.ffzyapi.com/api.php/provide/vod |
| 量子 | https://cj.lziapi.com/api.php/provide/vod |
| 红牛 | https://www.hongniuzy2.com/api.php/provide/vod |
| 虎牙 | https://www.huyaapi.com/api.php/provide/vod |
| 飘零 | https://p2100.net/api.php/provide/vod |
| 魔都 | https://caiji.moduapi.cc/api.php/provide/vod |
| 最大 | http://zuidazy.me/api.php/provide/vod |
| 新浪 | https://api.xinlangapi.com/xinlangapi.php/provide/vod |

## 手动复测

```bash
python3 check_sources.py
python3 build_sources.py
```

复测会更新检查报告，随后重新生成订阅与本说明。脚本仅检查接口，不自动推送 GitHub；本仓库也未启用定时检查。
