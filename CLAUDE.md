# WPF UI Debug Automation Agent

## プロジェクト概要
Claude Code と統合された WPF UI 自動化エージェント。pywinauto (UIA) を使用して Windows デスクトップアプリを操作する。

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
wpf-agent profiles list/add/edit/remove  # プロファイル管理
wpf-agent run --profile <name>           # エージェントループ
wpf-agent attach --pid <pid>             # PID接続
wpf-agent launch --exe <path>            # 起動接続
wpf-agent scenario run --file <yaml>     # シナリオテスト
wpf-agent random run --profile <name>    # ランダムテスト
wpf-agent replay --file <json>           # リプレイ
wpf-agent tickets open --last            # チケット確認
```

## カスタムスキル (スラッシュコマンド)
- `/project:wpf-setup` — セットアップ
- `/project:wpf-inspect` — UI調査 (ウィンドウ+コントロール一覧)
- `/project:wpf-click` — 要素クリック
- `/project:wpf-type` — テキスト入力
- `/project:wpf-scenario` — シナリオテスト実行/作成
- `/project:wpf-random` — ランダムテスト
- `/project:wpf-replay` — リプレイ再現
- `/project:wpf-ticket` — チケット確認

## 重要なディレクトリ
- `src/wpf_agent/` — ソースコード
- `scenarios/` — YAML シナリオ定義
- `artifacts/sessions/` — セッションログ (実行時生成)
- `artifacts/tickets/` — チケット (実行時生成)
- `profiles.json` — 対象アプリ定義
- `tests/` — ユニットテスト

## 開発
```
pip install -e .[dev]
python -m pytest tests/ -v
```
