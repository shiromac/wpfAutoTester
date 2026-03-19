# wpf-agent 使い方ガイド

## 目次
- [MCP サーバー](#mcp-サーバー)
- [CLI コマンド](#cli-コマンド)
- [UI 操作コマンド (`wpf-agent ui`)](#wpf-agent-ui--claude-code-直接-ui-操作)
- [UI ガード (マウス移動検知)](#ui-ガード-マウス移動検知)
- [カスタムスキル (スラッシュコマンド)](#カスタムスキル-スラッシュコマンド)
- [自然言語リクエストへの対応](#自然言語リクエストへの対応)
- [テストアプリ (testApp)](#テストアプリ-testapp)

---

## MCP サーバー
このプロジェクトは MCP サーバーを提供する。登録コマンド:
```
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

### 利用可能な MCP ツール (15個)
- `list_windows` — トップレベルウィンドウ一覧
- `resolve_target(target_spec)` — アプリ特定 (pid/process/exe/title_re)
- `focus_window(window_query|target_id)` — ウィンドウを前面に
- `wait_window(window_query|target_id, timeout_ms)` — ウィンドウ出現待機
- `list_controls(window_query|target_id, depth, filter, search)` — UIA コントロール列挙 (`search`: name/aid/value 部分一致、カンマ区切りで OR)
- `click(window_query|target_id, selector)` — クリック
- `drag(window_query|target_id, src_selector, dst_selector)` — ドラッグ&ドロップ (要素間のマウスドラッグ)
- `type_text(window_query|target_id, selector, text, method)` — テキスト入力 (`method`: `"keyboard"` (デフォルト) / `"value_pattern"`)
- `send_keys(window_query|target_id, selector, keys)` — キーボードショートカット送信 (pywinauto 記法: `"{ENTER}"`, `"^a"`)
- `select_combo(window_query|target_id, selector, item_text)` — コンボ選択
- `toggle(window_query|target_id, selector, state)` — トグル
- `read_text(window_query|target_id, selector)` — テキスト読取
- `get_state(window_query|target_id, selector)` — 状態取得
- `screenshot(window_query|target_id, region)` — スクリーンショット
- `wait_for(window_query|target_id, selector, condition, value, timeout_ms)` — 条件待機 (条件: exists, enabled, visible, text_equals, text_contains, text_not_equals, text_changed)

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

---

## CLI コマンド
```
wpf-agent init                           # 初期化
wpf-agent install-skills                 # Claude Code スキルインストール
wpf-agent install-skills --github        # .github/skills/ にもコピー (Copilot Coding Agent用)
wpf-agent profiles list/add/edit/remove  # プロファイル管理
wpf-agent personas list/add/edit/remove  # ペルソナプリセット管理
wpf-agent run --profile <name>           # エージェントループ
wpf-agent attach --pid <pid>             # PID接続
wpf-agent launch --exe <path>            # 起動接続
wpf-agent close --pid <pid> [--force]   # プロセスを終了 (--force: 起動元チェックスキップ)
wpf-agent scenario run --file <yaml>     # シナリオテスト
wpf-agent random run --profile <name>    # ランダムテスト
wpf-agent explore run --profile <name>   # AI誘導型探索テスト
wpf-agent verify --exe <path>            # ビルド後自動検証
wpf-agent verify --exe <path> --spec <yaml>  # spec付き検証
wpf-agent replay --file <json>           # リプレイ
wpf-agent tickets open --last            # チケット確認
wpf-agent tickets create --title "..." --summary "..." --actual-result "..." --expected-result "..." [--repro-steps "..."] [--evidence <path>] [--root-cause "..."] [--pid N] [--process "..."] [--profile "..."]
wpf-agent tickets list-pending           # 未分類チケット一覧
wpf-agent tickets triage --ticket <path> --decision <fix|wontfix> [--reason "..."]
```

---

## `wpf-agent ui` — Claude Code 直接 UI 操作
Claude Code が Bash 経由で直接 UI を操作するためのコマンド群。ANTHROPIC_API_KEY 不要。

### 操作系コマンド (ガード対象)
```
wpf-agent ui focus --pid <pid>                           # ウィンドウフォーカス
wpf-agent ui click --pid <pid> --aid <id> [--double] [--method mouse|invoke|keys]  # クリック (method: mouse=マウス, invoke=UIA InvokePattern, keys=フォーカス+SPACE)
wpf-agent ui drag --pid <pid> --aid <src_id> --dst-aid <dst_id>  # ドラッグ&ドロップ
wpf-agent ui type --pid <pid> --aid <id> --text "..." [--method keyboard|value_pattern]  # テキスト入力
wpf-agent ui send-keys --pid <pid> --keys "{ENTER}"      # キーボードショートカット送信
wpf-agent ui send-keys --pid <pid> --aid <id> --keys "^a" # 要素フォーカス後にキー送信
wpf-agent ui toggle --pid <pid> --aid <id>               # トグル
wpf-agent ui select-combo --pid <pid> --aid <id> --item "text"  # コンボボックス選択
wpf-agent ui close --pid <pid> [--force]                 # WM_CLOSE で終了 (--force: 起動元チェックスキップ)
```

### 読み取り系コマンド (ガード対象外 — 一時停止中も使用可)
```
wpf-agent ui windows [--brief]                            # トップレベルウィンドウ一覧 (PID/タイトル)
wpf-agent ui alive --process <name> [--brief]             # プロセス生存確認 + PID取得
wpf-agent ui alive --pid <pid>                            # PID指定の生存確認
wpf-agent ui screenshot --pid <pid> [--save <path>]       # スクショ撮影 (ポップアップ自動合成)
wpf-agent ui controls --pid <pid> [--depth N] [--type-filter Button,Edit] [--search "text"] [--aid-filter "id"] [--name-filter "name,name2"] [--has-aid] [--brief]  # コントロール一覧・検索 (フィルタはカンマ区切りでOR)
wpf-agent ui read --pid <pid> --aid <id>                  # テキスト読取
wpf-agent ui state --pid <pid> --aid <id>                 # 状態取得
wpf-agent ui init-session --prefix <name>                  # セッション用ワークスペース作成 (タイムスタンプ付き)
```

### ガード管理コマンド
```
wpf-agent ui status                       # 現在の状態 (active/paused)
wpf-agent ui resume                       # 一時停止を解除して再開
wpf-agent ui --no-guard click --pid ...   # ガードをスキップして実行
```

全コマンド共通: `--pid <int>` または `--title-re <regex>` でターゲット指定。
セレクタ: `--aid`, `--name`, `--control-type` で要素指定 (aid 推奨)。

### 典型的な作業フロー
```bash
# 1. ウィンドウ一覧から対象アプリを探す
wpf-agent ui windows --brief

# 2. プロセス名から PID を取得 (--brief で数値だけ出力)
wpf-agent ui alive --process MyApp --brief
#=> 12345

# 3. セッションディレクトリを作成 (タイムスタンプは自動生成)
wpf-agent ui init-session --prefix explore
#=> {"path": "artifacts/sessions/explore_20260301_153045"}

# 4. 以降は --pid で操作
wpf-agent ui controls --pid 12345 --brief
wpf-agent ui screenshot --pid 12345 --save artifacts/sessions/explore_20260301_153045/screen.png
wpf-agent ui click --pid 12345 --aid BtnOK
```
**注意**: タイムスタンプの取得には `init-session` を使うこと。`pwsh` や `date` コマンドで時刻を取得する必要はない。

---

## UI ガード (マウス移動検知)
操作系コマンド (`focus`, `click`, `drag`, `type`, `send-keys`, `toggle`) は実行前にマウス位置を 50ms サンプリングし、ユーザーのマウス移動 (>2px) を検出すると操作を中断する。中断後は pause ファイル (`~/.wpf-agent/pause`) で持続的にブロックされる。`close` はガード対象外（wpf-agent 起動プロセス限定で安全なため）。

- 中断時: exit code 2 + `{"interrupted": true, "reason": "...", ...}` を JSON 出力
- 実装: `src/wpf_agent/ui_guard.py` (check_guard, is_paused, set_paused, clear_pause)
- 定数: `src/wpf_agent/constants.py` (GUARD_CHECK_DELAY_MS, GUARD_MOVEMENT_THRESHOLD_PX, GUARD_PAUSE_DIR)

---

## カスタムスキル (スラッシュコマンド)
- `/wpf-setup` — セットアップとMCPサーバー登録
- `/wpf-ui` — UI操作（調査・クリック・入力・スクリーンショット）
- `/wpf-test` — テスト実行（探索・ランダム・シナリオ・ユーザビリティ・検証・リプレイ）
- `/wpf-ticket` — チケット管理（確認・作成・整理）

---

## 自然言語リクエストへの対応

ユーザーが以下のような自然言語で依頼した場合、**対応するスキルまたは `wpf-agent ui` コマンドを使って実行すること**。スラッシュコマンドを知らないユーザーでも自然に使えるようにする。

**重要**: 「wpf-agent で〇〇して」「wpf-agent を使って〇〇」のように **`wpf-agent` が明示されている場合は、必ず `wpf-agent` のコマンドやスキルを使って実行すること**。他のツールや手段で代替しない。

| ユーザーの発言（例） | 実行すべきアクション |
|---------------------|---------------------|
| 「デバッグして」「wpf-agentでデバッグ」「動かして確認」 | 対象アプリを `wpf-agent launch` で起動し、`/wpf-test explore` で探索。exe パスが不明ならプロファイルか会話から推定、それでも不明なら聞く |
| 「動作確認して」「テストして」「確認して」 | `/wpf-test verify` を実行（exe パスが不明なら聞く）。起動済みなら `/wpf-test explore` で探索 |
| 「画面を見て」「UI を確認して」「スクショ撮って」 | `/wpf-ui inspect` を実行 |
| 「探索テストして」「全部触って」 | `/wpf-test explore` を実行 |
| 「ユーザビリティテストして」「ペルソナテストして」 | `/wpf-test usability` を実行 |
| 「ランダムテストして」 | `/wpf-test random` を実行 |
| 「シナリオテストして」 | `/wpf-test scenario` を実行 |
| 「チケット見せて」「バグ一覧」 | `/wpf-ticket` を実行 |
| 「チケット作成して」 | `/wpf-ticket create` を実行 |
| 「チケット整理して」 | `/wpf-ticket triage` を実行 |
| 「〇〇に入力して」「テキストを入れて」 | `/wpf-ui type` を実行。**python/xdotool で直接入力しない** |
| 「〇〇の値を読んで」「テキストを取得して」 | `wpf-agent ui read --pid <pid> --aid <id>` を実行。**python で直接読み取らない** |
| 「〇〇をクリックして」「ボタン押して」 | `/wpf-ui click` を実行 |
| 「ドラッグして」「〇〇を〇〇に移動して」 | `wpf-agent ui drag --pid <pid> --aid <src> --dst-aid <dst>` を実行 |
| 「起動して」「アプリを立ち上げて」 | `wpf-agent launch --exe <path>` で起動 |
| 「閉じて」「終了して」 | `wpf-agent ui close --pid <pid>` で終了 |

### 判断のフロー
1. **`wpf-agent` が明示されているか？** → 明示されていれば必ず `wpf-agent` のコマンド/スキルを使う。他のツールで代替しない
2. 対象アプリの指定があるか？ → なければプロファイル (`.wpf-agent/profiles.json`) や直近の会話から推定、それでも不明なら聞く
3. アプリが起動済みか？ → `wpf-agent ui windows --brief` で確認
4. 起動済みなら `wpf-agent ui` コマンドや `/wpf-test explore` で直接操作
5. 未起動なら `wpf-agent launch --exe <path>` で起動してから操作。検証が目的なら `/wpf-test verify --exe <path>` を使う

---

## テストアプリ (testApp)
WPF (.NET 9) のデバッグ用サンプルアプリ。ビルド済み exe:
```
testApp/bin/Debug/net9.0-windows/TestApp.exe
```
UI 要素: TitleLabel, StatusLabel, MainButton, ResetButton, InputField, OptionCheck, ColorCombo, CounterLabel
