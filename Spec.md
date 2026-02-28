# 仕様書：Claude Code連携 WPF UI デバッグ自動化ループ

## 1. 目的

WPF（Windows デスクトップ）アプリケーションの画面状態をスクリーンショット等で取得し、Claude（Claude Code/Claude API）による解析結果に基づいて **Windows上でUI操作を自動実行**するエージェントループを構築する。

主用途:

- デバッグ支援
- UI回帰テスト
- 手順実行の自動化
- 探索的テスト（ランダムテスト）

本プロジェクトでは、AIが直接OSを操作するのではなく、AIは **操作命令（構造化）を生成**し、ローカル実行器（ツール層）が **厳密な検証の上でUI操作を実行**する。

追加要件として、以下を実現する。

- **シナリオテスト**（手順＋期待結果を定義したテスト）の実行
- **ランダムテスト**（探索的に操作を生成し、クラッシュ・UI破綻・不変条件違反などを検出）の実行
- **問題チケットの自動生成**（再現手順／現在の結果／期待する結果を必須で含む）
- **原因調査の補助**（可能な限り原因候補を推定し、証跡を添付）

---

## 2. 前提・想定環境

- OS: Windows 10/11
- 対象アプリ: WPF（.NET 8想定、ただしWPFであればバージョン依存は低い）
- 実行者: ローカルPC上で動作する自動化ランナー
- AI: Claude（Claude Code もしくは Claude API 経由）
- UI自動化方式（推奨）: UI Automation（UIA）ベース
  - Python: `pywinauto`（`backend="uia"`）を第一候補
  - フォールバック: OCR + 座標クリック（必要時のみ）

### 2.1 任意アプリ指定（必須要件）

特定アプリにハードコードせず **任意のデスクトップアプリ** をターゲット指定できること。

#### 2.1.1 ターゲット指定方式（優先順）

1. **プロセスID（PID）指定**（最も確実）
2. **プロセス名**（例: `MyApp.exe`）
3. **起動パス（EXEパス）**（起動も含む）
4. **ウィンドウタイトル正規表現**（例: `.*MyApp.*`）
5. （任意）**ウィンドウクラス名** や **Automation Root要素** による特定

#### 2.1.2 運用モード

- **Attachモード**: 既に起動しているアプリへ接続（PID/プロセス名/タイトルで特定）
- **Launchモード**: EXEパス＋引数で起動して接続（起動待ち含む）

### 2.2 セットアップ容易性（必須要件）

- 開発者以外でも導入できることを目標とし、**ワンコマンド初期化**（`init`）と **プロファイル設定**（`profiles`）を提供する。
- 追加依存（OCRなど）は **オプション扱い** とし、最小構成は UIAのみで動作する。

---

## 3. スコープ

### 3.1 実装するもの

1. **エージェントループ（制御ランナー）**
   - 画面取得 → AI解析 → 操作計画 → UI操作 → 検証 → 次ステップ の繰り返し
2. **UI操作ツール群（ローカル実行器）**
   - UIAでの要素列挙・クリック・入力・状態取得
3. **AIとの連携（Claude Code / MCP または API）**
   - AIがツールを呼び出せる形（MCPサーバー形式を推奨）
4. **ログ／リプレイ／失敗時デバッグ支援**
   - スクショ、AI入出力、ツール呼び出し、結果を保存
5. **テスト実行基盤**
   - シナリオテストとランダムテストの実行・検証・チケット生成

### 3.2 スコープ外（非対象）

- AIが自由記述のままOSを操作する仕組み（安全性のため）
- 画像解析だけで完全に要素同定する“座標主軸”の自動化（不安定のため）
- Webや外部サービスに対する自動操作

---

## 4. 全体アーキテクチャ

### 4.1 役割分離（重要）

- **AI（Claude）**: 画面状態の理解、次に行うべき操作の決定、ツール呼び出し（構造化）
- **ツール層（ローカル実行器）**: UI操作の実行（UIA/OCR/座標）、結果の返却
- **ランナー**: ループ制御、失敗時の再試行、タイムアウト、ログ記録、サニタイズ

### 4.2 データフロー

1. `screenshot()` で画面取得（必要に応じて対象ウィンドウ限定）
2. 画像＋目的（タスク）をAIに入力
3. AIは **ツール呼び出し**（例: `list_controls`, `click`, `type_text`）を返す
4. ランナーは呼び出しを検証し、ツール層へ実行依頼
5. ツール層は実行結果（成功/失敗・例外・状態）を返す
6. 必要に応じて再度 `screenshot()` や `read_text()` で検証
7. 終了条件（達成/失敗/最大ステップ）で停止

---

## 5. 機能要件（共通）

### 5.1 失敗（不具合）判定の基本オラクル（必須）

最小構成として、以下を不具合として扱う。

- アプリがクラッシュした／プロセスが終了した
- 例外ダイアログ、致命的エラー画面、未処理例外ログ等が検出された
- 操作対象が「存在するはず」なのにUIA上で見つからない（期待要素欠落）
- UIがフリーズした（一定時間応答なし）
- シナリオで定義された期待結果と一致しない

拡張オラクル（任意）:

- 画面上にエラー文言が表示（OCR/テキスト検出）
- 不変条件違反（例：保存後に「保存済」表示が出る、など）

### 5.2 安全性（特にランダムテスト時）

- **破壊的操作（削除・終了・外部送信等）をデフォルト禁止**。
- 破壊的操作を許可する場合は、プロファイル側で明示し、さらに二重確認ステップを要求する。

### 5.3 ウィンドウ管理

- `list_windows()`
  - 表示中のトップレベルウィンドウ一覧を返す
- `focus_window(window_query | target_id)`
  - 正規表現/部分一致等で対象ウィンドウを前面化
- `wait_window(window_query | target_id, timeout_ms)`
  - ウィンドウ出現待ち
- `resolve_target(target_spec)`
  - `target_spec` から対象アプリ（ウィンドウ/プロセス）を一意に解決し、`target_id` を返す

`target_spec` 例:

- `{ "pid": 12345 }`
- `{ "process": "MyApp.exe" }`
- `{ "exe": "C:/path/MyApp.exe", "args": ["--dev"] }`
- `{ "title_re": ".*MyApp.*" }`

### 5.4 UIA要素列挙

- `list_controls(window_query | target_id, depth?, filter?)`
  - UIAツリーから要素を列挙し、以下情報を返す
    - `automation_id`, `name`, `control_type`, `enabled`, `visible`, `bounding_rect`（可能なら）, `value`（可能なら）
  - フィルタで `control_type` などを絞れる

### 5.5 UI操作

- `click(window_query | target_id, selector)`
  - selector同定優先順:
    1. `automation_id`
    2. `name` + `control_type`
    3. `bounding_rect` 中心クリック（最後の手段）
- `type_text(window_query | target_id, selector, text)`
- `select_combo(window_query | target_id, selector, item_text)`
- `toggle(window_query | target_id, selector, state?)`

### 5.6 状態取得・検証

- `read_text(window_query | target_id, selector)`
- `get_state(window_query | target_id, selector)`
  - `enabled/visible/selected/value` 等を取得
- `screenshot(window_query | target_id?, region?)`
  - PNGとして保存し、パス/IDを返す

### 5.7 OCRフォールバック（任意）

- `ocr_find(text, screenshot_id)`
- `click_xy(x, y)`

※OCRと座標クリックは、UIAで見つからないカスタム描画UIへの対応オプション。

---

## 6. テスト実行モード要件（追加要件・必須）

本システムは、同一のUI操作ツール群を用いて以下2モードを提供する。

- **Scenarioモード（シナリオテスト）**
- **Randomモード（ランダム／探索的テスト）**

両モード共通で、失敗検出時は **問題チケットを生成**し、可能であれば最小再現手順に縮約（minimize）する。

### 6.1 シナリオテスト

#### 6.1.1 定義形式

- シナリオはファイルで定義し、CLIから実行可能とする
- 形式は YAML または JSON（実装ではどちらかに統一）

#### 6.1.2 シナリオ構造（最小）

- メタ情報: `id`, `title`, `tags`, `owner`, `created_at`
- ターゲット: `profile` または `target_spec`
- ステップ列:
  - `action`（`click`/`type_text`/`select_combo`/`toggle`/`wait_for` など）
  - `selector`（`automation_id`/`name`/`control_type`）
  - `args`
  - `expected`
- 終了条件:
  - 成功条件（期待が満たされた）
  - 失敗条件（タイムアウト、期待不一致、クラッシュ等）

#### 6.1.3 期待結果（expected）の最小仕様（必須）

- `exists`
- `text_equals`
- `enabled`
- `selected`

推奨拡張:

- `text_contains`, `value_equals`, `regex`, `count_greater_equal`, `screenshot_diff`（簡易）

#### 6.1.4 失敗時挙動（必須）

- 期待結果未達時に問題チケットを生成する
- 失敗地点の前後で以下を採取する
  - スクリーンショット
  - UIAスナップショット
  - 直前N操作ログ（Nは設定可能、デフォルト20）

### 6.2 ランダム（探索的）テスト

#### 6.2.1 入力（探索プロファイル）

- `target`（`profile`/`target_spec`）
- `seed`（省略時は生成し必ず記録）
- `max_steps`
- `action_space`（重み/前提条件/破壊フラグ）
- `invariants`（任意推奨）
- `safety`（破壊的操作の禁止/許可、二重確認）

#### 6.2.2 Exploration Strategy（必須最小）

- 一様ランダム＋重み付け

任意拡張:

- カバレッジ指標に基づく選択（新規画面/新規要素優先）
- 状態保存（スナップショット）と戻り（リセット）

#### 6.2.3 Seed/Replay（必須）

- 乱数seedを記録し、同一seedで再実行できること
- 実行アクション列から **AI無しでリプレイ** できること

#### 6.2.4 最小化（推奨）

- 失敗再現手順を可能な範囲で短縮する
- 最低限、以下を提供する
  - 直前N操作の切り出し
  - 前半/後半削除を試す簡易縮約

---

## 7. 問題チケット要件（必須）

### 7.1 保存形式

- 生成先: `artifacts/tickets/<session_id>/TICKET-<timestamp>-<shortid>/`
- 必須ファイル:
  - `ticket.md`
  - `repro.actions.json`
  - `screens/`
  - `uia/`
  - `runner.log`
- 任意ファイル:
  - `ticket.json`
  - `app.log` / `crash.dmp` / `eventlog.txt`

### 7.2 ticket.md の必須項目

- **Repro Steps（再現手順）**: 番号付き
- **Actual Result（現在の結果）**
- **Expected Result（期待する結果）**
- **Title**
- **Summary**
- **Environment**（OS、ターゲット指定、プロファイル名、seed、ビルド種別等）
- **Evidence**（添付一覧）
- **Root Cause Hypothesis**（根拠付き、断定しない）

### 7.3 原因調査補助（可能な限り）

- 直前操作対象（selector）と時点UIA状態（enabled/visible/bounding）
- 失敗直前/直後のUIA差分（要素消失/非活性化等）
- エラーUI文言（OCR/テキスト）
- 取得可能ならアプリログ、未処理例外スタック、Windowsイベントログ

---

## 8. AI側の出力仕様（構造化）

AIが返すのは自然言語ではなく、**ツール呼び出し**（または厳密JSONのアクション列）とする。

### 8.1 アクションJSON（例）

```json
[
  {"tool":"focus_window","args":{"window_query":".*MyApp.*"}},
  {"tool":"list_controls","args":{"window_query":".*MyApp.*"}},
  {"tool":"click","args":{"window_query":".*MyApp.*","selector":{"automation_id":"SettingsButton"}}},
  {"tool":"type_text","args":{"window_query":".*MyApp.*","selector":{"automation_id":"ServerUrlTextBox"},"text":"http://localhost:1234"}},
  {"tool":"click","args":{"window_query":".*MyApp.*","selector":{"automation_id":"SaveButton"}}},
  {"tool":"screenshot","args":{"window_query":".*MyApp.*"}}
]
```

### 8.2 AI安全制約

- 座標クリックは原則禁止（UIA selector が取れない時のみ許可）
- 同一操作の連打禁止（必ず状態再取得を挟む）
- 破壊的操作は明示許可がある場合のみ

---

## 9. 非機能要件

### 9.1 安定性

- 1操作ごとに待機・確認（`wait_for` / `get_state`）を挟む
- タイムアウト設定
  - デフォルト: 10秒
  - 各ツールで上書き可能

### 9.2 ロギング / 監査

各ステップで以下を保存する。

- スクリーンショット（PNG）
- UIAスナップショット（JSON）
- AIへの入力プロンプト
- AIの出力（ツール呼び出し/JSON）
- 実行ツール呼び出しと結果（成功/例外/ログ）

`1実行 = 1セッションID` でフォルダ分けする。

### 9.3 リプレイ

- 収集したアクションJSONを再実行できる
- AI無しでリプレイ可能

### 9.4 セキュリティ

- ツール層は許可操作のみ実装（ホワイトリスト）
- ファイル操作/ネットワーク送信/プロセス起動は原則禁止（必要時は要件化して追加）

### 9.5 パフォーマンス

- UIA列挙は重い場合があるため深さ・フィルタ指定を可能にする
- スクショは必要時取得を基本とし、毎回必須でないモードを用意する

---

## 10. 実装方式（推奨）

### 10.1 Claude Code + MCP構成（第一成果）

- ローカルにMCPサーバー（stdio）を実装
- Claude Codeからツールとして呼び出せるよう登録
- MCPサーバー内部で `pywinauto`（UIA）を呼び出す

### 10.2 代替案（API直結）

- Claude APIへ画像＋指示を送信
- 返却アクションJSONをランナーが実行

### 10.3 セットアップUX（最重要）

#### 10.3.1 配布形態（推奨）

- ZIP配布（推奨）: `wpf-ui-agent/`
  - `wpf-agent.exe`（ランナー＋MCPサーバー同梱の単体実行）
  - `setup.ps1`（初期化とClaude Code登録支援）
  - `profiles.json`（ターゲットアプリ定義）
  - `README.md`

Python実装時は、PyInstaller等で単体exe化することが望ましい。

#### 10.3.2 ワンコマンド初期化

`setup.ps1` 実行で以下を実施する。

1. 前提チェック（Windows/権限/必要コンポーネント）
2. `profiles.json` テンプレ生成
3. Claude CodeへのMCP登録（コマンド例表示）
4. スモークテスト（デモシナリオAをdry-run実行）

#### 10.3.3 CLI要件

- `wpf-agent init`
- `wpf-agent profiles list/add/edit/remove`
- `wpf-agent run --profile <name>`
- `wpf-agent attach --pid <pid>`
- `wpf-agent launch --exe <path> -- <args...>`
- （推奨追加）`wpf-agent scenario run --file <scenario.yaml> --profile <name>`
- （推奨追加）`wpf-agent random run --profile <name> --max-steps 200 --seed 12345`
- （推奨追加）`wpf-agent replay --file repro.actions.json`
- （推奨追加）`wpf-agent tickets open --last`

#### 10.3.4 プロファイル形式（任意アプリ指定）

`profiles.json` に複数アプリを登録可能とする。

- `name`: 例 `MyApp-Dev`
- `match`: `pid` / `process` / `title_re` / `exe`
- `launch`: 起動パス・引数（任意）
- `timeouts`: 起動待ち等
- `safety`: 破壊的操作の禁止/許可

---

## 11. 成果物（Deliverables）

1. ソースコード一式
   - `runner/`（ループ制御、ログ、リプレイ）
   - `mcp_server/`（ツール実装）
   - `schemas/`（アクションJSON/ツール引数スキーマ）
2. セットアップ手順書
   - Windows環境構築、依存関係、Claude CodeへのMCP登録手順
3. 仕様・設計ドキュメント（簡易で可）
   - ツール一覧、引数、エラーコード、ログ形式
4. デモシナリオ（最低2本）
   - (A) 設定画面を開き、テキスト入力して保存
   - (B) 画面遷移（ダイアログ含む）を伴う操作
5. テスト
   - ツール層の単体テスト（可能な範囲で）
   - デモの実行ログ例（セッションフォルダ）
6. 配布物（必須）
   - `wpf-agent.exe`（単体実行可能）または同等の簡易配布物
   - `setup.ps1`
   - `profiles.json` テンプレ
   - `README.md`（最短手順が1ページで分かる）

---

## 12. 受け入れ条件（Acceptance Criteria）

- Claude Codeからツールが呼び出せる（MCP経由）
- 対象アプリを任意指定できる（PID/プロセス名/EXE/タイトル正規表現の **4方式すべて**）
- `profiles.json` で複数アプリを登録し、`--profile` で切替できる
- 対象アプリのウィンドウを識別し、前面化できる
- UIAでコントロール一覧を取得できる
- AutomationId指定でクリック・入力が成功する
- 各操作後に状態確認ができる（スクショまたはUIA値）
- シナリオテストで期待不一致時に問題チケットが生成される
- ランダムテストが指定ステップ数実行でき、失敗時に問題チケットが生成される
- チケットに「再現手順／現在の結果／期待する結果」が必ず含まれる
- チケットにスクショ、UIAスナップショット、直前ログが添付される
- seedおよびアクション列により、AI無しで再現できる
- 1セッションのログがフォルダに完全保存される
- `setup.ps1` または `wpf-agent init` から **10分以内にスモークテスト完了（目標）**

---

## 13. リスクと対策

- **UIAに要素が見えない**（カスタム描画/独自コントロール）
  - 対策: `AutomationProperties.AutomationId` 付与、必要に応じてAutomationPeer実装
  - 代替: OCR + 座標クリック（限定利用）
- **AIが誤操作する**
  - 対策: ツールホワイトリスト化、破壊的操作禁止、二重確認
- **ウィンドウタイトルが変動する**
  - 対策: PID/プロセス名/正規表現/クラス名等を併用

---

## 14. 実装マイルストーン（推奨）

1. PoC（最小）
   - `list_windows` / `resolve_target` / `focus_window` / `list_controls` / `click` / `type_text` / `screenshot`
   - 任意アプリ指定（PID/タイトル）でデモ(A)達成
2. 配布・セットアップ整備
   - `wpf-agent init` / `profiles.json` / `setup.ps1`
   - Claude CodeへのMCP登録導線
   - スモークテスト
3. 安定化
   - `wait_for`, `get_state`, エラーハンドリング, リトライ
   - ログ整備、リプレイ
4. フォールバック導入（必要時）
   - OCR/座標クリック
   - デモ(B)達成

### 14.1 対象WPFアプリ側の推奨対応

- 主要コントロールに `AutomationProperties.AutomationId` を付与
- 変化するラベル等にも識別可能な Name/AutomationId を付与
- カスタムコントロールは必要に応じてAutomationPeerを実装

### 14.2 運用モード

- 安全モード: UIAのみ、座標クリック禁止
- 拡張モード: UIA + OCR（座標クリック許可）

### 14.3 事前ヒアリング項目（任意）

- 対象WPFアプリのウィンドウタイトル（または識別方法）
- 最初に自動化したい具体的シナリオ（画面遷移手順）
- UIAで見えない箇所の有無（カスタム描画の程度）

---

以上。
