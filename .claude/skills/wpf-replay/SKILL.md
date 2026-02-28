---
name: wpf-replay
description: 記録されたアクションのAI不要リプレイ再現
---

WPF UI自動化エージェントで記録されたアクションをリプレイ（AI不要の再現）してください。

手順:
1. リプレイ対象のアクションファイルを特定
   - 指定がない場合: 最新のセッションの `actions.json` を探す
   - artifacts/sessions/ 以下を確認
2. 対象プロファイルを確認
3. 以下を実行:

```bash
wpf-agent replay --file <actions.json> --profile <profile>
```

または PID / タイトル指定:
```bash
wpf-agent replay --file <actions.json> --pid <pid>
wpf-agent replay --file <actions.json> --title-re ".*MyApp.*"
```

4. リプレイ結果（成功/エラー数）を報告

指示: $ARGUMENTS
