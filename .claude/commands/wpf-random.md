WPF UI自動化エージェントでランダム（探索）テストを実行してください。

手順:
1. profiles.json からプロファイルを確認
2. 以下のコマンドを実行:

```bash
wpf-agent random run --profile <profile> --max-steps <steps> --seed <seed>
```

または設定YAMLがある場合:
```bash
wpf-agent random run --config <config.yaml>
```

3. 結果を確認し、失敗があればチケットの内容を表示
4. 再現する場合は seed を使ってリプレイ方法を案内

指示: $ARGUMENTS

デフォルト値:
- max-steps: 200
- seed: 自動生成（ログに記録）
- 安全設定: profiles.json に従う（デフォルトで破壊的操作ブロック）

失敗時:
- artifacts/tickets/ にチケットが自動生成される
- `wpf-agent tickets open --last` で最新チケットを確認可能
- `wpf-agent replay --file <actions.json> --profile <profile>` で再現可能
