# Claude Code Sync（運用向け）

## 目的
複数の Windows 端末に散在する Claude Code 設定を Git で一元管理し、
ローカル更新の消失を防ぎながら同期します。

## 管理対象
ルートディレクトリ: `.claude`（端末によって場所が異なる）

対象:
- `Skills\`
- `Agents\`
- `hooks\`
- `AGENTS.md`
- `CLAUDE.md`
- `settings.json`

※ `settings.json` はマシン固有の設定が含まれる可能性があるため、単純コピーで同期します。

## ルート解決（.claude の場所）
以下の順で決定します:
1. `--root` 引数
2. 環境変数 `CLAUDE_HOME`
3. 自動検出 `%USERPROFILE%\.claude`
4. 既定 `~/.claude`（`Path.home() / ".claude"`）

## コマンド
このリポジトリ直下で実行:

```powershell
python dotfiles_sync.py status
python dotfiles_sync.py local_to_git
python dotfiles_sync.py git_to_local
python dotfiles_sync.py delete_remote
```

## 判断フロー（最重要）
`DIFF` は「競合」です。どちらが正かを必ず判断します。

1. **端末を移動した直後**
   - `status`
   - `DIFF` があれば **git_to_local**（Git → ローカル）で最新化
2. **ローカルで編集した後**
   - `status`
   - `DIFF` があれば **local_to_git**（ローカル → Git）で反映

迷う場合は `status` 実行後に表示されるプロンプトで詳細差分を表示します。

## 各コマンドの挙動
- `status`: `LOCAL_ONLY` / `REMOTE_ONLY` / `DIFF` / `SAME` を表示
  - `DIFF` は `70/100 lines identical` のような一致率付き
- `local_to_git`: `LOCAL_ONLY + DIFF` を Git 側へ上書き
  - ローカルが正しいと判断した場合に使う
  - Git 履歴が残るためバックアップ不要
  - 実行後に `git add/commit/push` を自動実行（コミットメッセージはタイムスタンプ）
- `git_to_local`: `REMOTE_ONLY + DIFF` をローカルへ上書き
  - Git が正しいと判断した場合に使う
  - 上書き前にバックアップを作成
  - 実行前に `git pull` を自動実行
- `delete_remote`（メンテナンス用）: `REMOTE_ONLY` を `data/` から削除
  - 通常運用では使わない（不要ファイル整理時のみ）
  - 実行時に削除対象ファイル一覧を表示し、`y/n` で確認
  - 実行後に `git add/commit/push` を自動実行

## バックアップ（git_to_local のみ）
上書き前にローカルを退避:

```
backups/<timestamp>_<hostname>/...
```

`backups/` は Git から除外済み（`.gitignore`）。

## 典型的な安全運用
1. **作業開始時** → `status` → 通常は `git_to_local`
2. **作業終了時** → `status` → 通常は `local_to_git`

## 補足
- `data/` が未作成でも `local_to_git` が生成する
- 端末ごとに `.claude` の場所を固定する例:

```powershell
$env:CLAUDE_HOME="D:\Claude\.claude"
python dotfiles_sync.py status
```
