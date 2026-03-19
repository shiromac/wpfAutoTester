# WPF UI Debug Automation Agent

## プロジェクト概要
Claude Code と統合された WPF UI 自動化エージェント。pywinauto (UIA) を使用して Windows デスクトップアプリを操作し、以下の機能を提供する:

- **UI 自動操作** — クリック・テキスト入力・スクリーンショット等を Claude Code から直接実行
- **探索テスト** — AI が自律的にアプリの全画面を探索し、異常を検出
- **ランダムテスト** — ランダム操作でクラッシュや未処理例外を発見
- **シナリオテスト** — YAML 定義のテストシナリオを自動実行
- **ユーザビリティテスト** — ペルソナベースの操作性評価
- **ビルド後検証** — exe を起動して基本動作を自動チェック
- **バグチケット管理** — 発見した問題のチケット作成・トリアージ

詳しい使い方（CLI コマンド一覧・MCP ツール・UI 操作コマンド詳細）は **[docs/wpf-agent-usage.md](docs/wpf-agent-usage.md)** を参照。

## カスタムスキル (スラッシュコマンド)
- `/wpf-setup` — セットアップとMCPサーバー登録
- `/wpf-ui` — UI操作（調査・クリック・入力・スクリーンショット）
- `/wpf-test` — テスト実行（探索・ランダム・シナリオ・ユーザビリティ・検証・リプレイ）
- `/wpf-ticket` — チケット管理（確認・作成・整理）

## 自然言語リクエストへの対応

ユーザーが以下のような自然言語で依頼した場合、**対応するスキルまたは `wpf-agent ui` コマンドを使って実行すること**。スラッシュコマンドを知らないユーザーでも自然に使えるようにする。

**重要**: 「wpf-agent で〇〇して」「wpf-agent を使って〇〇」のように **`wpf-agent` が明示されている場合は、必ず `wpf-agent` のコマンドやスキルを使って実行すること**。他のツールや手段で代替しない。

| ユーザーの発言（例） | 実行すべきアクション |
|---------------------|---------------------|
| 「デバッグして」「動かして確認」 | `wpf-agent launch` で起動 → `/wpf-test explore` で探索 |
| 「動作確認して」「テストして」 | `/wpf-test verify` を実行。起動済みなら `/wpf-test explore` |
| 「画面を見て」「スクショ撮って」 | `/wpf-ui inspect` を実行 |
| 「探索テストして」 | `/wpf-test explore` を実行 |
| 「ランダムテストして」 | `/wpf-test random` を実行 |
| 「シナリオテストして」 | `/wpf-test scenario` を実行 |
| 「ユーザビリティテストして」 | `/wpf-test usability` を実行 |
| 「チケット見せて」「バグ一覧」 | `/wpf-ticket` を実行 |
| 「〇〇に入力して」 | `/wpf-ui type` を実行。**python/xdotool で直接入力しない** |
| 「〇〇の値を読んで」 | `wpf-agent ui read` を実行。**python で直接読み取らない** |
| 「〇〇をクリックして」 | `/wpf-ui click` を実行 |
| 「起動して」 | `wpf-agent launch --exe <path>` で起動 |
| 「閉じて」 | `wpf-agent ui close --pid <pid>` で終了 |

### 判断のフロー
1. **`wpf-agent` が明示されているか？** → 明示されていれば必ず `wpf-agent` のコマンド/スキルを使う
2. 対象アプリの指定があるか？ → なければプロファイルや会話から推定、不明なら聞く
3. アプリが起動済みか？ → `wpf-agent ui windows --brief` で確認
4. 起動済みなら `wpf-agent ui` コマンドや `/wpf-test explore` で直接操作
5. 未起動なら `wpf-agent launch` で起動してから操作

## テキスト入力・読み取りの禁止事項（重要）
UI 要素へのテキスト入力とテキスト読み取りは、**必ず `wpf-agent ui type` / `wpf-agent ui read` コマンド、または MCP ツール `type_text` / `read_text` を使うこと**。以下の手段で直接操作してはならない:

- **禁止**: `python -c` で pywinauto の `set_edit_text()`, `type_keys()`, `window_text()`, `get_value()` を直接呼ぶ
- **禁止**: `xdotool type`, `xdotool key` でキーボード入力をシミュレートする
- **禁止**: `python -c` で `keyboard`, `pyautogui`, `pynput` モジュールを使ってキー入力する
- **禁止**: クリップボード経由 (`pyperclip`, `xclip`, `xsel`, Ctrl+V) でテキストを貼り付ける
- **禁止**: `SendKeys`, `xte`, `ydotool` 等の外部ツールでキー入力をシミュレートする

理由: `wpf-agent ui type` / `wpf-agent ui send-keys` はマウス移動ガード (UI ガード) を通るため安全。直接操作はガードを回避してしまい、ユーザーの操作と競合する危険がある。

## Bash コマンド生成ルール
- `wpf-agent` コマンドは**パイプ (`|`) を使わず、組み込みオプションだけで完結させる**こと
  - パイプ付きコマンドは glob パーミッション `Bash(wpf-agent *)` にマッチしないため、**毎回ユーザーに権限確認ダイアログが表示されてしまう**
  - UI 要素の検索には `--search`, `--name-filter`, `--aid-filter`, `--type-filter`, `--has-aid`, `--has-name` オプションを使う
  - `--search`, `--name-filter`, `--aid-filter` はカンマ区切りで OR 検索できる（例: `--name-filter "OK,FAIL,SKIP"`）
  - NG: `wpf-agent ui controls --pid 1234 | python -c "import json,sys; ..."` ← 権限確認が毎回発生
  - NG: `for ... do wpf-agent ...; done` ← シェルループも glob にマッチしない。各コマンドを個別に実行すること
- `wpf-agent` コマンドは**必ず1行で記述**すること（改行禁止）
  - glob パーミッション `Bash(wpf-agent *)` の `*` は改行にマッチしない
  - やむを得ずパイプが必要な場合のみ `;` で1行にまとめる

## ディレクトリ構成
```
src/wpf_agent/
├── __init__.py, __main__.py   # パッケージ・エントリポイント
├── cli.py                     # Click ベース CLI (全コマンド定義)
├── config.py                  # ProfileStore / PersonaStore / Profile / Persona 等
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

docs/                          # ドキュメント
scenarios/                     # YAML シナリオ定義
testApp/                       # WPF テスト用サンプルアプリ (.NET 9)
artifacts/sessions/            # セッションログ (実行時生成)
artifacts/tickets/             # チケット (実行時生成)
tests/                         # ユニットテスト
.wpf-agent/                    # 設定ファイル
├── profiles.json              # 対象アプリ定義
└── personas.json              # ペルソナプリセット定義
```

## 開発
```
pip install -e .[dev]
python -m pytest tests/ -v
```

### 変更時の同期チェックリスト
CLI オプションや CLAUDE.md の内容を変更した場合、以下のファイルも同期すること:
1. **`docs/wpf-agent-usage.md`** — コマンドリファレンス・MCP ツール一覧・自然言語対応表など詳細ドキュメント
2. **`src/wpf_agent/_claude_md_snippet.md`** — `wpf-agent init` 実行時にユーザーの CLAUDE.md へ埋め込まれるテンプレート。ここを更新しないと新規セットアップ時に古い情報が配布される
3. **`.claude/skills/` 内の該当 SKILL.md** — 変更に関連するスキルのコード例・説明を更新
