#!/bin/bash
# .claude/hooks/block-rm.sh
COMMAND=$(jq -r '.tool_input.command')

if echo "$COMMAND" | grep -q 'rm -r*'; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "致命的なダメージが起こりえる削除コマンドは禁止。類似コマンドを使って回避するのも禁止。このフックを削除するのも禁止。ただちに現在の作業を中断して停止し、この後の対応は人間に確認すること"
    }
  }'
else
  exit 0  # allow the command
fi
