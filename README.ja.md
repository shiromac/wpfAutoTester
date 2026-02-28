# WPF UI デバッグ自動化エージェント

Claude Code と統合された WPF UI 自動化エージェントです。シナリオテスト、ランダム探索テスト、チケット自動生成、AI不要リプレイをサポートします。

## クイックスタート

```powershell
# ワンコマンドセットアップ
powershell -ExecutionPolicy Bypass -File setup.ps1
```

または手動で:

```bash
pip install -e .[dev]
wpf-agent init
```

## MCP サーバー登録

Claude Code に MCP サーバーを登録します:

```bash
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

または Claude Code の MCP 設定ファイルに直接追加:

```json
{
  "mcpServers": {
    "wpf-agent": {
      "command": "python",
      "args": ["-m", "wpf_agent", "mcp-serve"]
    }
  }
}
```

## 使い方

### プロファイルでアプリを指定

`profiles.json` に対象アプリの情報を設定してから実行します:

```bash
wpf-agent run --profile MyApp-Dev
```

### アタッチ / 起動

```bash
# 実行中のプロセスに PID で接続
wpf-agent attach --pid 12345

# EXE を起動して接続
wpf-agent launch --exe "C:/path/MyApp.exe" -- --dev-mode
```

### シナリオテスト

YAML で定義されたテストシナリオを実行します。期待結果と異なる場合はチケットが自動生成されます。

```bash
wpf-agent scenario run --file scenarios/demo_a_settings.yaml --profile MyApp
```

### ランダム（探索）テスト

seed ベースの決定的ランダムテストを実行します。クラッシュや UI 異常を検出するとチケットを生成します。

```bash
wpf-agent random run --profile MyApp --max-steps 200 --seed 42
```

### リプレイ（AI 不要）

記録されたアクションシーケンスを AI なしで再実行します:

```bash
wpf-agent replay --file artifacts/sessions/<session-id>/actions.json --profile MyApp
```

### チケット確認

```bash
# 最新のチケットを表示
wpf-agent tickets open --last

# 全チケット一覧
wpf-agent tickets open
```

## MCP ツール一覧（13個）

Claude Code から呼び出せるツールです:

| ツール | 説明 |
|--------|------|
| `list_windows` | 表示中のトップレベルウィンドウ一覧を取得 |
| `resolve_target` | PID / プロセス名 / EXEパス / タイトル正規表現でアプリを特定 |
| `focus_window` | 対象ウィンドウを最前面に移動 |
| `wait_window` | ウィンドウの出現を待機 |
| `list_controls` | UIA コントロールツリーを列挙 |
| `click` | UI 要素をクリック |
| `type_text` | UI 要素にテキストを入力 |
| `select_combo` | コンボボックスの項目を選択 |
| `toggle` | チェックボックス / トグルボタンの切り替え |
| `read_text` | UI 要素のテキストを読み取り |
| `get_state` | UI 要素の状態（enabled / visible / value 等）を取得 |
| `screenshot` | スクリーンショットを撮影（PNG保存） |
| `wait_for` | UI 条件の成立を待機（exists / enabled / text_equals 等） |

## プロファイル設定

`profiles.json` を編集して対象アプリを登録します:

```json
[
  {
    "name": "MyApp-Dev",
    "match": {
      "process": "MyApp.exe"
    },
    "launch": {
      "exe": "C:/path/MyApp.exe",
      "args": ["--dev"]
    },
    "timeouts": {
      "startup_ms": 15000,
      "default_ms": 10000,
      "screenshot_ms": 5000
    },
    "safety": {
      "allow_destructive": false,
      "destructive_patterns": ["delete", "remove", "exit", "quit", "close"],
      "require_double_confirm": true
    }
  }
]
```

### ターゲット指定方法（優先順位順）

1. **PID** — 最も確実。`"match": {"pid": 12345}`
2. **プロセス名** — `"match": {"process": "MyApp.exe"}`
3. **EXE パス** — 起動モード。`"launch": {"exe": "C:/path/MyApp.exe", "args": ["--dev"]}`
4. **タイトル正規表現** — `"match": {"title_re": ".*MyApp.*"}`

### 安全設定

デフォルトでは破壊的操作（削除 / 終了 / 外部送信等）はブロックされます。明示的に許可する場合:

```json
{
  "safety": {
    "allow_destructive": true,
    "require_double_confirm": true
  }
}
```

## シナリオ定義（YAML）

```yaml
id: my-scenario
title: "設定画面テスト"
tags: [smoke, settings]
profile: MyApp-Dev

steps:
  - action: focus_window
    selector: {}
    args: {}

  - action: click
    selector:
      automation_id: SettingsButton
    expected:
      - type: exists
        selector:
          automation_id: SettingsPanel

  - action: type_text
    selector:
      automation_id: ServerUrlTextBox
    args:
      text: "http://localhost:1234"
    expected:
      - type: text_equals
        selector:
          automation_id: ServerUrlTextBox
        value: "http://localhost:1234"

  - action: click
    selector:
      automation_id: SaveButton
    expected:
      - type: exists
        selector:
          automation_id: SavedIndicator
```

### 使用可能なアサーション

| アサーション | 説明 |
|---|---|
| `exists` | 要素が存在するか |
| `text_equals` | テキストが一致するか |
| `text_contains` | テキストを含むか |
| `enabled` | 有効状態か |
| `visible` | 表示状態か |
| `selected` | 選択状態か |
| `value_equals` | 値が一致するか |
| `regex` | テキストが正規表現にマッチするか |

## チケット出力

テスト失敗時に自動生成されるチケットの構成:

```
artifacts/tickets/<session-id>/TICKET-<timestamp>-<id>/
  ticket.md           # チケット本文（再現手順 / 実結果 / 期待結果 / 根本原因仮説）
  ticket.json          # 機械可読形式
  repro.actions.json   # リプレイ用アクションシーケンス
  runner.log           # 実行ログ
  screens/             # スクリーンショット
  uia/                 # UIA スナップショット + 差分
```

## プロジェクト構成

```
src/wpf_agent/
  core/       # ターゲットレジストリ、セッション管理、安全チェック、例外
  uia/        # UIAEngine、セレクタ、スナップショット、スクリーンショット、待機
  mcp/        # FastMCP サーバー（13ツール）、Pydantic 型定義
  runner/     # エージェントループ、リプレイ、構造化ログ
  testing/    # シナリオテスト、ランダムテスト、アサーション、障害オラクル、最小化
  tickets/    # チケット生成、Markdown テンプレート、証跡収集
scenarios/    # YAML シナリオ定義
artifacts/    # セッションとチケット（実行時生成）
tests/        # ユニットテスト
```

## 実行ファイルのビルド

```bash
pip install pyinstaller
pyinstaller wpf_agent.spec
```

`dist/wpf-agent.exe` が生成されます。

## 動作要件

- Windows 10 / 11
- Python 3.10 以上
- 対象アプリ: WPF（.NET 8 推奨、UIA 対応であれば .NET バージョン問わず）
