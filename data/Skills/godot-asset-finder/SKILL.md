---
name: godot-asset-finder
description: |
  Godot/2D・3Dゲーム向けのアセット（画像・音声・スクリプト/プラグイン）を要件ベースで調査し、ライセンス整合の候補リスト＋実物DLまで段階的に提供するスキル。
  プロジェクト情報（ジャンル/アートスタイル/ライセンス制約等）をインプットに、Godot公式アセットライブラリ＋外部素材サイト（Kenney/OpenGameArt/itch.io/Freesound等）を横断調査する。
  ユーザーが「アセットを探して」「素材の候補を出して」「Godot公式ライブラリでプラグインを探して」と依頼したとき、または `/godot-asset-finder` で明示的に呼び出されたときに使用する。
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Bash, PowerShell, WebSearch, WebFetch, AskUserQuestion, TaskCreate, TaskUpdate, TaskList
argument-hint: "<project_info_path or inline description> [<output_dir>]"
---

# Godot Asset Finder

ゲーム開発者の「使える素材を探す」工程を、要件ヒアリング → 候補抽出 → 選別 → DL までワンストップで支援する。

## 基本方針

1. **要件駆動**：プロジェクト情報を起点にニーズを分類してから探す。手当たり次第には探さない。
2. **段階確認**：候補提示 → ユーザー選別 → DL の3段階で進める。勝手にDLしない。
3. **ライセンス透明性**：すべての候補にライセンス種別を明記。商用要件なら CC0 を優先提案。
4. **公式と外部の役割分担**：公式アセットライブラリ＝プラグイン/スクリプト中心、外部サイト＝画像/音声中心と割り切る。

## インプット

`$ARGUMENTS` を以下のいずれかとして解釈：
- **既存ファイルパス**：プロジェクト情報の記述ファイル（README.md等）を Read
- **インライン記述**：「2Dトランプゲーム、レトロ風」のような短い説明
- **省略時**：対話的にヒアリング

オプションで第2引数として出力ディレクトリ。省略時は CWD 下の `tmp/asset/<YYYYMMDD>/`。

## 実行手順

### Step 1: 要件整理

プロジェクト情報から以下を抽出（不足は AskUserQuestion で補完）：

| 項目 | 例 |
|---|---|
| ジャンル/テーマ | カードゲーム、RPG、SF、汎用 |
| 必要なアセット種別 | 2D画像、3Dモデル、BGM、SE、UI、プラグイン |
| アートスタイル | ピクセル、ベクター、レトロ、フラット |
| ライセンス制約 | CC0のみ／CC-BY可／商用要否 |

確認内容を `requirements.md` として出力先に保存。

### Step 2: 公式アセットライブラリ調査（プラグイン/スクリプト）

[Godot Asset Library API](https://godotengine.org/asset-library/api/asset) を WebFetch で叩く。

```
https://godotengine.org/asset-library/api/asset?filter=<キーワード>&category=<id>&max_results=20
```

カテゴリID（よく使うもの）：
- `1` 2D Tools / `2` 3D Tools / `3` Shaders / `4` Materials
- `5` Tools / `6` Scripts / `7` Misc / `8` Templates / `9` Projects / `10` Demos

複数キーワードで横断検索し、要件に合うものを抽出。**「素材」より「制作支援」に有用**な点を理解した上で提示。

### Step 3: 公式ライブラリ候補の選別

候補を `AskUserQuestion`（multiSelect）で提示：
- どのプラグイン/スクリプトを詳しく見るか
- どれをDL対象にするか

選別結果を `selected_official.md` に記録。

### Step 4: 外部サイト調査（画像・音声）

要件に合わせて以下のサイトを WebSearch + WebFetch で横断調査：

| 優先度 | サイト | 強み |
|---|---|---|
| 1 | Kenney (kenney.nl) | CC0・スタイル統一・網羅性 |
| 2 | OpenGameArt.org | ライセンス明確・コミュニティ規模 |
| 3 | itch.io (free + CC0タグ) | 個性的素材・ピクセル系 |
| 4 | Freesound | SE専門・実録系 |
| 5 | その他（CraftPix, GameArt2D, FilmMusic.io 等） | 補完用 |

詳細は `references/sites.md` 参照。

各候補について以下を記録：
- 素材名・URL・ライセンス・形式（PNG/OGG/WAV等）・サイズ/長さ・特徴

### Step 5: 外部素材候補の選別

`AskUserQuestion`（multiSelect）で「DL対象」を確認。**選択されたもののみ次ステップへ**。

### Step 6: DL実行

選択されたアセットを出力ディレクトリ配下にDL。

- **Kenney**：直接ZIPリンクが取得できる。`Invoke-WebRequest` (PowerShell) または `curl` (Bash) で取得
- **OpenGameArt**：素材ページからファイルURL抽出 → DL
- **itch.io**：無料CC0は直接DL可能なケースが多い。要ログイン作品はスキップしユーザーに通知
- **Godot公式ライブラリ**：GitHubリポジトリのことが多い。`git clone` または release zip をDL

DL先構造：
```
<output_dir>/
  requirements.md
  candidates.md          # 全候補一覧
  selected_official.md   # 選別済み公式アセット
  selected_external.md   # 選別済み外部アセット
  report.md              # 最終レポート（知見・推奨運用含む）
  CREDITS.md             # CC-BY素材のクレジット記録
  downloads/
    images/<asset_name>/
    audio/<asset_name>/
    plugins/<asset_name>/
```

DL失敗時はエラーをレポートに記録し、手動DL用URLを残す。

### Step 7: 最終レポート出力

`report.md` を生成。テンプレートは `references/report_template.md` 参照。

含めるセクション：
1. 要件サマリ
2. 採用アセット一覧（種別×ライセンス×ファイルパス）
3. クレジット必須素材の一覧（CC-BY 等）
4. 統合上の留意点（ファイル形式変換・音量正規化・スタイル混在の注意 等）
5. 採用しなかった候補と理由（参考）

## ユーザー確認のタイミング（厳守）

| タイミング | 確認内容 |
|---|---|
| Step 1終了時 | 抽出した要件で合っているか |
| Step 3 | 公式ライブラリ候補のうちどれを採用するか |
| Step 5 | 外部素材候補のうちどれをDLするか |
| Step 6前 | DL実行してよいか（最終確認） |

**勝手に進めない**。各ステップで小休止を入れること。

## ライセンス判定の指針

| ライセンス | 商用 | クレジット | 推奨度 |
|---|---|---|---|
| CC0 / Public Domain | OK | 不要 | ★★★ |
| CC-BY 4.0 | OK | 必須 | ★★ |
| CC-BY-SA | OK（SA継承） | 必須 | ★ |
| CC-BY-NC | 不可 | 必須 | × (商用時) |
| GPL | OK（GPL継承） | 必須 | × (非OSS時) |
| 独自規約 | 規約次第 | 規約次第 | 都度判定 |

商用想定が不明なときは「CC0優先、CC-BYは要否確認」のスタンスで進める。

## 禁止事項

- ユーザー確認なしのDL実行
- ライセンス未確認のままの「採用」記載
- 公式ライブラリだけで素材完結を装う（素材は外部が主）
- DL先の元ファイル上書き

## 引数

$ARGUMENTS
