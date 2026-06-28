# gTTSで中国語MP3を生成する方法

このフォルダのHTMLは、`audio/` 内のMP3を再生する方式になっています。
`regenerate_audio_with_gtts.py` を使うと、`audio_manifest.csv` に基づいてMP3を一括生成・上書きできます。

## まず必要なもの

- Python 3
- インターネット接続
- gTTSライブラリ

Google Cloud TTSとは違い、APIキーやGoogle Cloudの課金設定は不要です。

## Macでの実行例

ターミナルで、この `chinese_vocab_pages` フォルダに移動してから実行します。

```bash
cd chinese_vocab_pages

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install gTTS
```

まず3件だけテストします。

```bash
python regenerate_audio_with_gtts.py --limit 3 --overwrite
```

問題なければ全部生成します。

```bash
python regenerate_audio_with_gtts.py --overwrite
```

## 聞き取りやすさを優先して遅めにする

```bash
python regenerate_audio_with_gtts.py --overwrite --slow
```

## `zh-CN` で失敗する場合

環境によって言語コードの扱いが違うことがあります。
その場合は以下を試してください。

```bash
python regenerate_audio_with_gtts.py --overwrite --lang zh-cn
```

または：

```bash
python regenerate_audio_with_gtts.py --overwrite --lang zh
```

## 途中で止まった場合

例えば100番目から再開するなら：

```bash
python regenerate_audio_with_gtts.py --start 100 --overwrite
```

## GitHub Pagesに上げるもの

生成後、以下をGitHubにアップロードしてください。

- `unit1.html`
- `unit2.html`
- `unit3.html`
- `unit4.html`
- `audio/`
- 必要なら `audio_manifest.csv`

アップロード不要なもの：

- `.venv/`
- `__pycache__/`
- `gtts_failed.txt`
- 認証情報やAPIキー類
