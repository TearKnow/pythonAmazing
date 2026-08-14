#!/usr/bin/env python3
"""
YouTube 下载工具 — 封装 yt-dlp，免敲命令行参数。

用法:
  python 1_download.py list URL              列出可用字幕和视频格式
  python 1_download.py sub URL               下载字幕 (SRT) 到 ./output/
  python 1_download.py vid URL [fmt]         下载视频到 ./output/
  python 1_download.py playlist URL [fmt]    下载整个播放列表到 ./output/<列表名>/
      可选: --embed-subs  内嵌字幕到视频
            --subs-only   只下载字幕 (SRT)
            --audio       转 MP3 音频
            --start/--end/--items   播放列表限量下载
            --langs        字幕语言 (默认: en,zh-Hans)
            -o             输出目录

示例:
  python 1_download.py vid t5oSxg5iG44 720p --embed-subs
  python 1_download.py playlist <URL> 720p          # 播放列表 720p
  python 1_download.py playlist <URL> --subs-only   # 只下列表字幕
  python 1_download.py playlist <URL> --items 3-5   # 只下第 3~5 集
"""

import sys
import os
import subprocess
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
YTDLP_OPTS = [
    "--cookies-from-browser", "firefox",
    "--js-runtimes", "node",
    "--remote-components", "ejs:github",
]


def normalize_url(input_str: str) -> str:
    """把视频 ID 或短链接转成完整 URL"""
    import re
    # 已经是完整 URL
    if input_str.startswith("http"):
        return input_str
    # 纯视频 ID（11 位字符）或 youtu.be/xxx 短格式
    if re.match(r'^[a-zA-Z0-9_-]{11}$', input_str):
        return f"https://www.youtube.com/watch?v={input_str}"
    # 可能是 youtu.be/xxx 不带协议
    if input_str.startswith("youtu.be/"):
        return f"https://{input_str}"
    # 可能是 youtube.com/watch?v=xxx 不带协议
    if "youtube.com" in input_str or "youtu.be" in input_str:
        return f"https://{input_str}"
    return input_str


def resolve_fmt(fmt):
    """把 '720p'/'1080p' 转成 yt-dlp 格式串，其余原样返回（默认最佳画质）"""
    import re
    if fmt is None:
        return "bestvideo+bestaudio/best"
    m = re.match(r'^(\d{3,4})p$', fmt)
    if m:
        h = m.group(1)
        return f"bv*[height<={h}]+ba/b[height<={h}]"
    return fmt


def run_ytdlp(*args):
    """运行 yt-dlp，实时输出到终端"""
    cmd = ["yt-dlp"] + list(args)
    return subprocess.run(cmd).returncode


def cmd_list(url):
    """列出字幕 + 视频格式"""
    print("=" * 50)
    print("📋 可用字幕")
    print("=" * 50)
    run_ytdlp(*YTDLP_OPTS, "--list-subs", "--skip-download", url)

    print()
    print("=" * 50)
    print("📹 可用视频格式")
    print("=" * 50)
    run_ytdlp(*YTDLP_OPTS, "-F", url)


def cmd_sub(url, langs="en,zh-Hans", output_dir=None):
    """下载字幕为 SRT"""
    out_dir = output_dir or OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"%(title)s [%(id)s].%(ext)s")
    return run_ytdlp(
        *YTDLP_OPTS,
        "--write-auto-subs",    # 自动生成字幕
        "--write-subs",          # 人工上传字幕
        "--sub-langs", langs,
        "--convert-subs", "srt",
        "--skip-download",
        "-f", "sb0",
        "-o", out,
        url,
    )


def cmd_vid(url, fmt=None, output_dir=None, embed_subs=False, langs="en,zh-Hans"):
    """下载视频，可选内嵌字幕"""
    out_dir = output_dir or OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"%(title)s [%(id)s].%(ext)s")

    args = [*YTDLP_OPTS, "-o", out]
    if fmt:
        args += ["-f", fmt]
    if embed_subs:
        args += [
            "--write-auto-subs",   # 自动生成字幕
            "--write-subs",         # 人工上传字幕
            "--sub-langs", langs,
            "--embed-subs",
        ]
    args.append(url)
    return run_ytdlp(*args)


def cmd_playlist(url, fmt=None, output_dir=None, mode="video",
                 langs="en,zh-Hans", start=None, end=None, items=None,
                 embed_subs=False, audio_format="mp3"):
    """下载整个播放列表：按列表名分目录，文件名带集数序号"""
    out_dir = output_dir or OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(
        out_dir,
        f"%(playlist_title)s/%(playlist_index)03d_%(title)s [%(id)s].%(ext)s")

    args = [*YTDLP_OPTS, "-o", out]
    if start:
        args += ["--playlist-start", str(start)]
    if end:
        args += ["--playlist-end", str(end)]
    if items:
        args += ["--playlist-items", items]

    if mode == "sub":
        args += [
            "--write-auto-subs",   # 自动生成字幕
            "--write-subs",         # 人工上传字幕
            "--sub-langs", langs,
            "--convert-subs", "srt",
            "--skip-download",
            "-f", "sb0",
        ]
    elif mode == "audio":
        args += ["-x", "--audio-format", audio_format, "--audio-quality", "0"]
    else:  # video
        args += ["-f", resolve_fmt(fmt)]
        if embed_subs:
            args += [
                "--write-auto-subs",   # 自动生成字幕
                "--write-subs",         # 人工上传字幕
                "--sub-langs", langs,
                "--embed-subs",
            ]
    args.append(url)
    return run_ytdlp(*args)


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 下载工具（免敲 yt-dlp 命令行）",
        epilog="""
示例:
  python 1_download.py list t5oSxg5iG44                     查看字幕和格式
  python 1_download.py sub  t5oSxg5iG44                     下载中英字幕
  python 1_download.py vid  t5oSxg5iG44                     下载最佳画质
  python 1_download.py vid  t5oSxg5iG44 720p                下载 720p
  python 1_download.py vid  t5oSxg5iG44 299+140             手动指定格式组合
  python 1_download.py vid  t5oSxg5iG44 1080p --embed-subs  下载 1080p + 内嵌字幕
  python 1_download.py playlist <URL> 720p                  播放列表 720p
  python 1_download.py playlist <URL> --subs-only           只下列表字幕
  python 1_download.py playlist <URL> --audio               列表转 MP3
  python 1_download.py playlist <URL> --items 3-5           只下第 3~5 集
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("action", choices=["list", "sub", "vid", "playlist"],
                        help="list: 查看信息 | sub: 下载字幕 | vid: 下载视频 | playlist: 下载播放列表")
    parser.add_argument("url", help="YouTube 视频 URL / ID / 播放列表 URL")
    parser.add_argument("fmt", nargs="?", default=None,
                        help='格式: "720p", "1080p", "299+140" 等')
    parser.add_argument("--langs", default="en,zh-Hans",
                        help="字幕语言 (默认: en,zh-Hans)")
    parser.add_argument("-o", "--output", default=None,
                        help="输出目录")
    parser.add_argument("--embed-subs", action="store_true",
                        help="下载视频时内嵌字幕")
    parser.add_argument("--subs-only", action="store_true",
                        help="(playlist) 只下载字幕，不下载视频")
    parser.add_argument("--audio", action="store_true",
                        help="(playlist) 转音频，不下载视频")
    parser.add_argument("--audio-format", default="mp3",
                        help="(playlist --audio) 音频格式 (默认: mp3)")
    parser.add_argument("--start", type=int, default=None,
                        help="(playlist) 从第几集开始")
    parser.add_argument("--end", type=int, default=None,
                        help="(playlist) 到第几集结束")
    parser.add_argument("--items", default=None,
                        help='(playlist) 指定集数，如 "3-5" 或 "1,3,7"')

    args = parser.parse_args()

    if args.action == "list":
        sys.exit(cmd_list(normalize_url(args.url)))
    elif args.action == "sub":
        sys.exit(cmd_sub(normalize_url(args.url), args.langs, args.output))
    elif args.action == "vid":
        sys.exit(cmd_vid(normalize_url(args.url), args.fmt, args.output,
                         args.embed_subs, args.langs))
    elif args.action == "playlist":
        if args.subs_only:
            mode = "sub"
        elif args.audio:
            mode = "audio"
        else:
            mode = "video"
        sys.exit(cmd_playlist(
            normalize_url(args.url), args.fmt, args.output,
            mode, args.langs, args.start, args.end, args.items,
            args.embed_subs, args.audio_format))


if __name__ == "__main__":
    main()
