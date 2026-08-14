# YouTube 工具集

## 推荐用法（不用记参数）

```bash
python allInOne.py            # 输入链接，跟着提示选即可
python allInOne.py <URL>      # 或直接带链接
```

## 运行顺序

```
⓪ allInOne.py  ──→  交互式下载：输入链接 → 选字幕 → 选画质 → 下载（推荐）
① 1_download.py  ──→  命令行版：下载字幕 (SRT) 或 下载视频
② 2_clean_srt.py  ──→  清理字幕去重
```

---

## ⓪ allInOne.py — 交互式下载（推荐）

不用记任何参数，运行后一步步回答即可：

1. 输入链接（单个视频或播放列表均可）
2. 自动探测：是视频还是列表、有没有字幕、支持哪些画质
3. 选择下载类型：`视频` / `🎵 仅音频 · MP3（转码）` / `🎵 仅音频 · M4A（原始）`
   - 选了仅音频：跳过字幕和画质，直接到确认（音频没有字幕）
4. 有字幕 → 选择如何处理字幕
   - 视频：内嵌到视频 / 只下字幕 SRT / 视频+单独字幕文件 / 不下载
   - 字幕语言自动按检测结果：有 en 和 zh-Hans 就都带上，只有其一就只用它，无需手动输入
5. 视频模式选择画质与格式：`1080p · mp4`、`720p · webm` 等逐项列出（播放列表以第一个视频为参考）
6. 播放列表可选限量（如 `1-5`、`1,3,7`，回车=全部）
7. 回车确认开始下载（输入 `n` 才取消，防止手滑回车被取消）

```bash
python allInOne.py
python allInOne.py "https://www.youtube.com/watch?v=xxx"
python allInOne.py "https://www.youtube.com/playlist?list=xxx"
```

| 字幕选项 | 效果 |
|------|------|
| 不下载字幕 | 纯视频 |
| 内嵌到视频 | 字幕烧进视频文件，播放器可切换轨道 |
| 只下载字幕 SRT | 不下载视频，配合 2_clean_srt.py |
| 视频 + 单独字幕文件 | 视频和 SRT 分开放，便于后续清理 |

> 探测或下载时如果 Firefox cookie 失效，脚本会自动去掉 cookie 重试（公开内容无需登录）；画质、视频格式（mp4/webm）都可在流程中自由选择，字幕语言自动优先 en+zh-Hans。**注意**：YouTube 上 2160p/1440p 通常只有 webm（VP9/AV1），mp4（H.264）一般最高 1080p，选“最佳 mp4”即可拿到 H.264 的 mp4。

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

### 播放列表（Playlist）下载

`1_download.py` 没专门做播放列表，但 yt-dlp 对带 `list=` 的 URL 会**默认下载整个列表**，直接传播放列表 URL 就行。两条规则：

1. **URL 必须加引号**：`&` 会被 shell 拆掉，`list=` 后半截直接丢。
2. **文件名加集数序号**：`%(playlist_index)03d` → `001_`、`002_`…，否则顺序乱。

公开列表一般不用 cookie（Firefox cookie 失效时也别慌，去掉 `--cookies-from-browser firefox` 即可）。

```bash
# 只下字幕 (SRT)，不下载视频 —— 配合 2_clean_srt.py 用
yt-dlp --js-runtimes node \
  --write-auto-subs --write-subs \
  --sub-langs "en,zh-Hans" --convert-subs srt \
  --skip-download -f sb0 \
  -o "output/%(playlist_title)s/%(playlist_index)03d_%(title)s [%(id)s].%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID"

# 下视频（最佳画质 + 内嵌字幕）
yt-dlp --js-runtimes node \
  -f "bestvideo+bestaudio/best" \
  --embed-subs --write-auto-subs --sub-langs "en,zh-Hans" \
  -o "output/%(playlist_title)s/%(playlist_index)03d_%(title)s [%(id)s].%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID"

# 先试跑 1~2 集，确认没问题再去掉 --playlist-items
yt-dlp --js-runtimes node \
  --write-auto-subs --write-subs \
  --sub-langs "en,zh-Hans" --convert-subs srt \
  --skip-download -f sb0 \
  --playlist-items 1-2 \
  -o "output/%(playlist_title)s/%(playlist_index)03d_%(title)s [%(id)s].%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID"
```

其他常用参数：`--playlist-start N` / `--playlist-end N` / `--playlist-items 3-5` 限量下载。

### 控制画质 / 音频（替换下视频命令里的 `-f` 或加 `-x`）

| 需求 | 写法 |
|------|------|
| 限制最高分辨率（如 720p） | `-f "bv*[height<=720]+ba/b[height<=720]"` |
| 同上，更简写 | `-f "bestvideo+bestaudio/best" -S "res:720"` |
| 只要音频，不转码（原始 m4a） | `-f "ba/b"` |
| 音频转 MP3（最高音质 V0） | `-x --audio-format mp3 --audio-quality 0` |
| 音频限码率（≤128k） | `-f "bv*[height<=720]+ba[abr<=128]/b[height<=720]"` |

```bash
# 例子：下 720p 封顶的视频（含内嵌字幕）
yt-dlp --js-runtimes node \
  -f "bv*[height<=720]+ba/b[height<=720]" \
  --embed-subs --write-auto-subs --sub-langs "en,zh-Hans" \
  -o "output/%(playlist_title)s/%(playlist_index)03d_%(title)s [%(id)s].%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID"

# 例子：整个列表转 MP3 音频
yt-dlp --js-runtimes node -x --audio-format mp3 --audio-quality 0 \
  -o "output/%(playlist_title)s/%(playlist_index)03d_%(title)s.%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID"
```

> 说明：`bv*[height<=720]` = 不高于 720p 的视频流，`ba` = 最佳音频流，`+` 表示合并；`/b` 是兜底（合并不了就单文件）。单视频下载同样适用这些写法。

> ⚠️ 注意：输出路径相对于 `youtube/` 目录，在项目根目录跑时前面加 `youtube/`，如 `-o "youtube/output/..."`。

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
