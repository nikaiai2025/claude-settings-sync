"""
CSVマージスクリプト
- 指定ディレクトリ内の全CSVを1つにマージ
- ヘッダ行は先頭ファイルのもののみ保持
- ヘッダ不一致時はエラーで中断
- UTF-8 BOM付きで出力（Excel対応）
- CSVフォーマットを問わず使用可能
"""

import sys
import os
import glob
import csv
from datetime import datetime


def detect_encoding(file_path):
    """BOM付きUTF-8かどうかを判定し、適切なエンコーディングを返す"""
    with open(file_path, "rb") as f:
        head = f.read(3)
    if head == b"\xef\xbb\xbf":
        return "utf-8-sig"
    with open(file_path, "rb") as f:
        raw = f.read()
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp932"


def describe_header_diff(base_file, base_header, target_file, target_header):
    """ヘッダの差分を分かりやすく説明する"""
    lines = []
    lines.append(f"  基準ファイル: {os.path.basename(base_file)}")
    lines.append(f"  不一致ファイル: {os.path.basename(target_file)}")

    base_set = set(base_header)
    target_set = set(target_header)

    if len(base_header) != len(target_header):
        lines.append(f"  項目数が異なります: 基準={len(base_header)}列, 不一致={len(target_header)}列")

    only_in_base = base_set - target_set
    only_in_target = target_set - base_set
    if only_in_base:
        lines.append(f"  基準にのみ存在する項目: {', '.join(sorted(only_in_base))}")
    if only_in_target:
        lines.append(f"  不一致ファイルにのみ存在する項目: {', '.join(sorted(only_in_target))}")

    if not only_in_base and not only_in_target and len(base_header) == len(target_header):
        # 項目名は同じだが順序が異なる
        for i, (b, t) in enumerate(zip(base_header, target_header)):
            if b != t:
                lines.append(f"  列{i + 1}: 基準=\"{b}\" ≠ 不一致=\"{t}\"（項目の順序が異なります）")

    return "\n".join(lines)


def sanitize_filename(name):
    """ファイル名からカンマ等のCSV特殊文字を除去する"""
    # 拡張子を除去し、カンマ・ダブルクォートを削除
    name = os.path.splitext(name)[0]
    for ch in [",", '"', "\n", "\r"]:
        name = name.replace(ch, "")
    return name


def merge_csv(input_dir, output_path=None):
    csv_files = sorted(glob.glob(os.path.join(input_dir, "*.csv")))

    if not csv_files:
        print(f"エラー: {input_dir} にCSVファイルが見つかりません。", file=sys.stderr)
        sys.exit(1)

    if output_path is None:
        dir_name = os.path.basename(os.path.normpath(input_dir))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(input_dir, f"{timestamp}_{dir_name}.csv")

    # 出力ファイル自体をマージ対象から除外
    output_abs = os.path.abspath(output_path)
    csv_files = [f for f in csv_files if os.path.abspath(f) != output_abs]

    if not csv_files:
        print("エラー: マージ対象のCSVファイルがありません。", file=sys.stderr)
        sys.exit(1)

    print(f"マージ対象: {len(csv_files)} ファイル")
    for f in csv_files:
        print(f"  - {os.path.basename(f)}")
    print()

    # === Phase 1: 全ファイルのヘッダを検証 ===
    print("ヘッダ検証中...")
    headers = {}
    for file_path in csv_files:
        encoding = detect_encoding(file_path)
        with open(file_path, "r", encoding=encoding, newline="") as f:
            reader = csv.reader(f)
            first_row = next(reader, None)
        if first_row is None:
            print(f"  警告: {os.path.basename(file_path)} は空のファイルです。スキップします。")
            continue
        headers[file_path] = first_row

    if not headers:
        print("エラー: 有効なCSVファイルがありません。", file=sys.stderr)
        sys.exit(1)

    base_file = list(headers.keys())[0]
    base_header = headers[base_file]
    errors = []

    for file_path, header in headers.items():
        if file_path == base_file:
            continue
        if header != base_header:
            errors.append(describe_header_diff(base_file, base_header, file_path, header))

    if errors:
        print("エラー: ヘッダの不一致が見つかりました。処理を中断します。\n", file=sys.stderr)
        for err in errors:
            print(err, file=sys.stderr)
            print(file=sys.stderr)
        print(f"基準ヘッダ ({os.path.basename(base_file)}): {base_header}", file=sys.stderr)
        sys.exit(1)

    print(f"  OK: 全ファイルのヘッダが一致しています。({len(base_header)}列)\n")

    # === Phase 2: マージ実行（ファイル名列を先頭に追加） ===
    all_rows = []
    valid_files = [f for f in csv_files if f in headers]

    for i, file_path in enumerate(valid_files):
        encoding = detect_encoding(file_path)
        fname = sanitize_filename(os.path.basename(file_path))
        with open(file_path, "r", encoding=encoding, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if i == 0:
            # ヘッダ行に「ファイル名」を先頭追加
            all_rows.append(["ファイル名"] + rows[0])
            for row in rows[1:]:
                all_rows.append([fname] + row)
        else:
            for row in rows[1:]:  # ヘッダ行をスキップ
                all_rows.append([fname] + row)

    # UTF-8 BOM付きで出力
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(all_rows)

    data_count = len(all_rows) - 1  # ヘッダ行を除く
    print(f"完了: {data_count} 件のデータ行をマージしました。")
    print(f"出力: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python merge_csv.py <CSVディレクトリ> [出力ファイルパス]")
        print("  例: python merge_csv.py C:\\data\\csv")
        print("  例: python merge_csv.py C:\\data\\csv C:\\output\\merged.csv")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) >= 3 else None

    if not os.path.isdir(input_dir):
        print(f"エラー: ディレクトリが見つかりません: {input_dir}", file=sys.stderr)
        sys.exit(1)

    merge_csv(input_dir, output_path)
