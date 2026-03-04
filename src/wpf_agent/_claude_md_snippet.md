<!-- wpf-agent:start -->
## WPF UI Debug Automation Agent (wpf-agent)

Claude Code と統合された WPF UI 自動化エージェント。pywinauto (UIA) を使用して Windows デスクトップアプリを操作する。

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
  - OK: `wpf-agent ui controls --pid 1234 --search "Add" --type-filter Button --brief`
  - OK: `wpf-agent ui controls --pid 1234 --aid-filter "Btn" --brief`
  - OK: `wpf-agent ui controls --pid 1234 --name-filter "OK,FAIL,SKIP,終端" --brief`  ← カンマ区切り OR
  - NG: `wpf-agent ui controls --pid 1234 | python -c "import json,sys; ..."` ← 権限確認が毎回発生
  - NG: `for ... do wpf-agent ...; done` ← シェルループも glob にマッチしない。各コマンドを個別に実行すること
- `wpf-agent` コマンドは**必ず1行で記述**すること（改行禁止）
  - glob パーミッション `Bash(wpf-agent *)` の `*` は改行にマッチしない
  - やむを得ずパイプが必要な場合のみ `;` で1行にまとめる

### CLI コマンド
```
wpf-agent init                           # 初期化
wpf-agent install-skills                 # Claude Code スキルインストール
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

### `wpf-agent ui` — Claude Code 直接 UI 操作
Claude Code が Bash 経由で直接 UI を操作するためのコマンド群。ANTHROPIC_API_KEY 不要。

#### 操作系コマンド (ガード対象)
```
wpf-agent ui focus --pid <pid>                           # ウィンドウフォーカス
wpf-agent ui click --pid <pid> --aid <id>                # クリック
wpf-agent ui type --pid <pid> --aid <id> --text "..." [--method keyboard|value_pattern]  # テキスト入力
wpf-agent ui send-keys --pid <pid> --keys "{ENTER}"      # キーボードショートカット送信
wpf-agent ui send-keys --pid <pid> --aid <id> --keys "^a" # 要素フォーカス後にキー送信
wpf-agent ui toggle --pid <pid> --aid <id>               # トグル
wpf-agent ui select-combo --pid <pid> --aid <id> --item "text"  # コンボボックス選択
wpf-agent ui close --pid <pid> [--force]                 # WM_CLOSE で終了 (--force: 起動元チェックスキップ)
```

#### 読み取り系コマンド (ガード対象外 — 一時停止中も使用可)
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

### カスタムスキル (スラッシュコマンド)
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

### セレクタの優先順位
1. `automation_id` (最も安定)
2. `name` + `control_type`
3. `bounding_rect` の中心クリック (最後の手段)

### 自然言語リクエストへの対応

ユーザーが以下のような自然言語で依頼した場合、**対応するスキルまたは `wpf-agent ui` コマンドを使って実行すること**。スラッシュコマンドを知らないユーザーでも自然に使えるようにする。

**重要**: 「wpf-agent で〇〇して」「wpf-agent を使って〇〇」のように **`wpf-agent` が明示されている場合は、必ず `wpf-agent` のコマンドやスキルを使って実行すること**。他のツールや手段で代替しない。

| ユーザーの発言（例） | 実行すべきアクション |
|---------------------|---------------------|
| 「デバッグして」「wpf-agentでデバッグ」「動かして確認」 | 対象アプリを `wpf-agent launch` で起動し、`/wpf-explore` で探索。exe パスが不明ならプロファイルか会話から推定、それでも不明なら聞く |
| 「動作確認して」「テストして」「確認して」 | `/wpf-verify` を実行（exe パスが不明なら聞く）。起動済みなら `/wpf-explore` で探索 |
| 「画面を見て」「UI を確認して」「スクショ撮って」 | `/wpf-inspect` を実行 |
| 「探索テストして」「全部触って」 | `/wpf-explore` を実行 |
| 「ユーザビリティテストして」「ペルソナテストして」 | `/wpf-usability-test` を実行 |
| 「ランダムテストして」 | `/wpf-random` を実行 |
| 「シナリオテストして」 | `/wpf-scenario` を実行 |
| 「チケット見せて」「バグ一覧」 | `/wpf-ticket` を実行 |
| 「チケット整理して」 | `/wpf-ticket-triage` を実行 |
| 「〇〇に入力して」「テキストを入れて」 | `/wpf-type` を実行。**python/xdotool で直接入力しない** |
| 「〇〇の値を読んで」「テキストを取得して」 | `wpf-agent ui read --pid <pid> --aid <id>` を実行。**python で直接読み取らない** |
| 「〇〇をクリックして」「ボタン押して」 | `/wpf-click` を実行 |
| 「起動して」「アプリを立ち上げて」 | `wpf-agent launch --exe <path>` で起動 |
| 「閉じて」「終了して」 | `wpf-agent ui close --pid <pid>` で終了 |

#### 判断のフロー
1. **`wpf-agent` が明示されているか？** → 明示されていれば必ず `wpf-agent` のコマンド/スキルを使う。他のツールで代替しない
2. 対象アプリの指定があるか？ → なければプロファイル (`profiles.json`) や直近の会話から推定、それでも不明なら聞く
3. アプリが起動済みか？ → `wpf-agent ui windows --brief` で確認
4. 起動済みなら `wpf-agent ui` コマンドや `/wpf-explore` で直接操作
5. 未起動なら `wpf-agent launch --exe <path>` で起動してから操作。検証が目的なら `/wpf-verify --exe <path>` を使う
<!-- wpf-agent:end -->
