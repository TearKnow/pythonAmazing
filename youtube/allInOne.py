#!/usr/bin/env python3
"""
交互式 YouTube 下载器 — 不用记任何参数，跟着提示走。

用法:
  python allInOne.py [URL]

流程:
  1. 输入链接（单个视频或播放列表，也可直接作为参数传入）
  2. 自动探测：是视频还是列表、有没有字幕、支持哪些画质
  3. 有字幕 → 问你要不要字幕 / 怎么处理（内嵌 or 单独文件）
  4. 列出可用画质 → 你选一个（列表则以第一个视频为参考）
  5. 确认后开始下载
"""

import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
YTDLP_OPTS = [
    "--cookies-from-browser", "firefox",
    "--js-runtimes", "node",
    "--remote-components", "ejs:github",
    "--socket-timeout", "30",   # 网络挂起时 30 秒报错，不无限卡住
]
# cookie 失效时降级用的最小选项（公开内容无需登录）
NO_COOKIE_OPTS = [
    "--js-runtimes", "node",
    "--remote-components", "ejs:github",
]

# 常见分辨率档位，用于兜底展示（探测不到时用）
FALLBACK_HEIGHTS = [2160, 1440, 1080, 720, 480, 360, 240, 144]


def normalize_url(input_str: str) -> str:
    """把视频 ID 或短链接转成完整 URL"""
    input_str = input_str.strip()
    if input_str.startswith("http"):
        return input_str
    if re.match(r'^[a-zA-Z0-9_-]{11}$', input_str):
        return f"https://www.youtube.com/watch?v={input_str}"
    if input_str.startswith("youtu.be/"):
        return f"https://{input_str}"
    if "youtube.com" in input_str or "youtu.be" in input_str:
        return f"https://{input_str}"
    return input_str


def run_capture(args):
    """运行 yt-dlp 并返回解析后的 stdout"""
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"命令失败: {' '.join(args)}")
    return json.loads(proc.stdout)


def probe(url):
    """探测 URL：类型、数量、字幕、画质。返回 dict。"""
    # 第一轮：flat 模式，判断是视频还是列表，并取出第一条
    # 失败（多为 Firefox cookie 失效）时去掉 cookie 重试一次
    try:
        info = run_capture([
            "yt-dlp", *YTDLP_OPTS,
            "-J", "--flat-playlist", "--playlist-items", "1", url,
        ])
    except RuntimeError:
        print("  ⚠️ 带 Firefox cookie 探测失败，改用无 cookie 重试…")
        info = run_capture([
            "yt-dlp", *NO_COOKIE_OPTS,
            "-J", "--flat-playlist", "--playlist-items", "1", url,
        ])
    kind = info.get("_type")
    is_playlist = kind in ("playlist", "multi_video")

    if is_playlist:
        entries = info.get("entries") or []
        # 有的列表第一个条目是 tab/子列表，没有 url，跳过找第一个真实视频
        first = next((e for e in entries if e.get("url")), None) or (entries[0] if entries else {})
        first_url = first.get("url")
        count = info.get("playlist_count") or len(entries)
        first_title = first.get("title", "")
    else:
        first_url = url
        count = 1
        first_title = info.get("title", "")

    # 第二轮：完整探测第一个视频（字幕 + 格式）；cookie 失败时同样降级重试
    full = {}
    if first_url:
        for _opts in (YTDLP_OPTS, NO_COOKIE_OPTS):
            try:
                full = run_capture(["yt-dlp", *_opts, "-J", first_url])
                break
            except RuntimeError:
                continue
    if not first_title:
        first_title = full.get("title", "")

    subs = full.get("subtitles") or {}
    auto_subs = full.get("automatic_captions") or {}
    sub_langs = sorted(set(list(subs.keys()) + list(auto_subs.keys())))
    sub_langs = [x for x in sub_langs if x != "live_chat"]

    heights = sorted(
        {f.get("height") for f in (full.get("formats") or []) if f.get("height")},
        reverse=True,
    )
    # 过滤掉 144p 以下的无意义小档位
    heights = [h for h in heights if h >= 144]

    # 各分辨率可用的容器格式（只关心 mp4 / webm，同高度 mp4 优先）
    ext_by_h = {}
    for f in full.get("formats") or []:
        h, e = f.get("height"), f.get("ext")
        if h and e in ("mp4", "webm"):
            ext_by_h.setdefault(h, set()).add(e)
    fmt_opts = []
    for h in sorted(ext_by_h, reverse=True):
        if h < 144:
            continue
        for e in ("mp4", "webm"):
            if e in ext_by_h[h]:
                fmt_opts.append((h, e))

    return {
        "is_playlist": is_playlist,
        "count": count,
        "first_title": first_title,
        "sub_langs": sub_langs,
        "heights": heights,
        "fmt_opts": fmt_opts,
    }


# 常见字幕语言（显示时优先展示，避免 200+ 种语言刷屏）
COMMON_LANGS = ["en", "zh-Hans", "zh-Hant", "ja", "ko", "es", "fr", "de", "ru", "pt"]


def fmt_langs(langs):
    """['en', 'zh-Hans', ...] → 精简展示（截断为常见语言 + 总数）"""
    if not langs:
        return "无"
    shown = [x for x in COMMON_LANGS if x in langs]
    total = len(langs)
    if len(shown) >= total:
        return ", ".join(langs)
    if shown:
        return f"{', '.join(shown)} 等 {total} 种语言"
    return f"{total} 种语言"


def default_langs(sub_langs):
    """自动选字幕语言：有 en 和 zh-Hans 就都带上，只有其一就只用它；
    都没有则取检测到的前两种，再没有就回退 en,zh-Hans。"""
    auto = [x for x in ("en", "zh-Hans") if x in sub_langs]
    if auto:
        return ",".join(auto)
    if sub_langs:
        return ",".join(sub_langs[:2])
    return "en,zh-Hans"


# ---------- 交互辅助 ----------

def ask(prompt, default=None):
    """input() 封装，处理空输入和 Ctrl+C"""
    try:
        val = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\n👋 已取消。")
        sys.exit(0)
    if not val.strip() and default is not None:
        return default
    return val.strip()


def ask_choice(prompt, options, default=0):
    """数字选择。options 是 [(值, 描述), ...]。返回所选值。"""
    print()
    for i, (_, desc) in enumerate(options):
        mark = " (默认)" if i == default else ""
        print(f"  {i}) {desc}{mark}")
    while True:
        val = ask(prompt, default=str(default))
        try:
            idx = int(val)
        except ValueError:  # 非数字（含 ² 这类 Unicode 数字）
            idx = -1
        if 0 <= idx < len(options):
            return options[idx][0]
        print(f"  ⚠️  请输入 0~{len(options) - 1} 之间的数字。")


# ---------- 菜单构造 ----------

# 下载类型选项（第一步）
MEDIA_OPTS = [
    ("video", "视频"),
    ("audio:mp3", "🎵 仅音频 · MP3（转码，通用）"),
    ("audio:m4a", "🎵 仅音频 · M4A（原始，不转码）"),
]
AUDIO_DESC = {
    "audio:mp3": "🎵 仅音频 · MP3（转码，通用）",
    "audio:m4a": "🎵 仅音频 · M4A（原始，不转码）",
}


def build_sub_menu(has_subs):
    """字幕处理选项（仅视频模式使用）"""
    options = [
        ("none", "不下载字幕"),
        ("embed", "下载字幕并内嵌到视频里（推荐）"),
        ("subs-only", "只下载字幕 SRT（不下载视频）"),
        ("separate", "下载视频 + 单独字幕文件（不内嵌，可配合 2_clean_srt.py）"),
    ]
    if not has_subs:
        options = [("none", "未检测到字幕，只下载视频")]
    return options


def build_quality_menu(fmt_opts):
    """画质选项：最佳 / 最佳 mp4 / 各分辨率×容器格式 / 自定义。
    fmt_opts: [(height, ext), ...]（已排序）或 []（探测失败，走兜底档位）"""
    options = [
        ("bestvideo+bestaudio/best", "最佳画质（自动选最高，可能是 webm）"),
    ]
    if any(ext == "mp4" for _, ext in fmt_opts):
        options.append((
            "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
            "最佳 mp4（H.264，最高 1080p）",
        ))
    if fmt_opts:
        for h, ext in fmt_opts:
            if ext == "mp4":
                fmt = f"bv*[height<={h}][ext=mp4]+ba[ext=m4a]/b[height<={h}][ext=mp4]"
            else:
                fmt = f"bv*[height<={h}][ext=webm]+ba[ext=webm]/b[height<={h}][ext=webm]"
            options.append((fmt, f"{h}p · {ext}"))
    else:
        # 探测不到具体格式时，按常见档位给出“任意容器”选项
        for h in FALLBACK_HEIGHTS:
            options.append((f"bv*[height<={h}]+ba/b[height<={h}]", f"{h}p 及以下"))
    options.append(("custom", "自定义格式串（如 299+140）"))
    return options


def pick_quality(fmt_opts):
    """询问画质，返回 (yt-dlp 格式串, 可读描述)"""
    options = build_quality_menu(fmt_opts)
    choice = ask_choice("请选择画质", options, default=0)
    if choice == "custom":
        fmt = ask("请输入格式串（如 299+140 或 bv*[height<=720][ext=mp4]+ba[ext=m4a]）: ")
        return fmt, fmt
    desc = next(d for v, d in options if v == choice)
    return choice, desc


# ---------- 下载 ----------

def run_ytdlp(*args):
    print()
    print("⬇️  开始下载...")
    cmd = ["yt-dlp"] + list(args)
    return subprocess.run(cmd).returncode


def download(url, *, is_playlist, sub_mode, langs, quality, media_type, items):
    """按所选配置拼 yt-dlp 参数并执行"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if is_playlist:
        out = os.path.join(
            OUTPUT_DIR,
            "%(playlist_title)s/%(playlist_index)03d_%(title)s [%(id)s].%(ext)s")
    else:
        out = os.path.join(OUTPUT_DIR, "%(title)s [%(id)s].%(ext)s")

    args = [*YTDLP_OPTS, "-o", out]
    if items:
        args += ["--playlist-items", items]

    if sub_mode == "subs-only":
        args += [
            "--write-auto-subs", "--write-subs",
            "--sub-langs", langs, "--convert-subs", "srt",
            "--skip-download", "-f", "sb0",
        ]
    elif media_type != "video":
        if media_type == "audio:mp3":
            args += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            # 只认 m4a，绝不 fallback 到 webm（没有 m4a 时 yt-dlp 会明确报错）
            args += ["-f", "ba[ext=m4a]/b[ext=m4a]"]
    else:
        args += ["-f", quality]
        if sub_mode == "embed":
            args += ["--write-auto-subs", "--write-subs",
                     "--sub-langs", langs, "--embed-subs"]
        elif sub_mode == "separate":
            args += ["--write-auto-subs", "--write-subs",
                     "--sub-langs", langs, "--convert-subs", "srt"]

    args.append(url)
    return run_ytdlp(*args)


# ---------- 主流程 ----------

def main():
    print("=" * 54)
    print("🎬  交互式 YouTube 下载器（不用记参数）")
    print("=" * 54)

    if len(sys.argv) > 1:
        url = normalize_url(sys.argv[1])
        print(f"链接: {url}")
    else:
        url = normalize_url(ask("\n请输入链接（单个视频或播放列表）: "))

    # ---- 探测 ----
    print("\n⏳  正在探测视频信息...")
    try:
        p = probe(url)
    except Exception as e:
        print(f"\n❌ 探测失败: {e}")
        print("   可能原因：链接无效 / 网络问题 / Firefox cookie 未登录。")
        sys.exit(1)

    kind = f"播放列表（共 {p['count']} 个视频）" if p["is_playlist"] else "单个视频"
    print("\n📺 探测结果")
    print(f"  类型: {kind}")
    if p["is_playlist"]:
        print(f"  第 1 个视频: {p['first_title'][:60]}")
    else:
        print(f"  标题: {p['first_title'][:60]}")
    print(f"  字幕: {fmt_langs(p['sub_langs'])}")
    print(f"  最高画质: {max(p['heights'])}p" if p["heights"] else "  最高画质: 未知")

    has_subs = bool(p["sub_langs"])

    # ---- ① 下载类型（视频 / 仅音频）----
    print("\n" + "-" * 54)
    print("📦 下载类型")
    print("-" * 54)
    media_type = ask_choice("请选择", MEDIA_OPTS, default=0)
    is_audio = media_type != "video"

    # ---- ② 字幕选择（仅视频模式；音频没有画面，不需要字幕）----
    if is_audio:
        sub_mode = "none"
        langs = "en,zh-Hans"
    else:
        print("\n" + "-" * 54)
        print("📝 字幕处理")
        print("-" * 54)
        if has_subs:
            print(f"检测到可用字幕: {fmt_langs(p['sub_langs'])}")
        sub_mode = ask_choice("请选择", build_sub_menu(has_subs), default=1 if has_subs else 0)
        # 字幕语言自动按检测结果定，无需手动输入
        if sub_mode != "none" and has_subs:
            langs = default_langs(p["sub_langs"])
            print(f"  → 字幕语言自动选为: {langs}")
        else:
            langs = "en,zh-Hans"

    # ---- ③ 画质选择（仅视频）----
    if is_audio:
        quality = None
        qual_desc = AUDIO_DESC[media_type]
    elif sub_mode == "subs-only":
        quality, qual_desc = None, None
        print("\n（只下载字幕，无需选择画质）")
    else:
        print("\n" + "-" * 54)
        print("📹 画质选择" + ("（以列表第一个视频为参考）" if p["is_playlist"] else ""))
        print("-" * 54)
        quality, qual_desc = pick_quality(p["fmt_opts"])

    # ---- 列表限量 ----
    items = None
    if p["is_playlist"] and sub_mode != "subs-only":
        val = ask("\n播放列表下载范围，回车=全部；如 1-5 / 1,3,7: ")
        items = val or None

    # ---- 确认 ----
    sub_desc = {
        "none": "不下载字幕",
        "embed": f"字幕内嵌到视频（{langs}）",
        "subs-only": f"只下载字幕 SRT（{langs}）",
        "separate": f"视频 + 单独字幕文件（{langs}）",
    }[sub_mode]
    if is_audio:
        sub_desc = "无（音频无字幕）"
    print("\n" + "=" * 54)
    print("📋 下载配置确认")
    print("=" * 54)
    print(f"  类型: {kind}")
    print(f"  字幕: {sub_desc}")
    if qual_desc:
        print(f"  画质: {qual_desc}")
    if items:
        print(f"  范围: 第 {items} 集")
    if is_audio:
        print("  ℹ️ 说明: 会先下载最佳音频流（可能是 webm），"
              "选 MP3 时自动转码并删除原 webm 文件")
    print(f"  输出: {OUTPUT_DIR}")
    if ask("\n开始下载?（回车=是，输入 n=取消）: ", "y").strip().lower() not in ("n", "no", "0"):
        sys.exit(download(url, is_playlist=p["is_playlist"], sub_mode=sub_mode,
                          langs=langs, quality=quality, media_type=media_type,
                          items=items))
    else:
        print("👋 已取消，什么也没下载。")


if __name__ == "__main__":
    main()
