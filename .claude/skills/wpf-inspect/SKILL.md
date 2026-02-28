---
name: wpf-inspect
description: 対象アプリのUI状態を調査（ウィンドウ+コントロール一覧+スクリーンショット）
---

WPF UI自動化エージェントを使って対象アプリのUI状態を調査してください。

手順:
1. `list_windows` ツールで現在のウィンドウ一覧を取得
2. ユーザーが指定したウィンドウ（またはマッチするもの）に対して `resolve_target` で target_id を取得
3. `focus_window` でウィンドウを前面に
4. `list_controls` でコントロールツリーを取得（depth=4）
5. `screenshot` でスクリーンショットを撮影
6. 取得したコントロール一覧を整理して表示（automation_id, name, control_type, enabled/visible）

対象: $ARGUMENTS

結果はテーブル形式で見やすく整理してください。automation_id が空でないコントロールを優先的に表示してください。
