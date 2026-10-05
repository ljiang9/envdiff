#!/usr/bin/env python3
"""envdiff - 比较两个 .env 文件的差异。

值默认打码（只显示长度），因为 diff 输出常被粘进工单/聊天窗口，
一不留神就会泄露密钥。用 --show-values 显式要求时才显示原文。
"""

from __future__ import annotations

import argparse
import json
import re
import sys

VERSION = "0.1.0"

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def strip_comment(value: str) -> str:
    """去掉行尾注释。引号内的 # 不是注释。"""
    out = []
    quote: str | None = None
    i = 0
    while i < len(value):
        ch = value[i]
        if quote:
            if ch == "\\" and i + 1 < len(value):
                out.append(ch)
                out.append(value[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            out.append(ch)
        else:
            if ch in ("'", '"'):
                quote = ch
                out.append(ch)
            elif ch == "#":
                break
            else:
                out.append(ch)
        i += 1
    return "".join(out).rstrip()


def unquote(value: str) -> str:
    """去掉一层引号，处理双引号内的常见转义。"""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == '"':
            inner = (
                inner.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )
        return inner
    return value


def parse_env(path: str) -> tuple[dict[str, str], list[str]]:
    """解析 .env 文件。返回 (键值字典, 警告列表)。

    容忍坏行：只记警告，不崩溃。多行值（引号跨行）不支持，
    遇到未闭合引号会产生警告并按单行处理。
    """
    data: dict[str, str] = {}
    warnings: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" not in line:
                warnings.append(f"{path}:{lineno}: 忽略无法解析的行：{line[:60]}")
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if not KEY_RE.match(key):
                warnings.append(f"{path}:{lineno}: 键名不合法，已跳过：{key[:60]}")
                continue
            value = unquote(strip_comment(value))
            data[key] = value
    return data, warnings


def mask(value: str) -> str:
    return f"<{len(value)} 字符>"


def diff_envs(
    a: dict[str, str], b: dict[str, str], ignore: set[str]
) -> list[tuple[str, str, str, str]]:
    """返回 [(op, key, old, new)]。op ∈ {+, -, ~}。"""
    rows: list[tuple[str, str, str, str]] = []
    for key in sorted(set(a) | set(b)):
        if key in ignore:
            continue
        in_a, in_b = key in a, key in b
        if in_a and not in_b:
            rows.append(("-", key, a[key], ""))
        elif in_b and not in_a:
            rows.append(("+", key, "", b[key]))
        elif a[key] != b[key]:
            rows.append(("~", key, a[key], b[key]))
    return rows


def print_table(rows: list[tuple[str, str, str, str]], show_values: bool) -> None:
    if not rows:
        print("两个文件完全一致。")
        return
    for op, key, old, new in rows:
        if op == "+":
            val = new if show_values else mask(new)
            print(f"+ {key} = {val}    （新增）")
        elif op == "-":
            val = old if show_values else mask(old)
            print(f"- {key} = {val}    （删除）")
        else:
            o = old if show_values else mask(old)
            n = new if show_values else mask(new)
            print(f"~ {key}: {o} -> {n}    （变更）")
    print(f"\n共 {len(rows)} 处差异。")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="envdiff",
        description="比较两个 .env 文件的差异（值默认打码防泄漏）。",
    )
    parser.add_argument("--version", action="version", version=f"envdiff {VERSION}")
    parser.add_argument("file_a", help="旧的 .env 文件")
    parser.add_argument("file_b", help="新的 .env 文件")
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="显示值的原文（默认只显示长度，防止密钥泄漏）",
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        metavar="KEY",
        help="忽略这些键",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    try:
        a, wa = parse_env(args.file_a)
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: 无法读取 {args.file_a}：{e}", file=sys.stderr)
        return 2
    try:
        b, wb = parse_env(args.file_b)
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: 无法读取 {args.file_b}：{e}", file=sys.stderr)
        return 2

    for w in wa + wb:
        print(f"警告：{w}", file=sys.stderr)

    rows = diff_envs(a, b, set(args.ignore))

    if args.json:
        print(
            json.dumps(
                {
                    "identical": not rows,
                    "differences": [
                        {
                            "op": {"+": "added", "-": "removed", "~": "changed"}[op],
                            "key": key,
                            "old": old if args.show_values else None,
                            "old_length": len(old),
                            "new": new if args.show_values else None,
                            "new_length": len(new),
                        }
                        for op, key, old, new in rows
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_table(rows, args.show_values)

    return 0 if not rows else 1


if __name__ == "__main__":
    sys.exit(main())
