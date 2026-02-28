---
name: wpf-type
description: UI要素にテキストを入力して値を検証
---

WPF UI自動化エージェントを使ってテキストを入力してください。

手順:
1. 対象ウィンドウが未解決の場合、`list_windows` → `resolve_target` で解決
2. `focus_window` でウィンドウを前面に
3. 指定されたセレクタで `type_text` を実行
4. 入力後に `read_text` で値を検証
5. `screenshot` で結果を確認

指示: $ARGUMENTS

セレクタとテキストの指定方法:
- 例: "ServerUrlTextBox に http://localhost:8080 を入力"
- 例: "ユーザー名フィールド(automation_id=UsernameBox)に admin を入力"
