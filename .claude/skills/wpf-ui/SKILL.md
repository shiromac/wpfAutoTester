---
name: wpf-ui
description: WPF UI操作（調査・クリック・入力・スクリーンショット）
argument-hint: "[inspect|click|type] target and params"
---

WPF UI自動化エージェントを使ってUI操作を行ってください。

指示: $ARGUMENTS

## モード判定

引数からモードを自動判定する:
- **inspect モード**: 引数なし / "inspect" / "調査" / "確認" / "スクショ"
- **click モード**: "click" / "クリック" / `--aid` 指定あり（`--text` なし）
- **type モード**: "type" / "入力" / `--text` 指定あり

---

## inspect モード（UI調査）

対象アプリのUI状態を調査する。

手順:
1. `list_windows` ツールで現在のウィンドウ一覧を取得
2. ユーザーが指定したウィンドウ（またはマッチするもの）に対して `resolve_target` で target_id を取得
3. `focus_window` でウィンドウを前面に
4. `list_controls` でコントロールツリーを取得（depth=4）
5. `screenshot` でスクリーンショットを撮影
6. 取得したコントロール一覧を整理して表示（automation_id, name, control_type, enabled/visible）

結果はテーブル形式で見やすく整理する。automation_id が空でないコントロールを優先的に表示する。

---

## click モード（要素クリック）

UI要素をクリックしてスクリーンショットで結果を検証する。

手順:
1. 対象ウィンドウが未解決の場合、`list_windows` → `resolve_target` で解決
2. `focus_window` でウィンドウを前面に
3. 指定されたセレクタで `click` を実行
4. クリック後に `screenshot` で結果を確認
5. 必要に応じて `list_controls` で変化を確認

セレクタの指定方法:
- automation_id: 例 "SaveButton"
- name + control_type: 例 "OK" Button
- 曖昧な場合は先に list_controls で候補を確認してからクリック

---

## type モード（テキスト入力）

UI要素にテキストを入力して値を検証する。

手順:
1. 対象ウィンドウが未解決の場合、`list_windows` → `resolve_target` で解決
2. `focus_window` でウィンドウを前面に
3. 指定されたセレクタで `type_text` を実行
4. 入力後に `read_text` で値を検証
5. `screenshot` で結果を確認

セレクタとテキストの指定方法:
- 例: "ServerUrlTextBox に http://localhost:8080 を入力"
- 例: "ユーザー名フィールド(automation_id=UsernameBox)に admin を入力"

---

## セレクタの優先順位
1. `automation_id` (最も安定)
2. `name` + `control_type`
3. `bounding_rect` の中心クリック (最後の手段)
