---
name: wpf-verify
description: ビルド後の自動検証（起動→スモークテスト→UIチェック→スクショ→レポート）
argument-hint: exe path
---

WPF アプリをビルドして自動検証を実行してください。

## 基本フロー

### 1. ビルド
対象アプリのビルドコマンドを実行:
```bash
# .NET の場合
dotnet build <project.csproj> -c Debug

# MSBuild の場合
msbuild <project.sln> /p:Configuration=Debug
```

ビルドが失敗した場合はエラーを修正してリトライしてください。

### 2. スモークテスト（最小検証）
ビルド成功後、実行ファイルのパスを特定して:
```bash
wpf-agent verify --exe <path/to/App.exe>
```

これだけで以下を自動確認:
- アプリが起動する
- ウィンドウが表示される
- UIが応答する（フリーズしていない）
- エラーダイアログが出ていない
- スクリーンショットとコントロール一覧を保存

### 3. 詳細検証（spec YAML指定時）
特定の要素や操作を検証する場合:
```bash
wpf-agent verify --exe <path/to/App.exe> --spec verify-spec.yaml
```

### 4. 結果の解釈
- **VERIFICATION PASSED**: 全チェック合格
- **VERIFICATION FAILED**: 問題あり → 失敗内容を分析してコード修正を提案

### 5. チケット作成（必須 — スキップ禁止）

検証結果に関わらず、**必ず以下の CLI コマンドでチケットを作成する**。

#### a. 検証結果を整理して以下を決定
- **title**: PASSED なら `検証完了 — 全チェック合格 (<アプリ名>)` / FAILED なら具体的な失敗を記述
- **summary**: 検証対象 exe と結果の要約
- **actual**: 実際の検証結果
- **expected**: 期待される動作
- **evidence**: verify で保存されたスクリーンショットのパス

#### b. CLI でチケットを作成
```bash
wpf-agent tickets create --title "タイトル" --summary "概要" --actual "実際の結果" --expected "期待される結果" --evidence "スクリーンショットパス" --hypothesis "原因の仮説"
```
**注意**: 全引数を1行で記述すること。

### 6. 失敗時のデバッグフロー
1. 失敗した check の名前とメッセージを確認
2. セッションディレクトリのスクリーンショットを確認
3. UIA スナップショット (JSON) でコントロール一覧を確認
4. 原因を特定してコードを修正
5. 再度ビルド → verify を繰り返す

## オプション
- `--title-re <regex>`: ウィンドウタイトルで特定（複数ウィンドウ環境用）
- `--timeout <ms>`: 起動待機時間（デフォルト5000ms）
- `--no-close`: 検証後もアプリを開いたままにする（手動確認用）

## Verification Spec YAML フォーマット
```yaml
app:
  exe: "bin/Debug/net8.0-windows/MyApp.exe"
  args: []
  title_re: "MyApp.*"
  startup_wait_ms: 5000

expected_controls:
  - selector: {automation_id: "MainButton"}
    expect: {exists: true, enabled: true}
  - selector: {automation_id: "StatusLabel"}
    expect: {exists: true, text: "Ready"}

interactions:
  - name: "ボタンクリックでステータス変更"
    action: click
    selector: {automation_id: "MainButton"}
    after:
      - selector: {automation_id: "StatusLabel"}
        expect: {text: "Clicked"}
```

## 注意事項
- **チケット作成をスキップしないこと** — 検証の成果物として必ず残す
- スクリーンショットはチケットディレクトリにコピーすること
- **Bash コマンドは必ず1行で記述する** — パーミッション glob `*` は改行にマッチしないため、複数行コマンドは毎回確認プロンプトが出る。複雑な処理は `wpf-agent` CLI サブコマンド（例: `wpf-agent tickets create`）を使う

指示: $ARGUMENTS
