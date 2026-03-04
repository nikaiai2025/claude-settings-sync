
## 使用言語
ドキュメントは原則として日本語で記述する。第二言語は英語（可読性等の理由があるときに使用する）。

## 環境管理ルール
このプロジェクトではPythonのパッケージ管理に `uv` を使用しています。
**標準の pip や venv コマンドは直接使用しないでください。**

- **環境構築・同期:** `uv sync`
- **ライブラリの追加:** `uv add <package_name>`
- **スクリプトの実行:** `uv run <script_main.py>`
- **Pythonバージョンの管理:** `uv` が管理（pyproject.tomlを参照）

## TypeScript/Node.js環境
- **パッケージマネージャー:** npm (または pnpm/yarn)
- **Node.js本体:** `uv tool` もしくはシステムインストールを使用

## 主要コマンド
- **テスト実行:** `uv run pytest`
- **フロントエンド起動:** `npm run dev`
- **環境の完全再構築:** `rm -rf .venv && uv sync`