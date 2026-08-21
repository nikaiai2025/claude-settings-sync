# 素材サイト別ガイド

各サイトの探索方法・API/検索URL・ライセンスの注意点をまとめる。

## Godot公式アセットライブラリ

- **URL**: https://godotengine.org/asset-library/asset
- **API**: `https://godotengine.org/asset-library/api/asset?filter=<keyword>&category=<id>&max_results=20`
- **JSON返却**：`result`配列の各要素に `asset_id`, `title`, `category`, `godot_version`, `download_url` 等
- **カテゴリID**: 1=2D Tools / 2=3D Tools / 3=Shaders / 4=Materials / 5=Tools / 6=Scripts / 7=Misc / 8=Templates / 9=Projects / 10=Demos
- **特性**：プラグイン/スクリプト/デモ中心。生素材は稀（例外：Calinou氏のKenney音素材リパッケージ）
- **DL**：多くがGitHubリポジトリの release zip。`download_url` から直接取得可能

## Kenney (kenney.nl)

- **URL**: https://kenney.nl/assets
- **ライセンス**：全てCC0
- **検索**：サイト内検索 or `https://kenney.nl/assets?q=<keyword>`
- **強み**：スタイル統一、商用OK・クレジット不要、画像と音声両方
- **DLパターン**：各アセットページの "Download" ボタン → ZIP直リンク

## OpenGameArt.org

- **URL**: https://opengameart.org/
- **検索**: `https://opengameart.org/art-search-advanced?keys=<keyword>&field_art_licenses_tid%5B%5D=4` （CC0フィルタ）
- **ライセンスID**: 4=CC0 / 2=CC-BY 3.0 / 3=CC-BY-SA 3.0 / 6=CC-BY 4.0 / 7=CC-BY-SA 4.0
- **特性**：作者ごとに異なるライセンス。各アセットページの "License(s)" 欄を必ず確認
- **DL**：ページ内 "Files" セクションに直リンク

## itch.io

- **URL**: https://itch.io/game-assets/free
- **タグ検索**: `https://itch.io/game-assets/free/tag-<タグ>` （例: tag-cards, tag-chiptune）
- **CC0絞り込み**: `https://itch.io/game-assets/assets-cc0`
- **特性**：作者ごとに条件異なる。CC0タグでも作者文面を要確認
- **DL**：「No thanks, just take me to the downloads」リンクで直接DL可能なものが多い

## Freesound

- **URL**: https://freesound.org/
- **検索**: `https://freesound.org/search/?q=<keyword>&f=license:%22Creative+Commons+0%22` （CC0絞り込み）
- **特性**：SE特化、実録系の品質が高い。アカウント登録が必要なケースあり
- **DL**：ログイン推奨

## CraftPix / GameArt2D（補完）

- CraftPix: https://craftpix.net/freebies/ — Game Kits（ジャンル一式）が便利
- GameArt2D: https://www.gameart2d.com/freebies.html — キャラ/背景セット
- **ライセンス**：サイト独自規約。商用条件を必ず読む

## FilmMusic.io（楽曲）

- **URL**: https://filmmusic.io/
- **特性**：Kevin MacLeod 等プロ楽曲。CC-BY が中心（クレジット必須）
- **注意**：MP3のみのこともある → Godotで使うなら OGG/WAV 変換推奨

## 探索フロー（推奨順序）

1. **公式ライブラリ**：プラグイン/スクリプトを最初に当たる
2. **Kenney**：画像・音声の第一候補（CC0で完結することが多い）
3. **OpenGameArt**：Kenneyに無いジャンル、特定の質感を求めるとき
4. **itch.io**：個性のあるピクセル素材、特化パック
5. **Freesound**：SE補完
6. **その他**：上記で足りない場合のみ
