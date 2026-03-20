# Claude Settings Sync

### What is this?
Sync your Claude Code settings (`~/.claude/`) across multiple machines via Git.
Home directory paths in `settings.json` are automatically normalized, so it works even when usernames differ between machines.

### Why not just `git init ~/.claude`?

`~/.claude/` contains files you should never commit: `history.jsonl` (large), `.credentials.json` (secrets), `sessions/`, `cache/`, `telemetry/`, etc.
Managing this with `.gitignore` negation rules is fragile and risks leaking credentials.
This tool uses an **allowlist approach** — only explicitly specified files are synced.

---

## これは何？
Claude Code の設定（`~/.claude/` 配下）を複数端末間で Git 同期するツールです。
ユーザー名が端末間で異なっていても、`settings.json` 内のパスは自動で正規化されます。

## なぜ `~/.claude/` を直接 Git 管理しないのか

`~/.claude/` には同期したくないファイルが大量にあります：

| 同期したい | 同期したくない |
|---|---|
| `Skills/`, `Agents/`, `hooks/` | `history.jsonl`（巨大な会話履歴） |
| `CLAUDE.md`, `settings.json` | `.credentials.json`（認証情報） |
| | `sessions/`, `cache/`, `telemetry/` 等 |

`.gitignore` で除外する方法もありますが、否定ルールのネスト管理が煩雑で、
Claude Code のアップデートで内部ファイルが増えるたびに対応が必要になります。
また、誤って認証情報をコミットするリスクもあります。

このツールは**許可リスト方式**で、指定したファイルだけを安全に同期します。

## 管理対象

| 対象 | 説明 |
|---|---|
| `Skills/`, `Agents/`, `hooks/` | カスタム定義ファイル |
| `CLAUDE.md`, `AGENTS.md` | グローバル指示ファイル |
| `settings.json` | 権限・hooks・MCP サーバー等の設定 |

## 使い方

```powershell
python claude_settings_sync.py status        # 差分を確認
python claude_settings_sync.py local_to_git  # ローカル → Git に反映
python claude_settings_sync.py git_to_local  # Git → ローカルに反映
python claude_settings_sync.py delete_remote # Git 側の不要ファイルを削除
```

**基本の運用サイクル:**

1. **作業開始時** → `status` → `git_to_local` で最新化
2. **作業終了時** → `status` → `local_to_git` で反映

`status` で `DIFF` が出たら、どちらが正しいかを判断してからコマンドを選びます。
迷う場合は `status` 実行後のプロンプトで詳細差分を表示できます。

## settings.json のパス正規化

`settings.json` 内のホームディレクトリパスは、Git 保存時に `{{HOME}}` に置換され、
ローカル復元時に各端末の `Path.home()` で展開されます。

### 例: alice が `local_to_git` → bob が `git_to_local` した場合

| | alice（端末A） | bob（端末B） |
|---|---|---|
| **Before** | `C:\Users\alice\anaconda3\fastmcp.exe` | `C:\Users\bob\anaconda3\fastmcp.exe` |
| **After** | 変化なし | `C:\Users\bob\anaconda3\fastmcp.exe` |

パス中のユーザー名は各端末に合わせて自動復元されます。

## 制限事項

- **`settings.json` はファイル単位の全上書きです。** キー単位のマージは行いません。
  `git_to_local` を実行すると、Git 側の内容でローカルが完全に置き換わります。
- **端末固有の設定は保持されません。** 例えば「この端末だけに特定の MCP サーバーを追加したい」場合、
  他端末から `git_to_local` するとその設定は消えます。
- ホームディレクトリ配下にないパス（例: `D:\tools\...`）は正規化の対象外です。
  端末間でパス構造が異なる場合は手動調整が必要です。
- `git_to_local` は上書き前にバックアップを `backups/` に作成します。
  `local_to_git` は Git 履歴があるためバックアップ不要です。

## 詳細設定

`.claude` の場所が既定と異なる場合、以下の順で解決します:

1. `--root` 引数
2. 環境変数 `CLAUDE_HOME`
3. `%USERPROFILE%\.claude`（自動検出）
4. `~/.claude`（既定）
