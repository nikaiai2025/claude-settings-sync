# DL実行レシピ

サイトごとの実DL手順。PowerShell（Windows）と Bash（Unix）両対応。

## 共通：出力先準備

```powershell
$base = Join-Path (Get-Location) "tmp\asset\$(Get-Date -Format yyyyMMdd)"
New-Item -ItemType Directory -Path "$base\downloads\images" -Force | Out-Null
New-Item -ItemType Directory -Path "$base\downloads\audio" -Force | Out-Null
New-Item -ItemType Directory -Path "$base\downloads\plugins" -Force | Out-Null
```

## Kenney（直リンクZIP）

WebFetchで該当アセットページから download URL を抽出してから DL：

```powershell
$url = "https://kenney.nl/media/pages/assets/<slug>/<hash>-<name>.zip"
$out = "$base\downloads\images\<asset_name>.zip"
Invoke-WebRequest -Uri $url -OutFile $out
Expand-Archive -Path $out -DestinationPath "$base\downloads\images\<asset_name>" -Force
```

## OpenGameArt

各アセットページの「Files」セクションから直リンクを抽出：

```powershell
$url = "https://opengameart.org/sites/default/files/<file>.zip"
$out = "$base\downloads\images\<asset_name>.zip"
Invoke-WebRequest -Uri $url -OutFile $out -UserAgent "Mozilla/5.0"
Expand-Archive -Path $out -DestinationPath "$base\downloads\images\<asset_name>" -Force
```

User-Agent指定が必要なことがある（403対策）。

## itch.io（CC0・無料）

無料CC0アセットの多くは "Download Now" → "No thanks, just take me to downloads" でログイン不要：

```powershell
# 1. 作者ページのリンクをWebFetchで取得
# 2. download URLを取得（通常はリンク先のフォーム送信が必要なため、UIで誘導することも視野）
# 3. Invoke-WebRequest で取得
```

要ログイン作品はスキップしユーザーに「手動DLしてください」と案内。

## Godot公式アセットライブラリ

API 応答の `download_url` は GitHub の release zip が多い：

```powershell
$apiUrl = "https://godotengine.org/asset-library/api/asset/<asset_id>"
$asset = Invoke-RestMethod -Uri $apiUrl
$zipUrl = $asset.download_url
$out = "$base\downloads\plugins\$($asset.title).zip"
Invoke-WebRequest -Uri $zipUrl -OutFile $out
Expand-Archive -Path $out -DestinationPath "$base\downloads\plugins\$($asset.title)" -Force
```

Git経由のほうが確実な場合は `git clone --depth 1`。

## 失敗時の扱い

- 403/404 → User-Agent追加、リトライ1回まで
- それ以上失敗 → スキップして `report.md` に「手動DL要・URL」として記録
- DL成功後はSHA256でログ：`Get-FileHash <path>` → CREDITS.md に記載すると追跡性向上

## ファイル展開後の整理

ZIP内の不要ファイル（readme.txt、preview.png等）はそのまま残してよい。**素材ファイルを別ディレクトリに移動・リネームしない**（後から作者・出所が辿れなくなる）。
