# WPF UI デバッグ自動化エージェント

> **Windows 10/11 必須** | Python 3.10+

Claude Code と統合された AI 駆動型 WPF UI テストエージェント。Claude がスクリーンショットを見て UI を理解し、自律的にアプリを探索・テストし、発見した問題を自動修正します。

## 主な機能

- **AI 誘導型探索** — Claude Code がスクリーンショットを見て操作を判断し、自律的にバグを発見 (`/wpf-explore`)
- **自動修正ループ** — ビルド→検証→問題発見→コード修正→再ビルドを AI が自動実行 (`/wpf-verify`)
- **シナリオテスト** — YAML 定義のテストシナリオ、アサーション、チケット自動生成
- **ランダムテスト** — seed 再現可能なランダム探索、クラッシュ・異常検出
- **AI 不要リプレイ** — 記録されたアクションを API 不要で再実行
- **チケット自動生成** — スクリーンショット、UIA スナップショット、再現手順付きバグチケット
- **UI 安全ガード** — マウス移動検知で自動化を一時停止

## インストール

```bash
pip install git+https://github.com/shiromac/wpfAutoTester.git
```

開発用:

```bash
git clone https://github.com/shiromac/wpfAutoTester.git
cd wpfAutoTester
pip install -e .[dev]
```

## クイックスタート

```bash
# 初期化
wpf-agent init

# Claude Code スキルをインストール (/wpf-explore, /wpf-verify 等)
wpf-agent install-skills

# Claude Code に MCP サーバーを登録
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

## 使い方

### AI 誘導型探索（メイン機能）

Claude Code がアプリを直接操作してテスト — UI コマンドに ANTHROPIC_API_KEY は不要:

```
/wpf-explore 設定画面のボタンと入力欄をすべてテスト
```

探索ループ:
1. スクリーンショットを撮影して確認
2. UI コントロール一覧を取得 (automation ID, 名前, 種類)
3. 視覚的な理解に基づいて次の操作を決定
4. 操作を実行 (`click`, `type`, `toggle`)
5. スクリーンショットで結果を検証
6. 発見した問題を報告

### ビルド＆自動検証

ビルド後にアプリを自動検証:

```bash
wpf-agent verify --exe bin/Debug/net9.0-windows/MyApp.exe
```

spec ファイルで詳細チェック:

```bash
wpf-agent verify --exe bin/Debug/net9.0-windows/MyApp.exe --spec verify-spec.yaml
```

検証失敗時、Claude Code がレポートを読み、コードを修正し、再ビルド・再検証します。

### プロファイルでアプリを指定

```bash
# profiles.json に対象アプリの情報を設定してから実行:
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

```bash
wpf-agent scenario run --file scenarios/demo_a_settings.yaml --profile MyApp
```

### ランダムテスト

```bash
wpf-agent random run --profile MyApp --max-steps 200 --seed 42
```

### ユーザビリティテスト（ペルソナ型）

ペルソナを設定して思考発話法でユーザビリティテストを実行:

```
/wpf-usability-test --pid 12345 --goal "カウンターを5にする"
/wpf-usability-test --pid 12345 --goal "設定を保存する" --persona suzuki
/wpf-usability-test --exe path/to/App.exe --goal "設定を保存する" --persona "大学生、ITに強い、せっかち"
```

`--persona` にはプリセット名（`tanaka`, `suzuki`, `sato` 等）またはインラインテキストを指定できます。省略時は `tanaka` がデフォルト。

Claude がペルソナになりきって思考を口に出しながらゴール達成を試みます。問題点・重大度・改善提案を含むユーザビリティ報告書を生成します。

### リプレイ（AI 不要）

```bash
wpf-agent replay --file artifacts/sessions/<session-id>/actions.json --profile MyApp
```

### チケット管理

```bash
# CLI でチケット作成
wpf-agent tickets create --title "ボタンクリックでクラッシュ" --summary "保存ボタン押下時に異常終了" \
  --actual-result "クラッシュ" --expected-result "正常保存" --repro-steps "MainButton をクリック" --pid 1234

# 最新のチケットを表示
wpf-agent tickets open --last

# 全チケット一覧
wpf-agent tickets open

# 未分類チケット一覧
wpf-agent tickets list-pending

# 分類: fix または wontfix に移動
wpf-agent tickets triage --ticket <path> --decision fix --reason "クラッシュ検出"
wpf-agent tickets triage --ticket <path> --decision wontfix --reason "仕様通りの動作"
```

スラッシュコマンドでも操作可能:

```
/wpf-ticket-create 保存ボタンクリック後にアプリがクラッシュした
/wpf-ticket-triage auto
```

## `wpf-agent ui` — 直接 UI 操作コマンド

Claude Code が Bash 経由で直接 UI を操作するコマンド群。ANTHROPIC_API_KEY 不要。

### 操作系コマンド（マウス移動検知ガード対象）

```bash
wpf-agent ui focus --pid <pid>                          # ウィンドウフォーカス
wpf-agent ui click --pid <pid> --aid <id>               # クリック
wpf-agent ui type --pid <pid> --aid <id> --text "..."   # テキスト入力
wpf-agent ui toggle --pid <pid> --aid <id>              # トグル
wpf-agent ui close --pid <pid>                          # WM_CLOSE で終了 (launch 起動のみ)
```

### 読み取り系コマンド（一時停止中も使用可）

```bash
wpf-agent ui windows [--brief]                          # トップレベルウィンドウ一覧 (PID/タイトル)
wpf-agent ui alive --process MyApp [--brief]            # プロセス検索 + PID 取得
wpf-agent ui alive --pid <pid>                          # プロセス生存確認 (PID)
wpf-agent ui screenshot --pid <pid> [--save <path>]     # スクショ撮影 (ポップアップ自動合成)
wpf-agent ui controls --pid <pid> [--depth N]            # 全コントロール一覧 (JSON)
wpf-agent ui controls --pid <pid> --has-aid --brief      # automation_id 付きのみ (テーブル)
wpf-agent ui controls --pid <pid> --type-filter Button,Edit,ComboBox --brief
wpf-agent ui read --pid <pid> --aid <id>                 # テキスト読取
wpf-agent ui state --pid <pid> --aid <id>                # 状態取得
```

`ui controls` フィルタオプション:

| オプション | 説明 |
|-----------|------|
| `--type-filter` | control_type でフィルタ (カンマ区切り) |
| `--name-filter` | name の部分一致フィルタ (大文字小文字無視) |
| `--has-name` | name が空でないもののみ |
| `--has-aid` | automation_id が空でないもののみ |
| `--brief` | JSON の代わりにコンパクトなテーブル出力 |

### ガード管理

```bash
wpf-agent ui status                                     # ガード状態確認
wpf-agent ui resume                                     # 再開
wpf-agent ui --no-guard click --pid ...                 # ガードスキップ
```

全コマンド共通: `--pid <int>` または `--title-re <regex>` でターゲット指定。
セレクタ: `--aid`, `--name`, `--control-type` (`--aid` 推奨)。

## UI ガード（マウス移動検知）

操作系コマンド (`focus`, `click`, `type`, `toggle`) は実行前にマウス位置を 50ms サンプリング。ユーザーのマウス移動 (>2px) を検出すると操作を中断し、持続的な一時停止状態に移行。

- 中断時: exit code 2 + JSON 出力（理由付き）
- 読み取り系コマンドは一時停止中も実行可能
- `wpf-agent ui resume` で再開

## MCP ツール一覧（13個）

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
| `get_state` | UI 要素の状態を取得 |
| `screenshot` | スクリーンショットを撮影 |
| `wait_for` | UI 条件の成立を待機 |

## VS Code Copilot でのインストール

`.claude/skills/` のスキルは [Agent Skills](https://agentskills.io) オープン標準に準拠しており、VS Code Copilot のエージェントモードから利用できます。

### 前提条件

- VS Code Insiders（またはエージェントモード対応の VS Code）
- GitHub Copilot 拡張機能がインストール済み
- Python 3.10 以上

### セットアップ手順

```bash
# 1. リポジトリをクローン
git clone https://github.com/shiromac/wpfAutoTester.git
cd wpfAutoTester

# 2. パッケージをインストール
pip install -e .[dev]

# 3. 初期化（profiles.json 等を生成）
wpf-agent init

# 4. スキルをインストール（.claude/skills/ に配置）
wpf-agent install-skills
```

### VS Code での使い方

1. VS Code でプロジェクトフォルダを開く
2. Copilot チャットをエージェントモードに切り替える
3. `.claude/skills/` 内のスキルが自動検出される
4. チャットからスキルを呼び出して UI テストを実行

### GitHub Copilot Coding Agent（リポジトリレベル）

GitHub 上で Copilot Coding Agent を使う場合は、`.github/skills/` にもスキルをコピーします:

```bash
wpf-agent install-skills --github
```

## Claude Code スラッシュコマンド

| コマンド | 説明 |
|----------|------|
| `/wpf-setup` | セットアップと MCP サーバー登録 |
| `/wpf-inspect` | UI 調査 (ウィンドウ + コントロール一覧 + スクリーンショット) |
| `/wpf-explore` | AI 誘導型探索テスト |
| `/wpf-usability-test` | ペルソナ型ユーザビリティテスト（思考発話法 + ゴール指向） |
| `/wpf-verify` | ビルド＆自動検証 (起動→スモークテスト→UI チェック→レポート) |
| `/wpf-click` | 要素クリック + 検証 |
| `/wpf-type` | テキスト入力 + 検証 |
| `/wpf-scenario` | シナリオテスト実行 / YAML 作成 |
| `/wpf-random` | ランダム探索テスト |
| `/wpf-replay` | AI 不要リプレイ |
| `/wpf-ticket` | チケット確認・分析 |
| `/wpf-ticket-create` | 問題チケット作成 (エビデンス収集付き) |
| `/wpf-ticket-triage` | チケット整理 (fix / wontfix に分類・移動) |

## プロファイル設定

`profiles.json` を編集して対象アプリを登録:

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

## ペルソナプリセット

`personas.json` にユーザビリティテスト用のペルソナプリセットを定義:

```json
[
  {
    "name": "tanaka",
    "description": "田中美咲（35歳）、事務職、ITリテラシー中程度（Word/Excelは日常使用）、慎重で説明をよく読む、エラーが出ると不安になる"
  },
  {
    "name": "suzuki",
    "description": "鈴木健一（62歳）、定年退職後の再雇用、ITリテラシー低（スマホは使うがPCは苦手）、文字が小さいと読みづらい、ゆっくり操作する"
  },
  {
    "name": "sato",
    "description": "佐藤翔太（22歳）、新卒エンジニア、ITリテラシー高、せっかちで説明を読まずにクリックする、エラーが出ても動じない"
  }
]
```

CLI でプリセットを管理:

```bash
wpf-agent personas list
wpf-agent personas add --name yamada --description "山田太郎（45歳）、管理職、ITリテラシー中程度"
wpf-agent personas edit yamada --description "山田太郎（45歳）、上級管理職、ITリテラシー高"
wpf-agent personas remove yamada
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
```

## プロジェクト構成

```
src/wpf_agent/
  core/       # ターゲットレジストリ、セッション管理、安全チェック、例外
  uia/        # UIAEngine、セレクタ、スナップショット、スクリーンショット、待機
  mcp/        # FastMCP サーバー (13ツール)、Pydantic 型定義
  runner/     # エージェントループ、リプレイ、構造化ログ
  testing/    # シナリオテスト、ランダムテスト、アサーション、障害オラクル、最小化
  tickets/    # チケット生成、テンプレート、証跡収集
scenarios/    # YAML シナリオ定義
artifacts/    # セッションとチケット (実行時生成)
tests/        # ユニットテスト
testApp/      # WPF テスト用サンプルアプリ (.NET 9)
profiles.json # 対象アプリ定義
personas.json # ペルソナプリセット定義
```

## 実行ファイルのビルド

```bash
pip install pyinstaller
pyinstaller wpf_agent.spec
```

## 動作要件

- Windows 10 / 11
- Python 3.10 以上
- 対象アプリ: WPF（UIA 対応であれば .NET バージョン問わず）

## Claude Code パーミッション設定

`wpf-agent` コマンドを自動承認するには、`.claude/settings.local.json`（プロジェクトローカル、gitignore 対象）に以下を設定します:

```jsonc
{
  "permissions": {
    "allow": [
      "Bash(wpf-agent *)",   // コマンド文字列全体にマッチ（パイプ含む）
      "Bash(wpf-agent:*)",   // コマンド名プレフィックスにマッチ（単純コマンド）
      "Bash(python:*)"
    ]
  }
}
```

| パターン | マッチ対象 | 用途 |
|---------|-----------|------|
| `Bash(wpf-agent:*)` | **コマンド名** のプレフィックス | 単純: `wpf-agent tickets create ...` |
| `Bash(wpf-agent *)` | **コマンド文字列全体** | パイプ付き: `wpf-agent ui controls ... \| head` |

両方の設定を推奨。glob の `*` は改行にマッチしないため、Bash コマンドは常に1行で記述してください。

Claude Code 内で `/permissions` を実行すると、現在有効なルールを確認できます。

## ライセンス

MIT License。[LICENSE](LICENSE) を参照。
