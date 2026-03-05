# シナリオ YAML 書き方ガイド

wpf-agent のシナリオテストで使う YAML ファイルの書き方リファレンス。

---

## 基本構造

```yaml
id: my-scenario               # シナリオID（ユニーク）
title: "シナリオの説明"         # タイトル
tags: [smoke, login]           # タグ（任意）
owner: tester                  # 作成者（任意）
profile: myapp                 # profiles.json のプロファイル名

steps:
  - action: アクション名
    selector:
      automation_id: 要素のID
    args:
      キー: 値
    expected:
      - type: アサーション種別
        value: 期待値
```

### ターゲット指定（どちらか一方）

| 方法 | 説明 |
|------|------|
| `profile: myapp` | profiles.json に登録済みのプロファイル名 |
| `target_spec:` | 直接指定（下記参照） |

```yaml
# target_spec の例
target_spec:
  exe: "C:/path/to/App.exe"     # exe パス指定（未起動なら起動）
  # args: ["--debug"]           # 起動引数（任意）

# その他の target_spec
target_spec:
  pid: 12345                    # PID 直接指定
target_spec:
  process: "MyApp.exe"          # プロセス名
target_spec:
  title_re: ".*MyApp.*"         # ウィンドウタイトル正規表現
```

---

## セレクタ（要素の指定方法）

```yaml
selector:
  automation_id: BtnOK           # automation_id（最も安定・推奨）
```

```yaml
selector:
  name: "OK"                    # 表示名
  control_type: Button          # コントロール種別
```

```yaml
selector:
  automation_id: ListItem
  index: 2                      # 同名要素が複数ある場合のインデックス
```

**優先順位**: `automation_id` > `name` + `control_type` > `bounding_rect`（最後の手段）

> **ヒント**: 要素の automation_id は `wpf-agent ui controls --pid <pid> --has-aid --brief` で確認できます。

---

## アクション一覧

### click — クリック

```yaml
- action: click
  selector:
    automation_id: SubmitButton
```

ダブルクリック:
```yaml
- action: click
  selector:
    automation_id: ListItem1
  args:
    double: true
```

### type_text — テキスト入力

```yaml
- action: type_text
  selector:
    automation_id: NameInput
  args:
    text: "山田太郎"
```

既存テキストをクリアせずに追記:
```yaml
- action: type_text
  selector:
    automation_id: NameInput
  args:
    text: "追記テキスト"
    clear: false               # デフォルトは true（クリアしてから入力）
```

### select_combo — コンボボックス選択

```yaml
- action: select_combo
  selector:
    automation_id: ColorCombo
  args:
    item_text: "赤"
```

### toggle — チェックボックス・トグル

```yaml
- action: toggle
  selector:
    automation_id: AgreeCheck
```

明示的に ON/OFF を指定:
```yaml
- action: toggle
  selector:
    automation_id: AgreeCheck
  args:
    state: true                # true=ON, false=OFF, 省略=反転
```

### drag — ドラッグ＆ドロップ

```yaml
- action: drag
  selector:
    automation_id: SourceItem
  args:
    dst_selector:
      automation_id: DropTarget
```

### focus_window — ウィンドウをフォーカス

```yaml
- action: focus_window
```

> **ヒント**: シナリオの最初のステップに入れておくと安全です。

### wait_for — 条件を待機

```yaml
- action: wait_for
  selector:
    automation_id: LoadingSpinner
  args:
    condition: visible
    value: false               # 非表示になるまで待つ
    timeout_ms: 10000          # タイムアウト（ミリ秒、デフォルト10000）
```

**condition の種類**:

| condition | value | 意味 |
|-----------|-------|------|
| `exists` | — | 要素が存在するまで |
| `enabled` | `true` / `false` | 有効/無効になるまで |
| `visible` | `true` / `false` | 表示/非表示になるまで |
| `text_equals` | `"文字列"` | テキストが一致するまで |
| `text_contains` | `"部分文字列"` | テキストに含まれるまで |
| `text_not_equals` | `"文字列"` | テキストが変わるまで |
| `text_changed` | — | テキストが何か変化するまで |

### screenshot — スクリーンショット

```yaml
- action: screenshot
```

---

## アサーション（expected）

各ステップの `expected` に検証条件を記述します。操作後に自動チェックされ、失敗するとシナリオが停止します。

```yaml
steps:
  - action: click
    selector:
      automation_id: SaveButton
    expected:
      - type: text_contains
        selector:                   # 別の要素を検証（省略するとステップのselectorを使用）
          automation_id: StatusLabel
        value: "保存しました"
```

### アサーション一覧

| type | value | 説明 |
|------|-------|------|
| `exists` | — | 要素が存在する |
| `text_equals` | `"文字列"` | テキストが完全一致 |
| `text_contains` | `"部分文字列"` | テキストに含まれる |
| `regex` | `"パターン"` | 正規表現にマッチ |
| `enabled` | `true` / `false` | 有効/無効状態 |
| `visible` | `true` / `false` | 表示/非表示状態 |
| `selected` | `true` / `false` | 選択状態 |
| `value_equals` | 任意の値 | 要素の value が一致 |

### セレクタの継承

`expected` 内の `selector` を省略すると、ステップの `selector` が使われます。

```yaml
- action: type_text
  selector:
    automation_id: InputField
  args:
    text: "hello"
  expected:
    - type: text_equals         # selector 省略 → InputField を検証
      value: "hello"
    - type: exists              # 別の要素を検証
      selector:
        automation_id: SubmitButton
```

---

## 実践パターン集

### パターン1: ログインフォーム

```yaml
id: login-success
title: "正常系: ログイン成功"
tags: [auth, smoke]
profile: myapp

steps:
  - action: focus_window

  - action: type_text
    selector:
      automation_id: UsernameInput
    args:
      text: "admin"

  - action: type_text
    selector:
      automation_id: PasswordInput
    args:
      text: "password123"

  - action: click
    selector:
      automation_id: LoginButton
    expected:
      - type: exists
        selector:
          automation_id: DashboardPanel
```

### パターン2: フォーム入力 → 保存 → 確認

```yaml
id: form-save
title: "フォーム入力して保存"
tags: [form, crud]
profile: myapp

steps:
  - action: focus_window

  - action: type_text
    selector:
      automation_id: NameField
    args:
      text: "テスト太郎"

  - action: select_combo
    selector:
      automation_id: CategoryCombo
    args:
      item_text: "カテゴリA"

  - action: toggle
    selector:
      automation_id: ActiveCheck
    args:
      state: true

  - action: click
    selector:
      automation_id: SaveButton
    expected:
      - type: text_contains
        selector:
          automation_id: StatusBar
        value: "保存"
      - type: enabled
        selector:
          automation_id: SaveButton
        value: true
```

### パターン3: ダイアログ操作

```yaml
id: delete-confirm
title: "削除確認ダイアログ"
tags: [dialog, delete]
profile: myapp

steps:
  - action: focus_window

  - action: click
    selector:
      automation_id: DeleteButton
    expected:
      - type: exists
        selector:
          name: "確認"
          control_type: Window

  - action: click
    selector:
      automation_id: ConfirmYesButton
    expected:
      - type: text_contains
        selector:
          automation_id: MessageLabel
        value: "削除しました"
```

### パターン4: 非同期処理の待機

```yaml
id: data-load
title: "データ読み込み待ち"
tags: [async, loading]
profile: myapp

steps:
  - action: focus_window

  - action: click
    selector:
      automation_id: LoadButton

  - action: wait_for
    selector:
      automation_id: LoadingIndicator
    args:
      condition: visible
      value: false
      timeout_ms: 15000

  - action: screenshot

  - action: click
    selector:
      automation_id: FirstRow
    expected:
      - type: exists
        selector:
          automation_id: DetailPanel
```

### パターン5: ドラッグ＆ドロップ

```yaml
id: drag-item
title: "アイテムをドラッグで移動"
tags: [drag, reorder]
profile: myapp

steps:
  - action: focus_window

  - action: drag
    selector:
      automation_id: Item_3
    args:
      dst_selector:
        automation_id: Item_1
    expected:
      - type: text_equals
        selector:
          automation_id: Item_1
        value: "移動されたアイテム"
```

---

## 実行方法

```bash
# YAML ファイルを指定して実行
wpf-agent scenario run --file scenarios/my-scenario.yaml

# プロファイルを上書き指定
wpf-agent scenario run --file scenarios/my-scenario.yaml --profile other-app
```

---

## 自動オラクル（暗黙のチェック）

`expected` を書かなくても、各ステップ後に以下が自動チェックされます:

- **プロセス生存**: アプリがクラッシュしていないか
- **UI 応答性**: アプリがフリーズしていないか（5秒タイムアウト）
- **エラーダイアログ**: "Error", "Exception", "Crash" 等のウィンドウが出ていないか

これにより、最低限のステップだけ書いても基本的な問題は検出できます。

---

## よくある間違い

### NG: selector なしでクリック
```yaml
# NG — 何をクリックするか不明
- action: click
  args: {}
```

### OK: selector を指定
```yaml
# OK
- action: click
  selector:
    automation_id: BtnOK
```

### NG: type_text で text を忘れる
```yaml
# NG — text がない
- action: type_text
  selector:
    automation_id: Input1
```

### OK: args.text を指定
```yaml
# OK
- action: type_text
  selector:
    automation_id: Input1
  args:
    text: "入力値"
```

### NG: expected の type を忘れる
```yaml
# NG — type がない
expected:
  - selector:
      automation_id: Label1
    value: "text"
```

### OK: type を指定
```yaml
# OK
expected:
  - type: text_equals
    selector:
      automation_id: Label1
    value: "text"
```

---

## automation_id の調べ方

シナリオを書く前に、対象アプリの automation_id を調べましょう。

```bash
# 全コントロール一覧（automation_id あり）
wpf-agent ui controls --pid <pid> --has-aid --brief

# 特定の種別で絞り込み
wpf-agent ui controls --pid <pid> --type-filter Button,Edit --has-aid --brief

# 名前で検索
wpf-agent ui controls --pid <pid> --search "保存" --brief
```
