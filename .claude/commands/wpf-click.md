WPF UI自動化エージェントを使ってUI要素をクリックしてください。

手順:
1. 対象ウィンドウが未解決の場合、`list_windows` → `resolve_target` で解決
2. `focus_window` でウィンドウを前面に
3. 指定されたセレクタで `click` を実行
4. クリック後に `screenshot` で結果を確認
5. 必要に応じて `list_controls` で変化を確認

指示: $ARGUMENTS

セレクタの指定方法:
- automation_id: 例 "SaveButton"
- name + control_type: 例 "OK" Button
- 曖昧な場合は先に list_controls で候補を確認してからクリック
