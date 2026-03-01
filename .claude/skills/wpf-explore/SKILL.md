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

### 1. ターゲット特定
```bash
# 方法A: 未起動 → launch で起動し PID を取得
wpf-agent launch --exe <path>

# 方法B: 起動済み → ウィンドウ一覧から PID を探す
wpf-agent ui windows --brief

# 方法C: プロセス名から PID を取得
wpf-agent ui alive --process <name> --brief
```

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
# 全コントロール (JSON)
wpf-agent ui controls --pid <pid> --depth 4

# フィルタ付き (1行で完結、python パイプ不要)
wpf-agent ui controls --pid <pid> --depth 4 --has-aid --brief
wpf-agent ui controls --pid <pid> --depth 6 --type-filter ListItem,TreeItem,DataItem --brief
wpf-agent ui controls --pid <pid> --depth 4 --type-filter Button,Edit,ComboBox --has-name --brief
```
フィルタオプション: `--type-filter` (カンマ区切り), `--name-filter` (部分一致), `--has-name`, `--has-aid`, `--brief` (テーブル出力)。

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

### 4. チケット作成（必須 — スキップ禁止）

探索が完了したら（中断された場合も含め）、**必ず以下の CLI コマンドでチケットを作成する**。
問題が見つからなかった場合も「問題なし」のチケットを作成する。

#### a. エビデンスのスクリーンショットを保存
```bash
wpf-agent ui screenshot --pid <pid> --save artifacts/sessions/explore_evidence.png
```

#### b. 探索結果を整理して以下を決定
- **title**: 問題ありなら具体的に (`ボタンクリック後にステータスが更新されない`) / 問題なしなら `UI探索テスト完了 — 問題なし (<アプリ名>)`
- **summary**: 1-2文の概要
- **actual**: 実際に起きたこと
- **expected**: 期待される動作
- **repro**: 再現手順 (wpf-agent ui コマンドで記述)
- **evidence**: スクリーンショットのパス
- **hypothesis**: 原因の仮説 (問題なしなら空)

#### c. CLI でチケットを作成
```bash
wpf-agent tickets create --title "タイトル" --summary "概要" --actual "実際の結果" --expected "期待される結果" --repro "ステップ1" --repro "ステップ2" --evidence "artifacts/sessions/explore_evidence.png" --hypothesis "原因の仮説" --pid <pid>
```
**注意**: 全引数を1行で記述すること。`--repro` と `--evidence` は複数回指定可能。

### 5. アプリ終了（launch で起動した場合）
```bash
wpf-agent ui close --pid <pid>
```
`wpf-agent launch` で起動したプロセスのみ閉じられる (WM_CLOSE)。手動で起動したアプリはユーザーに閉じてもらう。

### 6. ユーザーへの報告

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
2. **それまでの結果で `wpf-agent tickets create` を実行する**（手順4へ進む）
3. ユーザーに報告する

読み取り専用コマンド (`screenshot`, `controls`, `read`, `state`) は一時停止中も実行可能。

## 注意事項
- 各ステップでスクリーンショットを保存し、変化を追跡すること
- プロセスの生存確認は `wpf-agent ui alive --pid <pid>` を使う（`tasklist | findstr` は不要）
- アプリがクラッシュした場合は再起動して続行
- 破壊的操作（削除ボタン等）は慎重に判断すること
- **チケット作成をスキップしないこと** — 探索の成果物として必ず残す
- **Bash コマンドは必ず1行で記述する** — パーミッション glob `*` は改行にマッチしないため、複数行コマンドは毎回確認プロンプトが出る。複雑な処理は `wpf-agent` CLI サブコマンド（例: `wpf-agent tickets create`）を使う
