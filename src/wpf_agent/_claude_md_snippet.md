<!-- wpf-agent:start -->
## WPF UI Debug Automation Agent (wpf-agent)

Claude Code と統合された WPF UI 自動化エージェント。pywinauto (UIA) を使用して Windows デスクトップアプリを操作する。

### Bash コマンド生成ルール
- `wpf-agent` やパイプ付きコマンドは**必ず1行で記述**すること（改行禁止）
  - glob パーミッション `Bash(wpf-agent *)` の `*` は改行にマッチしない
  - OK: `wpf-agent ui controls --pid 1234 | python -c "import json,sys; [print(c['name']) for c in json.load(sys.stdin) if c.get('name')]"`
  - NG: `wpf-agent ui controls --pid 1234 | python -c "\nimport json\n..."`

### CLI コマンド
```
wpf-agent init                           # 初期化
wpf-agent install-skills                 # Claude Code スキルインストール
wpf-agent profiles list/add/edit/remove  # プロファイル管理
wpf-agent personas list/add/edit/remove  # ペルソナプリセット管理
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
wpf-agent ui select-combo --pid <pid> --aid <id> --item "text"  # コンボボックス選択
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

| ユーザーの発言（例） | 実行すべきアクション |
|---------------------|---------------------|
| 「動作確認して」「テストして」「確認して」 | `/wpf-verify` を実行（exe パスが不明なら聞く）。起動済みなら `/wpf-explore` で探索 |
| 「画面を見て」「UI を確認して」「スクショ撮って」 | `/wpf-inspect` を実行 |
| 「探索テストして」「全部触って」 | `/wpf-explore` を実行 |
| 「ユーザビリティテストして」「ペルソナテストして」 | `/wpf-usability-test` を実行 |
| 「ランダムテストして」 | `/wpf-random` を実行 |
| 「シナリオテストして」 | `/wpf-scenario` を実行 |
| 「チケット見せて」「バグ一覧」 | `/wpf-ticket` を実行 |
| 「チケット整理して」 | `/wpf-ticket-triage` を実行 |

#### 判断のフロー
1. 対象アプリの指定があるか？ → なければプロファイル (`profiles.json`) や直近の会話から推定、それでも不明なら聞く
2. アプリが起動済みか？ → `wpf-agent ui windows --brief` で確認
3. 起動済みなら `wpf-agent ui` コマンドや `/wpf-explore` で直接操作
4. 未起動なら `/wpf-verify --exe <path>` で起動＋検証、または `wpf-agent launch` で起動してから操作
<!-- wpf-agent:end -->
