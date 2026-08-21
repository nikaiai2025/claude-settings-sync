---
name: ai-chat
description: |
  外部AI（Codex / Grok / Claude）のCLIにプロンプトを送り、応答を得るスキル。
  ユーザーが「CLIで聞いて」「codexに聞いて」等、明示的にCLI経由での会話を指示した場合にのみ使用する。
  通常の質問応答・コーディング・調査タスクでは使用しない。
user-invocable: true
allowed-tools: Bash, Read, Write
context: fork
argument-hint: "<ai名> <プロンプト>"
---

# AI CLI チャット

コマンドラインからAI（Codex / Grok / Claude）にプロンプトを送り、応答を表示する。

## 引数

$ARGUMENTS

第1トークンがAI名、残りがプロンプト本文。

## AI名とCLIコマンドの対応

| AI名（エイリアス） | CLIコマンド |
|---|---|
| `codex` | `codex exec --sandbox read-only ` |
| `grok` | `grok -p` |
| `claude` | `claude -p` |

## 実行手順

1. 引数の第1トークンからAI名を特定する（大文字小文字不問）。該当しない場合はエラーを表示して終了。
2. プロンプト本文（第2トークン以降）を取得する。空の場合はエラーを表示して終了。
3. 以下のコマンドをBashツールで実行する:

### Codex の場合
```
codex exec --sandbox read-only "PROMPT" 2>/dev/null \
  || codex exec --sandbox read-only "PROMPT" 2>/dev/null \
  || echo "（Codex CLI実行失敗）"
```

- `read-only` でもリポジトリ内のファイルは参照できるが、変更はできない。
- 原則として対象リポジトリのルートをCWDにして実行する。
- CWDと対象が異なる場合は、`-C "REPO"` で対象リポジトリを明示する。
- 差分レビューには `codex -C "REPO" review --uncommitted` または `--base BRANCH` を優先する。
- セッション履歴を保存しない場合は、`codex exec` に `--ephemeral` を追加する。

### Grok の場合
```
grok -p "PROMPT" 2>/dev/null \
  || grok -p "PROMPT" 2>/dev/null \
  || echo "（Grok CLI実行失敗）"
```

### Claude の場合
```
echo "PROMPT" | claude -p --model opus 2>/dev/null \
  || echo "PROMPT" | claude -p 2>/dev/null \
  || echo "（Claude CLI実行失敗）"
```

4. 応答をそのままユーザーに表示する。

## 注意事項

- プロンプト内のシェル特殊文字はエスケープすること
- タイムアウトは120秒（デフォルト）
- 各CLIは事前にインストール・認証済みであることを前提とする
