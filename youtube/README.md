# YouTube 工具集

## 运行顺序

```
① 1_download.py  ──→  下载字幕 (SRT) 或 下载视频
② 2_clean_srt.py  ──→  清理字幕去重
```

---

## ① 1_download.py — 下载字幕 & 视频

封装 yt-dlp，无需手敲长命令。

```bash
# 查看可用字幕和视频格式
python 1_download.py list t5oSxg5iG44

# 下载中英文字幕 (SRT)
python 1_download.py sub t5oSxg5iG44

# 下载视频
python 1_download.py vid t5oSxg5iG44                  # 最佳画质
python 1_download.py vid t5oSxg5iG44 720p             # 指定分辨率
python 1_download.py vid t5oSxg5iG44 1080p --embed-subs  # 内嵌字幕
```

| 参数 | 说明 |
|------|------|
| `list` | 列出可用字幕语言 + 视频格式（等同于 `-F` + `--list-subs`） |
| `sub` | 下载自动生成字幕，默认 en + zh-Hans，自动转 SRT |
| `vid` | 下载视频，第二个参数可选：分辨率或格式号 |
| `--embed-subs` | （仅 `vid`）将字幕内嵌到视频文件中 |
| `--langs` | 字幕语言，如 `--langs "ja,ko"`（默认 `en,zh-Hans`） |
| `-o` | 输出目录 |

> ⚠️ **内嵌字幕后，播放器默认只显示一条字幕轨道。**
> 用 IINA / VLC 打开视频 → 右键 → 字幕 → 可切换到其他语言轨道。所有语言都在，只是需要手动切换。

### Cookie 与调试

`1_download.py` 已默认带上 `--cookies-from-browser firefox`，会从本机 Firefox 读取 YouTube 登录态（无需手动指定 Cookie 路径）。

**前提**：Firefox 已登录 YouTube 账号。

若下载失败（如「请登录确认你不是机器人」、年龄限制等），可先用 yt-dlp 原生命令排查 Cookie 是否读取成功：

```bash
# 用 verbose 查看实际读取的 cookies.sqlite 路径
yt-dlp --cookies-from-browser firefox --verbose "https://www.youtube.com/watch?v=VIDEO_ID"
```

将 `VIDEO_ID` 换成实际视频 ID 或完整 URL。成功时日志中会出现类似：

```
Extracting cookies from firefox
Extracting cookies from: "C:\Users\...\Mozilla\Firefox\Profiles\xxx.default\cookies.sqlite"
Extracted N cookies from firefox
```

| 场景 | 做法 |
|------|------|
| 排查 Cookie 是否生效 | 加上 `--verbose`，确认上述日志出现 |
| 仅列出格式、不下载 | 加 `-F` 或 `--list-subs --skip-download` |
| 多个 Firefox 配置 | `--cookies-from-browser firefox:配置名` |
| 不用 Firefox | 改用 `chrome` / `edge`，或 `--cookies cookies.txt` |

**注意**：Firefox 运行时可能锁定 `cookies.sqlite`，读不到时可先关闭 Firefox 再试。

---

## ② 2_clean_srt.py — SRT 清理去重

YouTube 自动字幕是逐词累积的，原始 SRT 充满重复帧和重叠文本。这个脚本清理为干净字幕。

```bash
# 处理单个文件
python 2_clean_srt.py "字幕文件.srt"

# 指定输出文件名
python 2_clean_srt.py "字幕文件.srt" "输出.srt"
```

| 处理 | 效果 |
|------|------|
| 过滤过渡帧 | 去掉 < 100ms 的重复帧 |
| 增量合并 | 下一条包含上一条 → 合并 |
| 重叠去重 | 上一条尾巴 = 下一条开头 → 去重拼接 |
| 智能断句 | 说话人切换 / 超时自动断句 |

原来 2400+ 条 → 清理后 200-300 条。

---

## 参考

- [yt-dlp-cheatsheet.md](yt-dlp-cheatsheet.md) — yt-dlp 命令行详细用法
