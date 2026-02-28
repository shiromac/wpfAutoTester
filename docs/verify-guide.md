# ビルド後自動検証 (`verify`) 使い方ガイド

## 概要

`wpf-agent verify` は、WPF アプリを**起動 → スモークテスト → UI要素チェック → 操作テスト → レポート**まで一発で実行するコマンドです。

Claude Code がコードを書いた直後に「ちゃんと動くか？」を自動確認する用途を想定しています。

---

## クイックスタート

### 最小限の使い方（スモークテストのみ）

```bash
wpf-agent verify --exe bin/Debug/net8.0-windows/MyApp.exe
```

これだけで以下を自動チェックします:

| チェック名 | 内容 |
|---|---|
| `app_launches` | プロセスが起動して生存している |
| `window_visible` | ウィンドウが表示されフォーカス可能 |
| `responsive` | UI がフリーズしていない |
| `no_error_dialogs` | エラーダイアログが出ていない |

加えて、スクリーンショットとコントロール一覧（JSON）をセッションディレクトリに保存します。

### 出力例

```
Verifying: bin/Debug/net8.0-windows/MyApp.exe
Session: a1b2c3d4e5f6
  [PASS] app_launches: Process alive
  [PASS] window_visible: Window is visible and focusable
  [PASS] responsive: Responsive
  [PASS] no_error_dialogs: No error dialogs found

VERIFICATION PASSED

Session: a1b2c3d4e5f6
Controls found: 12
Screenshot: artifacts/sessions/a1b2c3d4e5f6/screens/step-0002.png
```

---

## CLI オプション一覧

```bash
wpf-agent verify [OPTIONS]
```

| オプション | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `--exe <path>` | Yes | — | 起動する実行ファイルのパス |
| `--args <text>` | No | `""` | 起動引数（スペース区切り） |
| `--title-re <regex>` | No | 自動検出 | ウィンドウタイトルの正規表現 |
| `--spec <path>` | No | なし | 検証スペック YAML ファイル |
| `--timeout <ms>` | No | `5000` | 起動待機時間（ミリ秒） |
| `--no-close` | No | `false` | 検証後もアプリを閉じない |

### 使用例

```bash
# 基本（スモークテストのみ）
wpf-agent verify --exe MyApp.exe

# 引数付きで起動
wpf-agent verify --exe MyApp.exe --args "--debug --port 8080"

# タイトルで特定（複数ウィンドウがある場合）
wpf-agent verify --exe MyApp.exe --title-re "メインウィンドウ"

# 起動が遅いアプリ（10秒待機）
wpf-agent verify --exe MyApp.exe --timeout 10000

# 検証後もアプリを開いたままにする
wpf-agent verify --exe MyApp.exe --no-close

# スペック YAML でフル検証
wpf-agent verify --exe MyApp.exe --spec verify-spec.yaml
```

---

## 検証スペック YAML

スモークテストに加えて、特定の UI 要素の存在確認や操作テストを行う場合は YAML ファイルを指定します。

### フォーマット

```yaml
# verify-spec.yaml

# アプリ設定（CLIオプションでも上書き可能）
app:
  exe: "bin/Debug/net8.0-windows/MyApp.exe"
  args: []
  title_re: "MyApp.*"
  startup_wait_ms: 5000

# Phase 3: UI要素の存在・状態チェック
expected_controls:
  - selector: {automation_id: "MainButton"}
    expect: {exists: true, enabled: true}

  - selector: {automation_id: "StatusLabel"}
    expect: {exists: true, text: "Ready"}

  - selector: {name: "メニュー", control_type: "MenuBar"}
    expect: {exists: true, visible: true}

# Phase 4: 操作 → 検証ペア
interactions:
  - name: "ボタンクリックでステータス変更"
    action: click
    selector: {automation_id: "MainButton"}
    after:
      - selector: {automation_id: "StatusLabel"}
        expect: {text: "Clicked"}

  - name: "テキスト入力"
    action: type_text
    selector: {automation_id: "InputField"}
    text: "hello"
    after:
      - selector: {automation_id: "InputField"}
        expect: {text: "hello"}
```

### セレクタの書き方

セレクタは以下の優先順位で指定します:

```yaml
# 1. automation_id（最も安定、推奨）
selector: {automation_id: "BtnSubmit"}

# 2. name + control_type
selector: {name: "送信", control_type: "Button"}

# 3. name のみ
selector: {name: "送信ボタン"}

# 4. index 指定（同じ条件の N 番目）
selector: {control_type: "Button", index: 2}
```

### expect で使えるプロパティ

| プロパティ | 型 | 説明 |
|---|---|---|
| `exists` | `bool` | 要素が存在するか |
| `enabled` | `bool` | 操作可能か |
| `visible` | `bool` | 表示されているか |
| `text` | `string` | テキストが完全一致するか |
| `selected` | `bool` | 選択状態か |

### interactions で使えるアクション

| アクション | 追加パラメータ | 説明 |
|---|---|---|
| `click` | — | 要素をクリック |
| `type_text` | `text`, `clear`(省略時true) | テキスト入力 |
| `select_combo` | `item_text` | コンボボックス選択 |
| `toggle` | `state`(省略時トグル) | チェックボックス切替 |

---

## 検証フェーズの詳細

`verify` は以下の 5 フェーズを順に実行します:

```
Phase 1: Launch
  └─ アプリ起動 → 待機 → 生存確認

Phase 2: Smoke Test（常に実行）
  ├─ ウィンドウ表示確認
  ├─ UI応答確認
  ├─ エラーダイアログ検出
  ├─ スクリーンショット保存
  └─ コントロール一覧保存

Phase 3: Element Verification（expected_controls 指定時のみ）
  └─ 各要素の存在・状態チェック

Phase 4: Interaction Tests（interactions 指定時のみ）
  └─ 操作実行 → 事後条件チェック → スクリーンショット

Phase 5: Cleanup
  └─ auto_close=true ならプロセス終了
```

---

## セッション成果物

検証結果は `artifacts/sessions/<session_id>/` に保存されます:

```
artifacts/sessions/a1b2c3d4e5f6/
├── screens/
│   ├── step-0002.png      # スモークテスト時のスクリーンショット
│   ├── step-0004.png      # interaction 1 の後
│   └── step-0005.png      # interaction 2 の後
├── uia/
│   └── step-0002.json     # コントロール一覧（JSON）
└── runner.log             # 全ステップの構造化ログ
```

---

## Claude Code スキル（`/wpf-verify`）

Claude Code 上で `/wpf-verify` と入力すると、ビルド → 検証 → 修正の一連のフローを対話的に実行できます。

```
/wpf-verify MyApp.csproj をビルドしてボタンが動くか確認して
```

スキルは以下を自動で行います:
1. `dotnet build` でビルド
2. `wpf-agent verify --exe <path>` で検証
3. 失敗時はスクリーンショットとログを分析
4. コード修正を提案・実行

---

## 典型的なユースケース

### ケース 1: コード変更後の回帰確認

```bash
# 変更をビルドして即座に確認
dotnet build -c Debug && wpf-agent verify --exe bin/Debug/net8.0-windows/MyApp.exe
```

### ケース 2: 新機能追加の検証

```yaml
# new-feature-spec.yaml
expected_controls:
  - selector: {automation_id: "NewFeatureButton"}
    expect: {exists: true, enabled: true}

interactions:
  - name: "新機能ボタンをクリック"
    action: click
    selector: {automation_id: "NewFeatureButton"}
    after:
      - selector: {automation_id: "ResultLabel"}
        expect: {text: "Success"}
```

```bash
wpf-agent verify --exe MyApp.exe --spec new-feature-spec.yaml
```

### ケース 3: 起動確認のみ（CI用）

```bash
# 起動して3秒以内にクラッシュしなければOK
wpf-agent verify --exe MyApp.exe --timeout 3000
```

### ケース 4: 手動デバッグとの併用

```bash
# アプリを閉じずに残して手動でも確認
wpf-agent verify --exe MyApp.exe --no-close
```

---

## トラブルシューティング

### アプリが起動しない（`app_launches` FAIL）

- `--exe` のパスが正しいか確認
- 依存 DLL が不足していないか確認
- `--timeout` を長くしてみる

### ウィンドウが見つからない（`window_visible` FAIL）

- アプリがスプラッシュスクリーンを出している場合は `--timeout` を増やす
- 複数ウィンドウがある場合は `--title-re` でメインウィンドウを特定

### 要素が見つからない（`element_*` FAIL）

- `automation_id` が正しいか、Visual Studio の UI デバッグツールで確認
- コントロール一覧 JSON（`uia/step-*.json`）で実際の要素名を確認
- 要素の読み込みが遅い場合は `startup_wait_ms` を増やす

### 操作後のチェックが失敗する（`interaction_*` FAIL）

- UI の更新に時間がかかる場合がある（現在の待機は 0.5 秒固定）
- スクリーンショットで操作後の画面を確認
