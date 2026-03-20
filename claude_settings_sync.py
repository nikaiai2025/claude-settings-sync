import argparse
import hashlib
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parent
DATA_ROOT = REPO_ROOT / "data"
BACKUP_ROOT = REPO_ROOT / "backups"

TARGET_DIRS = ["Skills", "Agents", "hooks"]
TARGET_FILES = ["AGENTS.md", "CLAUDE.md", "settings.json"]

SETTINGS_FILENAME = "settings.json"
HOME_PLACEHOLDER = "{{HOME}}"


def find_claude_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()

    env_root = os.environ.get("CLAUDE_HOME")
    if env_root:
        return Path(env_root).expanduser()

    candidates = []
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(Path(userprofile) / ".claude")
    homedrive = os.environ.get("HOMEDRIVE")
    homepath = os.environ.get("HOMEPATH")
    if homedrive and homepath:
        candidates.append(Path(homedrive + homepath) / ".claude")

    for c in candidates:
        if c.exists():
            return c

    return Path.home() / ".claude"


@dataclass(frozen=True)
class FileStatus:
    rel_path: Path
    status: str  # LOCAL_ONLY | REMOTE_ONLY | DIFF | SAME
    similarity: str = ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text_lines(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def line_similarity(a_path: Path, b_path: Path) -> str:
    a_lines = read_text_lines(a_path)
    b_lines = read_text_lines(b_path)
    matcher = SequenceMatcher(a=a_lines, b=b_lines)
    identical = sum(block.size for block in matcher.get_matching_blocks())
    total = max(len(a_lines), len(b_lines))
    return (
        f"{identical}/{total} lines identical" if total > 0 else "0/0 lines identical"
    )


def collect_local_files(root: Path) -> Dict[Path, Path]:
    result: Dict[Path, Path] = {}

    for d in TARGET_DIRS:
        local_dir = root / d
        if local_dir.exists():
            for p in local_dir.rglob("*"):
                if p.is_file() and "__pycache__" not in p.parts:
                    rel = p.relative_to(root)
                    result[rel] = p

    for f in TARGET_FILES:
        p = root / f
        if p.exists() and p.is_file():
            result[p.relative_to(root)] = p

    return result


def collect_repo_files(root: Path) -> Dict[Path, Path]:
    result: Dict[Path, Path] = {}
    if not root.exists():
        return result

    for d in TARGET_DIRS:
        repo_dir = root / d
        if repo_dir.exists():
            for p in repo_dir.rglob("*"):
                if p.is_file() and "__pycache__" not in p.parts:
                    rel = p.relative_to(root)
                    result[rel] = p

    for f in TARGET_FILES:
        p = root / f
        if p.exists() and p.is_file():
            result[p.relative_to(root)] = p

    return result


def get_status(claude_root: Path) -> List[FileStatus]:
    local_map = collect_local_files(claude_root)
    repo_map = collect_repo_files(DATA_ROOT)

    all_paths = sorted(set(local_map.keys()) | set(repo_map.keys()))
    statuses: List[FileStatus] = []

    for rel in all_paths:
        local = local_map.get(rel)
        repo = repo_map.get(rel)
        if local and not repo:
            statuses.append(FileStatus(rel, "LOCAL_ONLY"))
            continue
        if repo and not local:
            statuses.append(FileStatus(rel, "REMOTE_ONLY"))
            continue
        if local and repo:
            if rel.name == SETTINGS_FILENAME:
                # settings.json はホームパスを正規化した内容で比較する
                local_text = normalize_settings(local.read_text(encoding="utf-8"))
                repo_text = repo.read_text(encoding="utf-8")
                if local_text == repo_text:
                    statuses.append(FileStatus(rel, "SAME"))
                else:
                    local_lines = local_text.splitlines()
                    repo_lines = repo_text.splitlines()
                    matcher = SequenceMatcher(a=repo_lines, b=local_lines)
                    identical = sum(b.size for b in matcher.get_matching_blocks())
                    total = max(len(local_lines), len(repo_lines))
                    sim = (
                        f"{identical}/{total} lines identical"
                        if total > 0
                        else "0/0 lines identical"
                    )
                    statuses.append(FileStatus(rel, "DIFF", sim))
            elif sha256_file(local) == sha256_file(repo):
                statuses.append(FileStatus(rel, "SAME"))
            else:
                sim = line_similarity(local, repo)
                statuses.append(FileStatus(rel, "DIFF", sim))
    return statuses


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dst: Path) -> None:
    ensure_parent(dst)
    shutil.copy2(src, dst)


def _home_variants() -> List[str]:
    """ホームパスのバリエーションを長い順に返す（JSONエスケープ、Win、Unix）。"""
    home = str(Path.home())
    variants = []
    # JSON内のエスケープ済み形式（\ → \\）— 最長なので先にマッチさせる
    json_escaped = home.replace("\\", "\\\\")
    if json_escaped != home:
        variants.append(json_escaped)
    # Windows形式（バックスラッシュ）
    variants.append(home.replace("/", "\\"))
    # Unix形式（スラッシュ）
    unix = home.replace("\\", "/")
    if unix not in variants:
        variants.append(unix)
    return variants


def normalize_settings(text: str) -> str:
    """ローカルのホームディレクトリパスを {{HOME}} プレースホルダーに置換する。"""
    for variant in _home_variants():
        text = text.replace(variant, HOME_PLACEHOLDER)
    return text


def restore_settings(text: str) -> str:
    """{{HOME}} プレースホルダーをローカルのホームディレクトリパスに復元する。
    settings.json はJSON形式のため、バックスラッシュをエスケープして復元する。
    """
    home = str(Path.home())
    home_for_json = home.replace("\\", "\\\\")
    return text.replace(HOME_PLACEHOLDER, home_for_json)


def copy_settings_normalized(src: Path, dst: Path) -> None:
    """settings.json をホームパス正規化してコピーする（local -> git 方向）。"""
    ensure_parent(dst)
    text = src.read_text(encoding="utf-8")
    dst.write_text(normalize_settings(text), encoding="utf-8")


def copy_settings_restored(src: Path, dst: Path) -> None:
    """settings.json の {{HOME}} を復元してコピーする（git -> local 方向）。"""
    ensure_parent(dst)
    text = src.read_text(encoding="utf-8")
    dst.write_text(restore_settings(text), encoding="utf-8")


def backup_files(files: Iterable[Tuple[Path, Path]]) -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    host = socket.gethostname()
    backup_root = BACKUP_ROOT / f"{ts}_{host}"
    for rel, local_path in files:
        backup_path = backup_root / rel
        copy_file(local_path, backup_path)
    return backup_root


def show_diffs(claude_root: Path, diff_items: List[FileStatus]) -> None:
    if not diff_items:
        return

    local_map = collect_local_files(claude_root)
    repo_map = collect_repo_files(DATA_ROOT)

    for s in diff_items:
        local_path = local_map[s.rel_path]
        repo_path = repo_map[s.rel_path]
        local_lines = read_text_lines(local_path)
        repo_lines = read_text_lines(repo_path)
        diff = unified_diff(
            repo_lines,
            local_lines,
            fromfile=f"repo/{s.rel_path}",
            tofile=f"local/{s.rel_path}",
            lineterm="",
        )
        print(f"\n=== DIFF {s.rel_path} ({s.similarity}) ===")
        for line in diff:
            print(line)


def cmd_status(claude_root: Path) -> int:
    statuses = get_status(claude_root)
    if not statuses:
        print("No target files found in local or repo.")
        return 0

    non_same = [s for s in statuses if s.status != "SAME"]
    if not non_same:
        print("差分なし")
        return 0

    local_map = collect_local_files(claude_root)
    repo_map = collect_repo_files(DATA_ROOT)

    def format_mtime(p: Path | None) -> str:
        if p and p.exists():
            return datetime.fromtimestamp(p.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        return "N/A"

    for s in non_same:
        if s.status == "DIFF":
            lm = format_mtime(local_map.get(s.rel_path))
            rm = format_mtime(repo_map.get(s.rel_path))
            print(f"{s.status:11} {s.rel_path} ({s.similarity})")
            print(f"            Local: {lm} / Git: {rm}")
        else:
            print(f"{s.status:11} {s.rel_path}")

    diff_items = [s for s in non_same if s.status == "DIFF"]
    if not diff_items:
        return 0

    answer = input("Show detailed DIFF for these files? (y/n): ").strip().lower()
    if answer == "y":
        show_diffs(claude_root, diff_items)

    return 0


def cmd_collect(claude_root: Path) -> int:
    statuses = get_status(claude_root)
    local_map = collect_local_files(claude_root)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    to_copy: List[Tuple[Path, Path]] = []
    for s in statuses:
        if s.status in ("LOCAL_ONLY", "DIFF"):
            src = local_map[s.rel_path]
            dst = DATA_ROOT / s.rel_path
            to_copy.append((src, dst))

    for src, dst in to_copy:
        if src.name == SETTINGS_FILENAME:
            # settings.json はホームパスを {{HOME}} に正規化して保存する
            copy_settings_normalized(src, dst)
        else:
            copy_file(src, dst)

    print(f"Collected {len(to_copy)} files into repo data/ (LOCAL_ONLY + DIFF).")
    return 0


def run_git_commit_push() -> None:
    def run(cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)

    add = run(["git", "add", "-A", "--", "data"])
    if add.returncode != 0:
        print("git add failed:")
        print(add.stderr.strip())
        return

    staged = run(["git", "diff", "--cached", "--quiet", "--", "data"])
    if staged.returncode == 0:
        print("Nothing to commit.")
        return
    if staged.returncode != 1:
        print("git diff --cached failed:")
        print(staged.stderr.strip())
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit = run(["git", "commit", "-m", f"Update Claude settings ({ts})"])
    if commit.returncode != 0:
        print("git commit failed:")
        print(commit.stderr.strip())
        return

    push = run(["git", "push"])
    if push.returncode != 0:
        print("git push failed:")
        print(push.stderr.strip())
        return

    print("Git add/commit/push completed.")


def run_git_pull() -> bool:
    pull = subprocess.run(
        ["git", "pull"], cwd=REPO_ROOT, text=True, capture_output=True
    )
    if pull.returncode != 0:
        print("git pull failed:")
        print(pull.stderr.strip())
        return False
    print("Git pull completed.")
    return True


def cmd_apply(claude_root: Path) -> int:
    if not run_git_pull():
        return 1
    statuses = get_status(claude_root)
    repo_map = collect_repo_files(DATA_ROOT)

    to_backup: List[Tuple[Path, Path]] = []
    to_copy: List[Tuple[Path, Path]] = []

    for s in statuses:
        if s.status == "DIFF":
            local_path = claude_root / s.rel_path
            to_backup.append((s.rel_path, local_path))
            src = repo_map[s.rel_path]
            dst = claude_root / s.rel_path
            to_copy.append((src, dst))
        elif s.status == "REMOTE_ONLY":
            src = repo_map[s.rel_path]
            dst = claude_root / s.rel_path
            to_copy.append((src, dst))

    if to_backup:
        backup_root = backup_files(to_backup)
        print(f"Backup created: {backup_root}")
    else:
        print("No backups created (no local files to overwrite).")

    for src, dst in to_copy:
        if src.name == SETTINGS_FILENAME:
            # settings.json は {{HOME}} をローカルのホームパスに復元して保存する
            copy_settings_restored(src, dst)
        else:
            copy_file(src, dst)

    print(f"Applied {len(to_copy)} files from repo data/ to local.")
    return 0


def remove_empty_dirs_upward(path: Path, stop_at: Path) -> None:
    current = path.parent
    while current != stop_at and stop_at in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def cmd_delete_remote(claude_root: Path) -> int:
    statuses = get_status(claude_root)
    repo_map = collect_repo_files(DATA_ROOT)

    to_remove: List[Tuple[Path, Path]] = []
    for s in statuses:
        if s.status == "REMOTE_ONLY":
            repo_path = repo_map.get(s.rel_path)
            if repo_path:
                to_remove.append((s.rel_path, repo_path))

    if not to_remove:
        print("No REMOTE_ONLY files to delete from repo data/.")
        return 2

    print("Delete target files from repo data/ (REMOTE_ONLY):")
    for rel, _ in to_remove:
        print(f"- {rel}")
    print(f"Total: {len(to_remove)}")

    answer = input("Proceed with deletion? (y/n): ").strip().lower()
    if answer != "y":
        print("Cancelled.")
        return 2

    removed = 0
    for _, repo_path in to_remove:
        if repo_path.exists() and repo_path.is_file():
            repo_path.unlink()
            remove_empty_dirs_upward(repo_path, DATA_ROOT)
            removed += 1

    print(f"Deleted {removed} REMOTE_ONLY files from repo data/.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Claude Code settings via Git repo."
    )
    parser.add_argument(
        "--root",
        help="Claude settings root (overrides CLAUDE_HOME). Example: C:\\Users\\user\\.claude",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show status between local and repo.")
    # diff command removed; status now supports optional detailed diff display
    sub.add_parser("local_to_git", help="Copy LOCAL_ONLY + DIFF from local to repo.")
    sub.add_parser(
        "git_to_local", help="Copy REMOTE_ONLY + DIFF from repo to local (with backup)."
    )
    sub.add_parser(
        "delete_remote",
        help="Delete REMOTE_ONLY files from repo data/ (maintenance, with confirmation).",
    )

    args = parser.parse_args()

    claude_root = find_claude_root(args.root)

    if args.command == "status":
        return cmd_status(claude_root)
    if args.command == "local_to_git":
        rc = cmd_collect(claude_root)
        if rc == 0:
            run_git_commit_push()
        return rc
    if args.command == "git_to_local":
        return cmd_apply(claude_root)
    if args.command == "delete_remote":
        rc = cmd_delete_remote(claude_root)
        if rc == 0:
            run_git_commit_push()
        return rc

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
