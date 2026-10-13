#!/usr/bin/env python3
"""Build LibreTV subscription using verified checks only."""
import datetime
import json
import pathlib
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent


def write(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def endpoint_key(url):
    parsed = urllib.parse.urlsplit(url)
    return (parsed.netloc.lower(), parsed.path.rstrip('/'), parsed.query)


def main():
    report = json.loads((ROOT / 'check-results.json').read_text())
    valid = [r for r in report['results'] if r['status'] == 'verified']
    selected, merged = {}, []
    for result in valid:
        key = endpoint_key(result['url'])
        if key not in selected:
            selected[key] = result
        elif result['url'].startswith('https://') and selected[key]['url'].startswith('http://'):
            merged.append({**selected[key], 'reason': 'verified HTTPS equivalent retained'})
            selected[key] = result
        else:
            merged.append({**result, 'reason': 'verified equivalent retained'})
    sources = []
    for result in selected.values():
        item = {'name': result['name'], 'url': result['url']}
        sources.append(item)
    if not sources:
        raise SystemExit('No verified sources; refusing to produce an empty subscription')
    payload = {'name': 'LibreTV-SourceList', 'version': 2,
               'exportedAt': int(datetime.datetime.fromisoformat(report['checked_at']).timestamp() * 1000),
               'sources': sources, 'liveSources': []}
    write('sources.json', payload)
    write('default-sources.json', sources)
    excluded = [r for r in report['results'] if r['status'] != 'verified']
    write('excluded-sources.json', {'checked_at': report['checked_at'], 'results': excluded,
                                  'merged_verified_equivalents': merged, 'duplicates': report['duplicates']})
    checked = max(datetime.datetime.fromisoformat(r['checked_at']) for r in report['results'])
    local_time = checked.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M UTC+8')
    raw_url = 'https://raw.githubusercontent.com/ximishan/-LibreTV-api-source/main/sources.json'
    source_rows = '\n'.join(f"| {s['name']} | {s['url']} |" for s in sources)
    readme = f'''# LibreTV API 数据源

整理用户提供的 75 条影视 API 记录，提供经过接口检查的 LibreTV 数据源订阅。

最近检查：**{local_time}**。主订阅保留 **{len(sources)}** 个接口；原名单有 **{len(report['duplicates'])}** 条重复记录；通过检测的 HTTP/HTTPS 同接口合并 **{len(merged)}** 条；另有 **{len(excluded)}** 个接口未通过完整检查，已从主订阅排除。

## 使用方法

在当前 [LibreSpark/LibreTV](https://github.com/LibreSpark/LibreTV) 中打开 **设置 → 源管理 → 数据源订阅**，粘贴下面的地址并点击「订阅」：

```text
{raw_url}
```

这是一份数据源订阅（LibreTV-SourceList JSON），应在「数据源订阅」中使用。该文件不包含偏好设置和观看历史。不同旧版或分支的导入界面可能不同；没有订阅入口时，可从下面表格逐项添加 API。

部署者还可使用 `default-sources.json` 的数组内容作为 `DEFAULT_SOURCES` 环境变量，或配置：

```text
DEFAULT_SUBSCRIPTIONS=["{raw_url}"]
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
{source_rows}

## 手动复测

```bash
python3 check_sources.py
python3 build_sources.py
```

复测会更新检查报告，随后重新生成订阅与本说明。脚本仅检查接口，不自动推送 GitHub；本仓库也未启用定时检查。
'''
    (ROOT / 'README.md').write_text(readme)
    assert len(sources) <= 100
    assert len({s['url'] for s in sources}) == len(sources)
    print(json.dumps({'retained': len(sources), 'excluded': len(excluded),
                      'merged': len(merged), 'duplicates': len(report['duplicates'])}))


if __name__ == '__main__':
    main()
