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

### 5. チケット作成（必須）

検証結果に関わらず、**必ず** `/wpf-ticket-create` スキルを呼び出してチケットを作成する。

呼び出し例:
```
/wpf-ticket-create 検証完了 — 全チェック合格。exe: bin/Debug/net9.0-windows/MyApp.exe。起動OK、UI応答OK、エラーダイアログなし。
```

```
/wpf-ticket-create 起動後にUIが応答しない。wpf-agent verify --exe bin/Debug/net9.0-windows/MyApp.exe で responsive チェックが FAIL。
```

#### チケットタイトルのルール
- **PASSED**: `検証完了 — 全チェック合格 (<アプリ名>)`
- **FAILED**: 具体的な失敗を記述 (例: `起動後にUIが応答しない`)

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

指示: $ARGUMENTS
