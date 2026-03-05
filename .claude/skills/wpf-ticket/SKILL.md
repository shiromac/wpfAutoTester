---
name: wpf-ticket
description: チケット管理（確認・作成・整理）
argument-hint: "[create|triage|view] params"
---

WPF UI自動化エージェントのチケットを管理してください。

指示: $ARGUMENTS

## モード判定

引数からモードを自動判定する:
- **create モード**: "create" / "作成"
- **triage モード**: "triage" / "整理" / "分類"
- **view モード**: それ以外（--last, ID指定, 引数なし）

---

## view モード（チケット確認・分析）

### 手順
1. 最新のチケットを表示する場合:
```bash
wpf-agent tickets open --last
```

2. 特定セッションのチケットを表示:
```bash
wpf-agent tickets open --session <session-id>
```

3. 全チケット一覧:
```bash
wpf-agent tickets open
```

4. チケットの内容を読み、以下を要約して報告:
   - タイトルとサマリー
   - 再現手順
   - 実際の結果 vs 期待結果
   - 根本原因仮説
   - 添付されたスクリーンショットやUIA差分の有無

5. 必要に応じて UIA diff (uia/diff.json) を読んで変化を分析

---

## create モード（チケット作成）

### 1. 問題情報を整理
以下の情報を会話コンテキストから収集する:
- 問題のタイトル (簡潔に)
- 概要 (1-2文)
- 再現手順 (`wpf-agent ui` コマンドで記述)
- 実際の結果
- 期待される結果
- 原因の仮説

### 2. エビデンス収集
```bash
wpf-agent ui screenshot --pid <pid> --save artifacts/sessions/ticket_evidence.png
wpf-agent ui controls --pid <pid> --depth 4
```

### 3. チケット生成
```bash
wpf-agent tickets create --title "<タイトル>" --summary "<概要>" --actual-result "<実際の結果>" --expected-result "<期待される結果>" --repro-steps "<ステップ1>" --repro-steps "<ステップ2>" --evidence "artifacts/sessions/ticket_evidence.png" --root-cause "<原因の仮説>" --pid <pid> --process "<プロセス名>" --profile "<プロファイル名>"
```
`--repro` と `--evidence` は複数回指定可能。**全引数を1行で記述すること。**

### 4. 結果をユーザーに報告
- チケットのパスを表示
- ticket.md の内容を表示
- 次のアクション (コード修正の提案等) があれば提示

### チケット構造
```
artifacts/tickets/TICKET-<timestamp>/
├── ticket.md              <- Markdown チケット
├── ticket.json            <- 機械可読 JSON
└── screens/               <- スクリーンショット (--evidence で自動コピー)
```

---

## triage モード（チケット整理）

### 1. 未分類チケット一覧を取得
```bash
wpf-agent tickets list-pending
```
チケットがなければ「未分類チケットはありません」と報告して終了。

### 2. 各チケットの内容を確認
一覧に含まれる各チケットの `ticket.md` を Read ツールで読み、タイトル/概要/実際の結果/期待される結果/根本原因仮説を把握する。

### 3. 判断

#### 自動モード (auto / 引数なし)
以下の基準で AI が判断する:

**fix (修正対象):**
- クラッシュ / プロセス終了
- UI フリーズ / デッドロック
- エラーダイアログ表示
- アサーション失敗で明確な不具合
- データ損失や不整合

**wontfix (修正しない):**
- テスト自体の誤検知 (false positive)
- 仕様通りの動作
- 再現不能 / 環境依存の一時的問題
- 軽微な表示揺れ

**判断できない場合:** AskUserQuestion でユーザーに確認する。

#### 手動モード (manual)
各チケットについて概要を表示し、AskUserQuestion で `fix` / `wontfix` を選択してもらう。

### 4. 分類を実行
```bash
wpf-agent tickets triage --ticket <ticket_dir_path> --decision fix --reason "クラッシュ: 未処理例外"
wpf-agent tickets triage --ticket <ticket_dir_path> --decision wontfix --reason "仕様通りの動作"
```

### 5. 結果サマリ
全チケットの処理が完了したら、テーブル形式でサマリを表示する。

---

## 注意事項
- 再現手順には必ず `wpf-agent ui` コマンドを含めること
- スクリーンショットは必ず保存すること
- **Bash コマンドは必ず1行で記述する**
