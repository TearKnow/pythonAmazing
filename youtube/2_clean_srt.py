#!/usr/bin/env python3
"""
清理 YouTube 自动生成 SRT 字幕中的重复/累积片段。

YouTube 自动字幕是"增量累积"模式，每条字幕包含之前的所有文本再加新词，
导致大量重复。此脚本将其合并为干净的逐句字幕。
"""

import re
import sys
import os


def parse_srt(filepath: str) -> list[dict]:
    """解析 SRT 文件，返回条目列表 [{index, start, end, text}]"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    # SRT 格式: 序号\n时间范围\n文本\n\n
    pattern = re.compile(
        r'(\d+)\n'
        r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n'
        r'(.*?)\n\s*\n',
        re.DOTALL
    )

    entries = []
    for m in pattern.finditer(content):
        entries.append({
            'index': int(m.group(1)),
            'start': m.group(2),
            'end': m.group(3),
            'text': m.group(4).strip().replace('\n', ' '),
        })
    return entries


def time_to_ms(t: str) -> int:
    """将 SRT 时间戳转为毫秒"""
    h, m, s = t.split(':')
    sec, ms = s.split(',')
    return int(h) * 3600000 + int(m) * 60000 + int(sec) * 1000 + int(ms)


def ms_to_time(ms: int) -> str:
    """毫秒转回 SRT 时间戳"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    milli = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def find_overlap(a: str, b: str) -> int:
    """
    找到 a 的尾部 与 b 的头部 的最长重叠字符数。
    只在空白边界处截断，避免切断单词。
    """
    max_len = min(len(a), len(b))
    # 从大到小找，优先在单词边界处
    for length in range(max_len, 2, -1):
        if a[-length:] == b[:length]:
            # 必须对齐单词边界
            if a[-length - 1].isspace() or a[-length - 1] in '.!?…,;:':
                return length
    return 0


def is_sentence_end(text: str) -> bool:
    """检查文本是否以句子结束符结尾"""
    return text.rstrip().endswith(('.', '!', '?', '…', '."', '!"', '?"',
                                   '。', '！', '？'))


def is_new_thought(next_text: str) -> bool:
    """检查是否明显是新话题/新句子（不应合并）"""
    # 说话人切换
    if next_text.startswith('>>'):
        return True
    # 以大写字母开头且前一句已结束 = 新句子
    return False


def trim_overlap_with_prev(prev_text: str, new_text: str) -> str:
    """
    从 new_text 开头去掉与 prev_text 尾部重叠的部分。
    例如 prev="...China really is.", new="is. >> We are about..." → ">> We are about..."
         prev="...领先多少 。", new="。 我们即将开始..." → "我们即将开始..."
    """
    max_len = min(len(prev_text), len(new_text))
    for length in range(max_len, 0, -1):
        suffix = prev_text[-length:]
        if suffix == new_text[:length]:
            if length <= 1:
                # 单字重叠：只去除纯标点
                if suffix in '.!?。，,;:…、':
                    return new_text[length:].lstrip()
                # 单字非标点不处理（避免过度修剪）
                return new_text
            # 多字重叠：检查单词/字边界
            if length < len(prev_text):
                boundary_char = prev_text[-length - 1]
                if not (boundary_char.isspace() or boundary_char in '.!?。，,;:…、'):
                    continue
            return new_text[length:].lstrip()
    return new_text


def clean_entries(entries: list[dict], min_duration_ms: int = 100,
                  max_group_duration_ms: int = 15000) -> list[dict]:
    """
    智能清理 YouTube 自动字幕：
    1. 过滤掉极短（< min_duration_ms）的过渡帧
    2. 增量累积合并（next 完全包含 current）
    3. 首尾重叠去重合并：
       - 遇到句子结束 + 说话人切换（>>）时断句
       - 合并时长超过上限且遇到句子结束时断句
       - 断句时自动剪掉新条目开头的重叠文字
    """
    # 第一步：过滤过渡帧
    filtered = []
    for entry in entries:
        start_ms = time_to_ms(entry['start'])
        end_ms = time_to_ms(entry['end'])
        if end_ms - start_ms >= min_duration_ms:
            filtered.append(entry)

    if not filtered:
        return []

    # 第二步：智能合并
    cleaned = []
    current = {
        'start': filtered[0]['start'],
        'end': filtered[0]['end'],
        'text': filtered[0]['text'],
    }

    def start_new(prev, next_entry):
        """开始新条目，剪掉与上一条的重叠尾巴"""
        text = trim_overlap_with_prev(prev['text'], next_entry['text'])
        return {
            'start': next_entry['start'],
            'end': next_entry['end'],
            'text': text,
        }

    for i in range(1, len(filtered)):
        next_entry = filtered[i]
        next_text = next_entry['text']

        group_start = time_to_ms(current['start'])
        group_end = time_to_ms(next_entry['end'])
        group_duration = group_end - group_start

        # --- 不合并的条件 ---

        # 1. 前一句已完整结束 且 下一句切换说话人
        if is_sentence_end(current['text']) and next_text.startswith('>>'):
            cleaned.append(current)
            current = start_new(current, next_entry)
            continue

        # 2. 合并组太长 → 强制断句
        #    a) 遇到句子结束：自然断句
        #    b) 超过 2 倍上限：硬断句（避免单条字幕过长）
        too_long = group_duration > max_group_duration_ms
        way_too_long = group_duration > max_group_duration_ms * 2
        if too_long and is_sentence_end(current['text']):
            cleaned.append(current)
            current = start_new(current, next_entry)
            continue
        elif way_too_long:
            cleaned.append(current)
            current = start_new(current, next_entry)
            continue

        # --- 合并逻辑 ---

        # 情况1: next 完全包含在 current 中 → 跳过
        if next_text.strip() in current['text']:
            current['end'] = next_entry['end']
            continue

        # 情况2: current 完全包含在 next 中 → 增量累积
        if current['text'].strip() in next_text:
            current['text'] = next_text
            current['end'] = next_entry['end']
            continue

        # 情况3: 首尾重叠 → 去重拼接
        overlap = find_overlap(current['text'], next_text)
        if overlap > 3:
            current['text'] = current['text'] + next_text[overlap:]
            current['end'] = next_entry['end']
            continue

        # 情况4: 无法合并 → 保存当前，开始新的
        cleaned.append(current)
        current = start_new(current, next_entry)

    cleaned.append(current)
    return cleaned


def write_srt(entries: list[dict], filepath: str):
    """输出 SRT 文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(entries, 1):
            f.write(f"{i}\n")
            f.write(f"{entry['start']} --> {entry['end']}\n")
            f.write(f"{entry['text']}\n\n")


def main():
    if len(sys.argv) < 2:
        print("用法: python clean_srt.py <input.srt> [output.srt]")
        print("     如果不指定输出文件，默认在原文件名后加 _clean.srt")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_clean{ext}"

    entries = parse_srt(input_path)
    print(f"📖 原始条目: {len(entries)}")

    cleaned = clean_entries(entries)
    print(f"🧹 清理后:   {len(cleaned)} (减少了 {len(entries) - len(cleaned)} 条)")

    write_srt(cleaned, output_path)
    print(f"✅ 已保存: {output_path}")


if __name__ == "__main__":
    main()
