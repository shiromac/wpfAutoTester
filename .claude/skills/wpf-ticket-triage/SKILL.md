---
name: wpf-ticket-triage
description: 未分類チケットの整理（fix / wontfix に分類して移動）
argument-hint: "[auto|manual]"
---

未分類チケットを「修正する (fix)」「修正しない (wontfix)」に分類してください。

モード: $ARGUMENTS (デフォルト: auto)

## 手順

### 1. 未分類チケット一覧を取得

```bash
wpf-agent tickets list-pending
```

チケットがなければ「未分類チケットはありません」と報告して終了。

### 2. 各チケットの内容を確認

一覧に含まれる各チケットの `ticket.md` を Read ツールで読み、以下を把握する:
- タイトル / 概要
- 実際の結果 (actual_result)
- 期待される結果 (expected_result)
- 根本原因仮説

### 3. 判断

#### 自動モード (auto / 引数なし)

以下の基準で AI が判断する:

**→ `fix` (修正対象):**
- クラッシュ / プロセス終了が発生
- UI フリーズ / デッドロックが発生
- エラーダイアログが表示された
- アサーション失敗で明確な不具合がある
- データ損失や不整合が発生

**→ `wontfix` (修正しない):**
- テスト自体の誤検知 (false positive)
- 仕様通りの動作
- 再現不能 / 環境依存の一時的問題
- 軽微な表示揺れ (テスト精度の問題)

**→ 判断できない場合:**
- AskUserQuestion でユーザーに確認する
- チケットの概要と判断材料を提示する

#### 手動モード (manual)

各チケットについて:
1. チケットの概要を表示する
2. AskUserQuestion でユーザーに `fix` / `wontfix` を選択してもらう
3. 必要に応じて理由を入力してもらう

### 4. 分類を実行

判断結果に基づいて CLI でチケットを移動する:

```bash
# 修正対象
wpf-agent tickets triage --ticket <ticket_dir_path> --decision fix --reason "クラッシュ: 未処理例外"

# 修正しない
wpf-agent tickets triage --ticket <ticket_dir_path> --decision wontfix --reason "仕様通りの動作"
```

### 5. 結果サマリ

全チケットの処理が完了したら、以下のサマリを表示する:

| チケット | 判断 | 理由 |
|---------|------|------|
| TICKET-xxx | fix | クラッシュ検出 |
| TICKET-yyy | wontfix | 仕様通り |

合計: fix N件 / wontfix N件

## 分類後のディレクトリ構造

```
artifacts/tickets/
├── fix/                    ← 修正対象
│   └── TICKET-xxx/
├── wontfix/                ← 修正しない
│   └── TICKET-xxx/
└── {session_id}/           ← 未分類 (従来通り)
    └── TICKET-xxx/
```
