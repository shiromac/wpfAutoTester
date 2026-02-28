---
name: wpf-explore
description: AI誘導型探索テスト（Claude Codeが直接UIを見て操作・判断するループ）
argument-hint: goal or app path
---

WPF アプリの AI 誘導型探索テストを実行してください。
Claude Code 自身がスクリーンショットを見て判断し、`wpf-agent ui` コマンドで直接操作します。
外部 API キー (ANTHROPIC_API_KEY) は不要です。

指示: $ARGUMENTS

## 探索手順

### 1. アプリ起動
```bash
wpf-agent launch --exe <path>
```
出力から PID を取得する。既に起動済みなら `--pid` で直接指定も可。

### 2. ウィンドウフォーカス
```bash
wpf-agent ui focus --pid <pid>
```

### 3. 探索ループ（以下を繰り返す）

#### a. スクリーンショット撮影
```bash
wpf-agent ui screenshot --pid <pid> --save artifacts/sessions/explore_step_N.png
```

#### b. スクリーンショットを確認
Read ツールで画像ファイルを読み込み、画面の状態を視覚的に把握する。

#### c. コントロール一覧取得
```bash
wpf-agent ui controls --pid <pid> --depth 4
```
JSON 出力から automation_id, name, control_type, enabled, visible を確認。

#### d. 次の操作を判断
- まだ触っていないボタン、メニュー、タブを優先
- テキスト入力欄にはテスト値を入力
- チェックボックスはトグル
- エラーダイアログや異常な状態を発見したら記録

#### e. 操作実行
```bash
# クリック
wpf-agent ui click --pid <pid> --aid <automation_id>

# テキスト入力
wpf-agent ui type --pid <pid> --aid <automation_id> --text "テスト値"

# トグル
wpf-agent ui toggle --pid <pid> --aid <automation_id>

# テキスト読み取り
wpf-agent ui read --pid <pid> --aid <automation_id>

# 状態確認
wpf-agent ui state --pid <pid> --aid <automation_id>
```

#### f. 操作結果を確認
再度スクリーンショットを撮影し、期待通りの変化があったか確認する。
問題（クラッシュ、表示崩れ、予期せぬエラー）を発見したら記録する。

### 4. チケット作成（必須）

探索が完了したら（中断された場合も含め）、**必ず** `/wpf-ticket-create` スキルを呼び出してチケットを作成する。
問題が見つからなかった場合も「問題なし」のチケットを作成する。

呼び出し例:
```
/wpf-ticket-create UI探索テスト完了。探索した要素: MainButton, InputField, OptionCheck。結果: 全操作正常、問題なし。
```

```
/wpf-ticket-create ボタンクリック後にステータスラベルが更新されない。MainButton をクリックしたが StatusLabel が "Ready" のまま変化しなかった。
```

#### チケットタイトルのルール
- **問題あり**: 具体的な問題を記述 (例: `ボタンクリック後にステータスが更新されない`)
- **問題なし**: `UI探索テスト完了 — 問題なし (<アプリ名>)` の形式

### 5. ユーザーへの報告

チケット作成後、以下を表示する:
- チケットのパス
- 探索したUI要素の一覧
- 実行した操作のサマリ
- 発見した問題（あれば）
- スクリーンショットのパス一覧

## セレクタの優先順位
1. `--aid` (automation_id) — 最も安定
2. `--name` + `--control-type` — aid がない場合
3. スクリーンショットの座標情報から判断 — 最後の手段

## ユーザー中断の対応 (UI ガード)

UI 操作コマンド (`focus`, `click`, `type`, `toggle`) は実行前にマウス移動を検知する。
ユーザーがマウスを動かすと操作は中断され、exit code 2 + JSON が返る:
```json
{"interrupted": true, "reason": "mouse_movement", "detail": "...", "command": "click", "action": "Run 'wpf-agent ui resume' to continue."}
```

**中断を検知したら:**
1. 探索ループを即座に停止する
2. **それまでの結果でチケットを作成する**（手順4へ進む）
3. ユーザーに報告する

読み取り専用コマンド (`screenshot`, `controls`, `read`, `state`) は一時停止中も実行可能。

## 注意事項
- 各ステップでスクリーンショットを保存し、変化を追跡すること
- アプリがクラッシュした場合は再起動して続行
- 破壊的操作（削除ボタン等）は慎重に判断すること
- **チケット作成をスキップしないこと** — 探索の成果物として必ず残す
