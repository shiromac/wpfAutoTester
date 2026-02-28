# Claude Code への導入ガイド

WPF UI 自動化エージェント (`wpf-agent`) を Claude Code に導入する手順です。

---

## 前提条件

- **OS**: Windows 10/11
- **Python**: 3.10 以上
- **Claude Code**: インストール済み（`claude` コマンドが使える状態）
- 対象の WPF アプリのソースコードまたは実行ファイル

---

## Step 1: リポジトリの取得

```bash
git clone <このリポジトリのURL>
cd wpfAutoTester
```

---

## Step 2: パッケージのインストール

```bash
pip install -e .[dev]
```

インストールされるもの:

| パッケージ | 用途 |
|---|---|
| pywinauto | Windows UI オートメーション (UIA) |
| mcp | Claude Code との通信プロトコル |
| click | CLI フレームワーク |
| psutil | プロセス管理 |
| Pillow | スクリーンショット撮影 |
| pyyaml | YAML 設定ファイル |
| anthropic | AI 探索テスト用（`/wpf-explore`） |

インストール確認:

```bash
wpf-agent --version
```

---

## Step 3: 初期化

```bash
wpf-agent init
```

以下が作成されます:
- `profiles.json` — 対象アプリの定義ファイル
- `artifacts/sessions/` — テスト結果の保存先
- `artifacts/tickets/` — 障害チケットの保存先

---

## Step 4: MCP サーバーの登録

Claude Code に MCP サーバーとして登録します:

```bash
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

登録確認:

```bash
claude mcp list
```

`wpf-agent` が表示されれば成功です。

### MCP サーバーで使えるようになるツール（13個）

Claude Code のチャット内から直接呼び出せるようになります:

```
list_windows        — デスクトップ上のウィンドウ一覧
resolve_target      — アプリを PID/プロセス名/タイトル等で特定
focus_window        — ウィンドウを前面に
wait_window         — ウィンドウの出現を待機
list_controls       — UI コントロール一覧を取得
click               — ボタン等をクリック
type_text           — テキスト入力
select_combo        — コンボボックス選択
toggle              — チェックボックス切替
read_text           — テキスト読み取り
get_state           — 要素の状態取得
screenshot          — スクリーンショット撮影
wait_for            — 条件を満たすまで待機
```

---

## Step 5: 対象アプリのプロファイル登録

### 方法 A: CLI から追加

```bash
# プロセス名で特定する場合
wpf-agent profiles add --name myapp --process MyApp.exe

# ウィンドウタイトルで特定する場合
wpf-agent profiles add --name myapp --title-re "My Application.*"

# EXE パスで起動する場合
wpf-agent profiles add --name myapp --exe "C:/path/to/MyApp.exe"
```

### 方法 B: profiles.json を直接編集

```json
[
  {
    "name": "myapp",
    "match": {
      "title_re": "My Application.*"
    },
    "launch": {
      "exe": "C:/path/to/MyApp.exe",
      "args": [],
      "cwd": null
    },
    "timeouts": {
      "startup_ms": 10000,
      "default_ms": 10000,
      "screenshot_ms": 5000
    },
    "safety": {
      "allow_destructive": false,
      "destructive_patterns": ["delete", "remove", "drop", "exit", "quit", "close"],
      "require_double_confirm": true
    }
  }
]
```

プロファイル確認:

```bash
wpf-agent profiles list
```

---

## Step 6: 動作確認

### 6a. CLI での確認

対象アプリを起動した状態で:

```bash
# ウィンドウが認識されるか確認
wpf-agent attach --pid <アプリのPID>
```

または verify でスモークテスト:

```bash
wpf-agent verify --exe "C:/path/to/MyApp.exe"
```

### 6b. Claude Code での確認

Claude Code を起動して対話:

```
あなた: 今開いているウィンドウを一覧表示して

Claude: (list_windows ツールを呼び出して一覧を表示)
```

MCP ツールが呼び出されれば導入完了です。

---

## Step 7: スキル（スラッシュコマンド）の確認

`.claude/skills/` ディレクトリ内のスキルは Claude Code が自動検出します。
以下のスラッシュコマンドが使えるようになります:

| コマンド | 説明 |
|---|---|
| `/wpf-setup` | セットアップとMCPサーバー登録 |
| `/wpf-inspect` | UI調査（ウィンドウ＋コントロール一覧＋スクショ） |
| `/wpf-click` | 要素クリック＋検証 |
| `/wpf-type` | テキスト入力＋検証 |
| `/wpf-scenario` | シナリオテスト実行／YAML作成 |
| `/wpf-random` | ランダム探索テスト |
| `/wpf-explore` | AI誘導型探索テスト（Claude Vision） |
| `/wpf-verify` | ビルド後自動検証 |
| `/wpf-replay` | AI不要リプレイ再現 |
| `/wpf-ticket` | チケット確認・分析 |

Claude Code のチャットで `/wpf-` と入力すると候補が表示されます。

---

## 推奨: パーミッション設定

`.claude/settings.local.json` に以下が設定済みです。
Claude Code が `wpf-agent` コマンドを許可なしで実行できるようになっています:

```json
{
  "permissions": {
    "allow": [
      "Bash(wpf-agent:*)",
      "Bash(python:*)",
      "Bash(dotnet:*)",
      "Bash(pip install:*)"
    ]
  }
}
```

新しいプロジェクトに導入する場合は、この設定をコピーしてください。

---

## 使い方の例

### 例 1: アプリの UI を調べる

```
あなた: /wpf-inspect MyApp のUI構造を教えて
```

Claude が自動で:
1. ウィンドウを検出
2. コントロール一覧を取得
3. スクリーンショットを撮影
4. 構造をまとめて報告

### 例 2: コード修正後の動作確認

```
あなた: ボタンのテキストを「送信」に変えて、ビルドして動作確認して

Claude:
1. コードを編集
2. dotnet build
3. /wpf-verify で起動＋検証
4. 結果を報告（スクショ付き）
```

### 例 3: ランダム探索で不具合発見

```
あなた: /wpf-random myapp を100ステップ探索して
```

Claude が自動で:
1. アプリを操作
2. クラッシュ・フリーズ・エラーダイアログを検出
3. 障害チケットを自動生成

---

## トラブルシューティング

### `claude mcp list` に wpf-agent が表示されない

```bash
# 再登録
claude mcp remove wpf-agent
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

### MCP ツールが呼び出せない

Python のパスを確認:

```bash
# python コマンドのパスが正しいか
python -m wpf_agent mcp-serve
```

仮想環境を使っている場合はフルパスで登録:

```bash
claude mcp add wpf-agent -- /path/to/venv/Scripts/python -m wpf_agent mcp-serve
```

### `wpf-agent` コマンドが見つからない

```bash
pip install -e .
# または
python -m wpf_agent --version
```

### スキルが表示されない

`.claude/skills/` ディレクトリがプロジェクトルートにあることを確認:

```
wpfAutoTester/
├── .claude/
│   ├── skills/
│   │   ├── wpf-setup/SKILL.md
│   │   ├── wpf-verify/SKILL.md
│   │   └── ...
│   └── settings.local.json
├── src/
├── CLAUDE.md
└── ...
```

Claude Code はプロジェクトルートで起動する必要があります:

```bash
cd wpfAutoTester
claude
```

### pywinauto のエラー

管理者権限が必要な場合があります。ターミナルを管理者として実行してください。
