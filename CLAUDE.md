# WPF UI Debug Automation Agent

## プロジェクト概要
Claude Code と統合された WPF UI 自動化エージェント。pywinauto (UIA) を使用して Windows デスクトップアプリを操作する。

## Bash コマンド生成ルール
- `wpf-agent` やパイプ付きコマンドは**必ず1行で記述**すること（改行禁止）
  - glob パーミッション `Bash(wpf-agent *)` の `*` は改行にマッチしない
  - 複雑な処理は `wpf-agent` CLI サブコマンドを使う（例: `wpf-agent tickets create --title "..." ...`）
  - パイプで `python -c` を使う場合は `;` で1行にまとめる
  - OK: `wpf-agent ui controls --pid 1234 | python -c "import json,sys; [print(c['name']) for c in json.load(sys.stdin) if c.get('name')]"`
  - NG: `wpf-agent ui controls --pid 1234 | python -c "\nimport json\n..."`

## MCP サーバー
このプロジェクトは MCP サーバーを提供する。登録コマンド:
```
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

### 利用可能な MCP ツール (13個)
- `list_windows` — トップレベルウィンドウ一覧
- `resolve_target(target_spec)` — アプリ特定 (pid/process/exe/title_re)
- `focus_window(window_query|target_id)` — ウィンドウを前面に
- `wait_window(window_query|target_id, timeout_ms)` — ウィンドウ出現待機
- `list_controls(window_query|target_id, depth, filter)` — UIA コントロール列挙
- `click(window_query|target_id, selector)` — クリック
- `type_text(window_query|target_id, selector, text)` — テキスト入力
- `select_combo(window_query|target_id, selector, item_text)` — コンボ選択
- `toggle(window_query|target_id, selector, state)` — トグル
- `read_text(window_query|target_id, selector)` — テキスト読取
- `get_state(window_query|target_id, selector)` — 状態取得
- `screenshot(window_query|target_id, region)` — スクリーンショット
- `wait_for(window_query|target_id, selector, condition, value, timeout_ms)` — 条件待機

### ツール使用パターン
1. まず `list_windows` でウィンドウを確認
2. `resolve_target({"title_re": "..."})` で target_id を取得
3. `focus_window(target_id=...)` でフォーカス
4. `list_controls(target_id=..., depth=4)` でコントロール調査
5. `click` / `type_text` 等で操作
6. `screenshot` / `read_text` / `get_state` で検証

### セレクタの優先順位
1. `automation_id` (最も安定)
2. `name` + `control_type`
3. `bounding_rect` の中心クリック (最後の手段)

## CLI コマンド
```
wpf-agent init                           # 初期化
wpf-agent install-skills                 # Claude Code スキルインストール
wpf-agent install-skills --github        # .github/skills/ にもコピー (Copilot Coding Agent用)
wpf-agent profiles list/add/edit/remove  # プロファイル管理
wpf-agent run --profile <name>           # エージェントループ
wpf-agent attach --pid <pid>             # PID接続
wpf-agent launch --exe <path>            # 起動接続
wpf-agent scenario run --file <yaml>     # シナリオテスト
wpf-agent random run --profile <name>    # ランダムテスト
wpf-agent explore run --profile <name>   # AI誘導型探索テスト
wpf-agent verify --exe <path>            # ビルド後自動検証
wpf-agent verify --exe <path> --spec <yaml>  # spec付き検証
wpf-agent replay --file <json>           # リプレイ
wpf-agent tickets open --last            # チケット確認
wpf-agent tickets create --title "..." --summary "..." --actual "..." --expected "..." [--repro "..."] [--evidence <path>] [--hypothesis "..."] [--pid N] [--process "..."] [--profile "..."]
wpf-agent tickets list-pending           # 未分類チケット一覧
wpf-agent tickets triage --ticket <path> --decision <fix|wontfix> [--reason "..."]
```

### `wpf-agent ui` — Claude Code 直接 UI 操作
Claude Code が Bash 経由で直接 UI を操作するためのコマンド群。ANTHROPIC_API_KEY 不要。

#### 操作系コマンド (ガード対象)
```
wpf-agent ui focus --pid <pid>                           # ウィンドウフォーカス
wpf-agent ui click --pid <pid> --aid <id>                # クリック
wpf-agent ui type --pid <pid> --aid <id> --text "..."    # テキスト入力
wpf-agent ui toggle --pid <pid> --aid <id>               # トグル
wpf-agent ui close --pid <pid>                           # WM_CLOSE で終了 (launch 起動のみ)
```

#### 読み取り系コマンド (ガード対象外 — 一時停止中も使用可)
```
wpf-agent ui windows [--brief]                            # トップレベルウィンドウ一覧 (PID/タイトル)
wpf-agent ui alive --process <name> [--brief]             # プロセス生存確認 + PID取得
wpf-agent ui alive --pid <pid>                            # PID指定の生存確認
wpf-agent ui screenshot --pid <pid> [--save <path>]       # スクショ撮影 (ポップアップ自動合成)
wpf-agent ui controls --pid <pid> [--depth N] [--type-filter Button,Edit] [--has-aid] [--brief]  # コントロール一覧
wpf-agent ui read --pid <pid> --aid <id>                  # テキスト読取
wpf-agent ui state --pid <pid> --aid <id>                 # 状態取得
```

#### ガード管理コマンド
```
wpf-agent ui status                       # 現在の状態 (active/paused)
wpf-agent ui resume                       # 一時停止を解除して再開
wpf-agent ui --no-guard click --pid ...   # ガードをスキップして実行
```

全コマンド共通: `--pid <int>` または `--title-re <regex>` でターゲット指定。
セレクタ: `--aid`, `--name`, `--control-type` で要素指定 (aid 推奨)。

#### 典型的な作業フロー
```bash
# 1. ウィンドウ一覧から対象アプリを探す
wpf-agent ui windows --brief

# 2. プロセス名から PID を取得 (--brief で数値だけ出力)
wpf-agent ui alive --process MyApp --brief
#=> 12345

# 3. 以降は --pid で操作
wpf-agent ui controls --pid 12345 --brief
wpf-agent ui screenshot --pid 12345 --save /tmp/screen.png
wpf-agent ui click --pid 12345 --aid BtnOK
```

### UI ガード (マウス移動検知)
操作系コマンド (`focus`, `click`, `type`, `toggle`) は実行前にマウス位置を 50ms サンプリングし、ユーザーのマウス移動 (>2px) を検出すると操作を中断する。中断後は pause ファイル (`~/.wpf-agent/pause`) で持続的にブロックされる。`close` はガード対象外（launch 起動プロセス限定で安全なため）。

- 中断時: exit code 2 + `{"interrupted": true, "reason": "...", ...}` を JSON 出力
- 実装: `src/wpf_agent/ui_guard.py` (check_guard, is_paused, set_paused, clear_pause)
- 定数: `src/wpf_agent/constants.py` (GUARD_CHECK_DELAY_MS, GUARD_MOVEMENT_THRESHOLD_PX, GUARD_PAUSE_DIR)

## カスタムスキル (スラッシュコマンド)
- `/wpf-setup` — セットアップとMCPサーバー登録
- `/wpf-inspect` — UI調査 (ウィンドウ+コントロール一覧+スクリーンショット)
- `/wpf-click` — 要素クリック+検証
- `/wpf-type` — テキスト入力+検証
- `/wpf-scenario` — シナリオテスト実行/YAML作成
- `/wpf-random` — ランダム探索テスト
- `/wpf-explore` — AI誘導型探索テスト (Claude Code 直接 UI 操作)
- `/wpf-verify` — ビルド後自動検証 (起動→スモークテスト→UIチェック→レポート)
- `/wpf-replay` — AI不要リプレイ再現
- `/wpf-ticket` — チケット確認・分析
- `/wpf-ticket-create` — 問題チケット作成 (ticket.md + エビデンス収集)
- `/wpf-usability-test` — ペルソナ型ユーザビリティテスト（思考発話法 + ゴール指向）
- `/wpf-ticket-triage` — チケット整理 (fix / wontfix に分類・移動)

## ディレクトリ構成
```
src/wpf_agent/
├── __init__.py, __main__.py   # パッケージ・エントリポイント
├── cli.py                     # Click ベース CLI (全コマンド定義)
├── config.py                  # ProfileStore / Profile / ProfileMatch 等
├── constants.py               # グローバル定数 + ガード定数
├── ui_guard.py                # マウス移動検知ガード
├── core/
│   ├── errors.py              # 例外階層 (UserInterruptError 含む)
│   ├── safety.py              # 安全ポリシー
│   ├── session.py             # セッション管理
│   └── target.py              # TargetRegistry / ResolvedTarget
├── uia/
│   ├── engine.py              # UIAEngine (pywinauto ラッパー)
│   ├── screenshot.py          # スクリーンショット撮影
│   ├── selector.py            # Selector データクラス
│   ├── snapshot.py            # UI スナップショット
│   └── waits.py               # 待機ユーティリティ
├── mcp/
│   ├── server.py              # MCP サーバー (stdio)
│   └── types.py               # MCP 型定義
├── runner/
│   ├── agent_loop.py          # エージェントループ
│   ├── logging.py             # 構造化ログ
│   └── replay.py              # リプレイ実行
├── testing/
│   ├── assertions.py          # アサーション
│   ├── explorer.py            # AI 誘導型探索
│   ├── minimizer.py           # テストケース最小化
│   ├── oracles.py             # テストオラクル
│   ├── random_tester.py       # ランダムテスト
│   ├── scenario.py            # シナリオテスト
│   └── verifier.py            # ビルド後検証
└── tickets/
    ├── evidence.py            # エビデンス収集
    ├── generator.py           # チケット生成
    └── templates.py           # チケットテンプレート

scenarios/                     # YAML シナリオ定義
testApp/                       # WPF テスト用サンプルアプリ (.NET 9)
artifacts/sessions/            # セッションログ (実行時生成)
artifacts/tickets/             # チケット (実行時生成)
tests/                         # ユニットテスト
profiles.json                  # 対象アプリ定義
```

## 開発
```
pip install -e .[dev]
python -m pytest tests/ -v
```

## テストアプリ (testApp)
WPF (.NET 9) のデバッグ用サンプルアプリ。ビルド済み exe:
```
testApp/bin/Debug/net9.0-windows/TestApp.exe
```
UI 要素: TitleLabel, StatusLabel, MainButton, ResetButton, InputField, OptionCheck, CounterLabel
