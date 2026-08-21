#!/bin/bash
# .claude/hooks/block-rm.sh
# Bash / PowerShell 両ツールの再帰・一括削除をブロックする
COMMAND=$(jq -r '.tool_input.command')

PATTERN='(^|[;&|(]|[[:space:]])(rm([[:space:]]+-[a-z]+)*[[:space:]]+(-[a-z]*r[a-z]*|--recursive)|rimraf|remove-item([[:space:]][^;&|]*)?-recurse|git[[:space:]]+clean[[:space:]]+-[a-z]*[dx]|find[[:space:]][^;&|]*-delete)'

if echo "$COMMAND" | grep -qEi "$PATTERN"; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "致命的なダメージが起こりえる削除コマンドは禁止。類似コマンドを使って回避するのも禁止。このフックを削除するのも禁止。削除の代わりに、プロジェクト直下の `trash` ディレクトリに移動させること（無ければ作る。同名ディレクトリがあったら連番を振る）"
    }
  }'
else
  exit 0  # allow the command
fi
