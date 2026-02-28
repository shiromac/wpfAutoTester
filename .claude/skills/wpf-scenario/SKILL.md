---
name: wpf-scenario
description: シナリオテストの実行またはYAML定義の作成
---

WPF UI自動化エージェントでシナリオテストを実行してください。

以下のいずれかの方法で実行します:

## 方法A: YAMLファイルからの実行
scenariosディレクトリ内のYAMLファイルを指定された場合:
```bash
wpf-agent scenario run --file <scenario.yaml> --profile <profile>
```

## 方法B: 指示からの対話的実行
YAMLファイルが指定されていない場合:
1. `list_windows` → `resolve_target` で対象アプリを特定
2. `focus_window` でフォーカス
3. ユーザーの指示に従って各ステップを実行:
   - `click`, `type_text`, `select_combo`, `toggle` 等
   - 各ステップ後に `screenshot` / `read_text` / `get_state` で検証
4. 期待結果が満たされない場合はその旨を報告
5. 全ステップのアクション記録をJSON形式で出力（リプレイ用）

## 方法C: シナリオYAMLの生成
「シナリオを作成して」と指示された場合:
1. 対象アプリのUIを `list_controls` で調査
2. ユーザーの指示からステップと期待結果を構成
3. scenarios/ にYAMLファイルを生成

指示: $ARGUMENTS
