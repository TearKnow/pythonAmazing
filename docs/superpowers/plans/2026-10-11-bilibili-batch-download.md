# B 站文件批量下载 Implementation Plan

> **For agentic workers:** 实现 `docs/superpowers/specs/2026-10-11-bilibili-batch-download-design.md`，改动仅限 `youtube/allInOne.py`。

**Goal:** 在 `allInOne.py` 增加「通过文件下载 B 站视频」：解析 ID 文件 → 问一次配置 → 无 cookie 依次下载 → 失败跳过并汇总。

**Architecture:** 入口加模式选择；批量分支独立函数；`download()` 增加可传入的 yt-dlp 基础选项（默认仍为 `YTDLP_OPTS`）。

**Tech Stack:** Python 3、yt-dlp、现有交互辅助函数。

---

### Task 1: 解析 + 批量流程 + 入口

修改 `youtube/allInOne.py`：

1. `parse_bilibili_ids` / `load_bilibili_ids_from_file`
2. `download(..., ytdlp_opts=None)`，默认 `YTDLP_OPTS`
3. 批量媒体菜单（无 book）；画质菜单始终提供最佳 mp4
4. `run_bilibili_batch()`：读文件 → 配置 → 循环下载 → 汇总
5. `main()` 开头模式选择

手动验证：默认路径解析 `bilibili.txt` 能抽出 BV；选取消不下载。
