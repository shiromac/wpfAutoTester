---
name: wpf-ticket
description: 生成されたチケットの確認・分析
---

WPF UI自動化エージェントで生成されたチケットを確認・管理してください。

手順:
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

指示: $ARGUMENTS
