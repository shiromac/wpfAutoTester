<!-- wpf-agent:start -->
## WPF UI Debug Automation Agent (wpf-agent)

Claude Code と統合された WPF UI 自動化エージェント。pywinauto (UIA) を使用して Windows デスクトップアプリを操作し、以下の機能を提供する:

- **UI 自動操作** — クリック・テキスト入力・スクリーンショット等を Claude Code から直接実行
- **探索テスト** — AI が自律的にアプリの全画面を探索し、異常を検出
- **ランダムテスト / シナリオテスト / ユーザビリティテスト**
- **ビルド後検証** — exe を起動して基本動作を自動チェック
- **バグチケット管理** — 発見した問題のチケット作成・トリアージ

詳しい使い方（CLI コマンド一覧・UI 操作コマンド・MCP ツール・自然言語対応表）は **[docs/wpf-agent-usage.md](docs/wpf-agent-usage.md)** を参照。

### テキスト入力・読み取り・キー送信の禁止事項（重要）
UI 要素へのテキスト入力・テキスト読み取り・キー送信は、**必ず `wpf-agent ui type` / `wpf-agent ui read` / `wpf-agent ui send-keys` コマンド、または MCP ツール `type_text` / `read_text` / `send_keys` を使うこと**。以下の手段で直接操作してはならない:

- **禁止**: `python -c` で pywinauto の `set_edit_text()`, `type_keys()`, `window_text()`, `get_value()` を直接呼ぶ
- **禁止**: `xdotool type`, `xdotool key` でキーボード入力をシミュレートする
- **禁止**: `python -c` で `keyboard`, `pyautogui`, `pynput` モジュールを使ってキー入力する
- **禁止**: クリップボード経由 (`pyperclip`, `xclip`, `xsel`, Ctrl+V) でテキストを貼り付ける
- **禁止**: `SendKeys`, `xte`, `ydotool` 等の外部ツールでキー入力をシミュレートする

理由: `wpf-agent ui type` / `wpf-agent ui send-keys` はマウス移動ガード (UI ガード) を通るため安全。直接操作はガードを回避してしまい、ユーザーの操作と競合する危険がある。

### Bash コマンド生成ルール
- `wpf-agent` コマンドは**パイプ (`|`) を使わず、組み込みオプションだけで完結させる**こと
  - パイプ付きコマンドは glob パーミッション `Bash(wpf-agent *)` にマッチしないため、**毎回ユーザーに権限確認ダイアログが表示されてしまう**
  - UI 要素の検索には `--search`, `--name-filter`, `--aid-filter`, `--type-filter`, `--has-aid`, `--has-name` オプションを使う
  - `--search`, `--name-filter`, `--aid-filter` はカンマ区切りで OR 検索できる（例: `--name-filter "OK,FAIL,SKIP"`）
  - NG: `wpf-agent ui controls --pid 1234 | python -c "import json,sys; ..."` ← 権限確認が毎回発生
  - NG: `for ... do wpf-agent ...; done` ← シェルループも glob にマッチしない。各コマンドを個別に実行すること
- `wpf-agent` コマンドは**必ず1行で記述**すること（改行禁止）
  - glob パーミッション `Bash(wpf-agent *)` の `*` は改行にマッチしない
  - やむを得ずパイプが必要な場合のみ `;` で1行にまとめる

### カスタムスキル (スラッシュコマンド)
- `/wpf-setup` — セットアップとMCPサーバー登録
- `/wpf-ui` — UI操作（調査・クリック・入力・スクリーンショット）
- `/wpf-test` — テスト実行（探索・ランダム・シナリオ・ユーザビリティ・検証・リプレイ）
- `/wpf-ticket` — チケット管理（確認・作成・整理）
<!-- wpf-agent:end -->
