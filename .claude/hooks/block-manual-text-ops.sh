#!/usr/bin/env bash
# PreToolUse hook: Block manual text input/reading that bypasses wpf-agent ui commands.
# Reads tool input JSON from stdin, checks the "command" field for prohibited patterns.
# Exit 0 = allow, Exit 2 = block (stdout shown as reason).
set -euo pipefail

INPUT="$(cat)"
COMMAND="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null || true)"

if [ -z "$COMMAND" ]; then
  exit 0
fi

# --- Prohibited patterns ---

# 1. Direct pywinauto text operations (set_edit_text, type_keys, window_text, get_value)
if echo "$COMMAND" | grep -qiP '(set_edit_text|type_keys|\.window_text\(|\.get_value\()'; then
  if ! echo "$COMMAND" | grep -q 'wpf-agent'; then
    cat <<'MSG'
[BLOCKED] pywinauto のテキスト操作を直接使用しないでください。
代わりに以下のコマンドを使ってください:
  テキスト入力: wpf-agent ui type --pid <pid> --aid <id> --text "..."
  テキスト読取: wpf-agent ui read --pid <pid> --aid <id>
MSG
    exit 2
  fi
fi

# 2. xdotool type / key
if echo "$COMMAND" | grep -qiP '\bxdotool\s+(type|key)\b'; then
  cat <<'MSG'
[BLOCKED] xdotool でのキーボード入力は禁止されています。
代わりに以下のコマンドを使ってください:
  テキスト入力: wpf-agent ui type --pid <pid> --aid <id> --text "..."
MSG
  exit 2
fi

# 3. python keyboard / pyautogui / pynput modules for text input
if echo "$COMMAND" | grep -qiP 'python.*\b(keyboard\.(write|send|press)|pyautogui\.(typewrite|write|press|hotkey)|pynput)'; then
  cat <<'MSG'
[BLOCKED] keyboard / pyautogui / pynput でのキー入力は禁止されています。
代わりに以下のコマンドを使ってください:
  テキスト入力: wpf-agent ui type --pid <pid> --aid <id> --text "..."
MSG
  exit 2
fi

# 4. Clipboard paste tools
if echo "$COMMAND" | grep -qiP '\b(xclip|xsel|pyperclip|pbpaste|pbcopy)\b'; then
  if ! echo "$COMMAND" | grep -q 'wpf-agent'; then
    cat <<'MSG'
[BLOCKED] クリップボード経由のテキスト操作は禁止されています。
代わりに以下のコマンドを使ってください:
  テキスト入力: wpf-agent ui type --pid <pid> --aid <id> --text "..."
  テキスト読取: wpf-agent ui read --pid <pid> --aid <id>
MSG
    exit 2
  fi
fi

# 5. SendKeys / xte / ydotool
if echo "$COMMAND" | grep -qiP '\b(SendKeys|xte|ydotool)\b'; then
  if ! echo "$COMMAND" | grep -q 'wpf-agent'; then
    cat <<'MSG'
[BLOCKED] SendKeys / xte / ydotool でのキー入力は禁止されています。
代わりに以下のコマンドを使ってください:
  テキスト入力: wpf-agent ui type --pid <pid> --aid <id> --text "..."
MSG
    exit 2
  fi
fi

# All checks passed
exit 0
