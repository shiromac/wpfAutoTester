---
name: wpf-ticket-create
description: 探索テストで発見した問題のチケットを作成（ticket.md + ticket.json + エビデンス）
argument-hint: issue description
---

探索テストやUI操作中に発見した問題のチケットを作成してください。

指示: $ARGUMENTS

## チケット作成手順

### 1. 問題情報を整理
以下の情報を会話コンテキストから収集する:
- 問題のタイトル (簡潔に)
- 概要 (1-2文)
- 再現手順 (`wpf-agent ui` コマンドで記述)
- 実際の結果
- 期待される結果
- 原因の仮説

### 2. エビデンス収集
問題発生時のスクリーンショットやコントロール情報を集める:
```bash
wpf-agent ui screenshot --pid <pid> --save artifacts/sessions/ticket_evidence.png
wpf-agent ui controls --pid <pid> --depth 4
```

### 3. チケット生成
CLI コマンドで作成する:
```bash
wpf-agent tickets create --title "<タイトル>" --summary "<概要>" --actual "<実際の結果>" --expected "<期待される結果>" --repro "<ステップ1>" --repro "<ステップ2>" --evidence "artifacts/sessions/ticket_evidence.png" --hypothesis "<原因の仮説>" --pid <pid> --process "<プロセス名>" --profile "<プロファイル名>"
```

`--repro` と `--evidence` は複数回指定可能。

### 4. 結果をユーザーに報告
- チケットのパスを表示
- ticket.md の内容を表示
- 次のアクション (コード修正の提案等) があれば提示

## チケット構造
```
artifacts/tickets/TICKET-<timestamp>/
├── ticket.md              ← Markdown チケット
├── ticket.json            ← 機械可読 JSON
└── screens/               ← スクリーンショット (--evidence で自動コピー)
```

## ticket.md セクション
| セクション | 内容 |
|---|---|
| Summary | 問題の概要 |
| Repro Steps | 再現手順 (wpf-agent コマンド付き) |
| Actual Result | 実際に起きたこと |
| Expected Result | 期待される動作 |
| Environment | OS, Python, PID, プロセス名等 |
| Evidence | エビデンスファイル一覧 |
| Root Cause Hypothesis | 原因の推測 |

## 注意事項
- 再現手順には必ず `wpf-agent ui` コマンドを含めること (`wpf-agent replay` で再現可能にする)
- スクリーンショットは必ず保存すること
- チケット内容はユーザーに表示して確認を促すこと
- **Bash コマンドは必ず1行で記述する** — パーミッション glob `*` は改行にマッチしないため、複数行コマンドは毎回確認プロンプトが出る
