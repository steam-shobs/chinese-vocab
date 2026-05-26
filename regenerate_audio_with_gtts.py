#!/usr/bin/env python3
"""
中国語単語練習ページ用 gTTS 音声一括生成スクリプト

このスクリプトは audio_manifest.csv を読み、各単語のMP3を
audio/unit1/001.mp3 のような既存のパスへ生成・上書きします。

使い方:
  cd chinese_vocab_pages
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install gTTS
  python regenerate_audio_with_gtts.py --limit 3 --overwrite
  python regenerate_audio_with_gtts.py --overwrite

注意:
  - gTTSはインターネット接続が必要です。
  - Google Cloud TTSとは違い、課金設定やAPIキーは不要です。
  - 非公式・小規模向けの方法なので、大量生成時は失敗することがあります。
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

try:
    from gtts import gTTS
    from gtts.lang import tts_langs
except ImportError:
    print(
        "ERROR: gTTS がインストールされていません。\n"
        "次を実行してください:\n"
        "  python -m pip install gTTS",
        file=sys.stderr,
    )
    raise


def read_manifest(manifest_path: Path) -> list[dict[str, str]]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"audio_manifest.csv が見つかりません: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError("audio_manifest.csv が空です。")

    required = {"unit", "number", "text", "audio"}
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(
            "audio_manifest.csv に必要な列がありません: "
            + ", ".join(sorted(missing))
        )

    return rows


def normalize_lang(lang: str) -> str:
    """
    gTTSのバージョン差に備えて、zh-CN / zh-cn / zh をゆるく扱う。
    """
    lang = lang.strip()
    available = tts_langs()

    if lang in available:
        return lang

    lower = lang.lower()
    if lower in available:
        return lower

    # 現行gTTSでは zh-CN が使えることが多い。
    # 古い環境では zh-cn または zh の場合がある。
    candidates = []
    if lower in {"zh-cn", "zh_cn", "cmn-cn", "cmn_cn"}:
        candidates = ["zh-CN", "zh-cn", "zh"]
    elif lower in {"zh-tw", "zh_tw"}:
        candidates = ["zh-TW", "zh-tw", "zh"]
    else:
        candidates = [lang, lower]

    for cand in candidates:
        if cand in available:
            return cand

    print("WARNING: 指定された言語コードが gTTS の一覧に見つかりません。")
    print(f"指定値: {lang}")
    print("ただし --nocheck 相当でそのまま試します。")
    return lang


def synthesize_one(
    text: str,
    output_path: Path,
    lang: str,
    tld: str,
    slow: bool,
    lang_check: bool,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # gTTSは内部でGoogle Translate TTSにアクセスするため、ここで通信が発生する。
    tts = gTTS(
        text=text,
        lang=lang,
        tld=tld,
        slow=slow,
        lang_check=lang_check,
    )

    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        tts.save(str(temp_path))
        if temp_path.stat().st_size == 0:
            raise RuntimeError("生成されたMP3が0バイトです。")
        temp_path.replace(output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="audio_manifest.csv から gTTS で中国語MP3を一括生成します。"
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="chinese_vocab_pages フォルダのパス。既定値は現在のフォルダ。",
    )
    parser.add_argument(
        "--manifest",
        default="audio_manifest.csv",
        help="音声対応表CSV。既定値は audio_manifest.csv。",
    )
    parser.add_argument(
        "--lang",
        default="zh-CN",
        help="gTTSの言語コード。普通話なら通常 zh-CN。うまくいかない場合は zh-cn または zh を試してください。",
    )
    parser.add_argument(
        "--tld",
        default="com",
        help="Google Translateのドメイン。通常は com。地域差を試すなら com.hk など。",
    )
    parser.add_argument(
        "--slow",
        action="store_true",
        help="ゆっくり読み上げる。単語練習には聞き取りやすいが、やや不自然な場合があります。",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="既存MP3を上書きする。指定しない場合、既存ファイルはスキップします。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="テスト用。最初のN件だけ生成。0なら全部。",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="1始まりの開始位置。途中から再開したいとき用。",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="各リクエスト間の待ち時間。ブロック回避のため既定値は0.5秒。",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="失敗時の再試行回数。",
    )
    parser.add_argument(
        "--no-lang-check",
        action="store_true",
        help="gTTS側の言語チェックを無効化します。",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir).expanduser().resolve()
    manifest_path = base_dir / args.manifest
    rows = read_manifest(manifest_path)

    if args.start < 1:
        raise ValueError("--start は1以上にしてください。")

    rows = rows[args.start - 1 :]
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    lang_check = not args.no_lang_check
    lang = args.lang if args.no_lang_check else normalize_lang(args.lang)

    total = len(rows)
    generated = 0
    skipped = 0
    failed: list[tuple[str, str, str]] = []

    print(f"base_dir: {base_dir}")
    print(f"manifest: {manifest_path}")
    print(f"lang: {lang}")
    print(f"tld: {args.tld}")
    print(f"slow: {args.slow}")
    print()

    for i, row in enumerate(rows, start=args.start):
        text = row["text"].strip()
        rel_audio = row["audio"].strip()
        output_path = base_dir / rel_audio

        if not text:
            print(f"[{i}] SKIP empty text")
            skipped += 1
            continue

        if output_path.exists() and not args.overwrite:
            print(f"[{i}] SKIP exists: {rel_audio}")
            skipped += 1
            continue

        print(f"[{i}] {text} -> {rel_audio}")

        last_error = None
        for attempt in range(1, args.retries + 1):
            try:
                synthesize_one(
                    text=text,
                    output_path=output_path,
                    lang=lang,
                    tld=args.tld,
                    slow=args.slow,
                    lang_check=lang_check,
                )
                generated += 1
                break
            except Exception as exc:
                last_error = exc
                print(f"    retry {attempt}/{args.retries} failed: {exc}")
                if attempt < args.retries:
                    time.sleep(max(1.0, args.sleep * attempt))
        else:
            failed.append((row.get("unit", ""), text, str(last_error)))

        if args.sleep > 0:
            time.sleep(args.sleep)

    print()
    print(f"Done. generated={generated}, skipped={skipped}, failed={len(failed)}, total={total}")

    if failed:
        fail_log = base_dir / "gtts_failed.txt"
        with fail_log.open("w", encoding="utf-8") as f:
            for unit, text, err in failed:
                f.write(f"{unit}\t{text}\t{err}\n")
        print(f"失敗ログを書き出しました: {fail_log}")
        print("一部失敗しました。時間を置いて、--start や --limit を使って再実行してください。")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
