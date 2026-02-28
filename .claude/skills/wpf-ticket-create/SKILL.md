---
name: wpf-ticket-create
description: 探索テストで発見した問題のチケットを作成（ticket.md + ticket.json + エビデンス）
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
# スクリーンショット (対象アプリが起動中なら)
wpf-agent ui screenshot --pid <pid> --save artifacts/sessions/ticket_evidence.png

# コントロール一覧 (JSON)
wpf-agent ui controls --pid <pid> --depth 4
```

### 3. チケット生成
Python でチケットを生成する:
```python
python -c "
import json, pathlib, time
from wpf_agent.tickets.templates import render_ticket_md, default_environment

env = default_environment()
env['Target PID'] = '<pid>'
env['Target Process'] = '<process>'
env['Profile'] = '<profile>'

md = render_ticket_md(
    title='<タイトル>',
    summary='<概要>',
    repro_steps=[
        '<ステップ1>',
        '<ステップ2>',
    ],
    actual_result='<実際の結果>',
    expected_result='<期待される結果>',
    environment=env,
    evidence_files=['<ファイルリスト>'],
    root_cause_hypothesis='<原因の仮説>',
)

# チケットディレクトリ作成
ts = time.strftime('%Y%m%d-%H%M%S')
ticket_dir = pathlib.Path('artifacts/tickets') / f'TICKET-{ts}'
ticket_dir.mkdir(parents=True, exist_ok=True)

# ticket.md 書き出し
(ticket_dir / 'ticket.md').write_text(md, encoding='utf-8')

# ticket.json 書き出し (機械可読)
ticket_data = {
    'title': '<タイトル>',
    'summary': '<概要>',
    'repro_steps': ['<ステップ>'],
    'actual_result': '<実際の結果>',
    'expected_result': '<期待される結果>',
    'environment': env,
    'timestamp': ts,
}
(ticket_dir / 'ticket.json').write_text(
    json.dumps(ticket_data, indent=2, ensure_ascii=False), encoding='utf-8'
)
print(f'Ticket created: {ticket_dir}')
print(md)
"
```

### 4. エビデンスファイルのコピー
スクリーンショットや UIA スナップショットをチケットディレクトリに集約:
```bash
# screens/ にスクリーンショットをコピー
mkdir -p <ticket_dir>/screens
cp artifacts/sessions/<関連スクショ>.png <ticket_dir>/screens/

# uia/ にスナップショットをコピー (あれば)
mkdir -p <ticket_dir>/uia
```

### 5. 結果をユーザーに報告
- チケットのパスを表示
- ticket.md の内容を表示
- 次のアクション (コード修正の提案等) があれば提示

## チケット構造
```
artifacts/tickets/TICKET-<timestamp>/
├── ticket.md              ← Markdown チケット
├── ticket.json            ← 機械可読 JSON
├── screens/               ← スクリーンショット
└── uia/                   ← UIA スナップショット・diff
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
| UIA Diff | 障害前後の UI 要素差分 (あれば) |

## 注意事項
- 再現手順には必ず `wpf-agent ui` コマンドを含めること (`wpf-agent replay` で再現可能にする)
- スクリーンショットは必ず保存すること
- チケット内容はユーザーに表示して確認を促すこと
