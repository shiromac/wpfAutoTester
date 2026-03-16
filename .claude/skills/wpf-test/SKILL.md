---
name: wpf-test
description: テスト実行（探索・ランダム・シナリオ・ユーザビリティ・検証・リプレイ）
argument-hint: "[explore|random|scenario|usability|verify|replay] target and params"
---

WPF アプリのテストを実行してください。

指示: $ARGUMENTS

## モード判定

引数からモードを自動判定する:
- **explore モード**: "explore" / "探索" / "全部触って" / "デバッグ"
- **random モード**: "random" / "ランダム"
- **scenario モード**: "scenario" / "シナリオ"
- **usability モード**: "usability" / "ペルソナ" / "ユーザビリティ"
- **verify モード**: "verify" / "検証" / "確認" / `--exe` 指定あり
- **replay モード**: "replay" / "リプレイ"
- **判定不能**: ユーザーに確認する

---

## explore モード（AI誘導型探索テスト）

Claude Code 自身がスクリーンショットを見て判断し、`wpf-agent ui` コマンドで直接操作する。
外部 API キー (ANTHROPIC_API_KEY) は不要。

### 1. ターゲット特定
```bash
# 方法A: 未起動 → launch で起動し PID を取得
wpf-agent launch --exe <path>

# 方法B: 起動済み → ウィンドウ一覧から PID を探す
wpf-agent ui windows --brief

# 方法C: プロセス名から PID を取得
wpf-agent ui alive --process <name> --brief
```

### 2. セッションディレクトリ作成
```bash
wpf-agent ui init-session --prefix explore
```
出力 JSON の `path` をセッションディレクトリとして使用する。

### 3. ウィンドウフォーカス
```bash
wpf-agent ui focus --pid <pid>
```

### 4. 探索ループ（以下を繰り返す）

#### a. スクリーンショット撮影
```bash
wpf-agent ui screenshot --pid <pid> --save <session_dir>/step_N.png
```

#### b. スクリーンショットを確認
Read ツールで画像ファイルを読み込み、画面の状態を視覚的に把握する。

#### c. コントロール一覧取得
```bash
wpf-agent ui controls --pid <pid> --depth 4 --has-aid --brief
```
フィルタオプション: `--type-filter` (カンマ区切り), `--name-filter` (部分一致), `--has-name`, `--has-aid`, `--brief` (テーブル出力)。

#### d. 次の操作を判断
- まだ触っていないボタン、メニュー、タブを優先
- テキスト入力欄にはテスト値を入力
- チェックボックスはトグル
- エラーダイアログや異常な状態を発見したら記録

#### e. 操作実行
```bash
wpf-agent ui click --pid <pid> --aid <automation_id>
wpf-agent ui type --pid <pid> --aid <automation_id> --text "テスト値"
wpf-agent ui toggle --pid <pid> --aid <automation_id>
wpf-agent ui read --pid <pid> --aid <automation_id>
wpf-agent ui state --pid <pid> --aid <automation_id>
```

#### f. 操作結果を確認
再度スクリーンショットを撮影し、期待通りの変化があったか確認する。

### 5. チケット作成
探索完了後（中断された場合も含め）、CLI でチケットを作成する。問題なしの場合も作成する。
```bash
wpf-agent tickets create --title "タイトル" --summary "概要" --actual-result "実際の結果" --expected-result "期待される結果" --repro-steps "ステップ1" --repro-steps "ステップ2" --evidence "<session_dir>/explore_evidence.png" --root-cause "原因の仮説" --pid <pid>
```
**注意**: 全引数を1行で記述すること。

### 6. アプリ終了（wpf-agent で起動した場合）
```bash
wpf-agent close --pid <pid>
```

### 7. ユーザーへの報告
チケットのパス、探索したUI要素、実行した操作のサマリ、発見した問題、スクリーンショットパス一覧を表示する。

---

## random モード（ランダム探索テスト）

### 手順
1. .wpf-agent/profiles.json からプロファイルを確認
2. 実行:
```bash
wpf-agent random run --profile <profile> --max-steps <steps> --seed <seed>
```
3. 結果を確認し、失敗があればチケットの内容を表示
4. 再現する場合は seed を使ってリプレイ方法を案内

デフォルト値: max-steps: 200, seed: 自動生成

失敗時:
- `wpf-agent tickets open --last` で最新チケットを確認可能
- `wpf-agent replay --file <actions.json> --profile <profile>` で再現可能

---

## scenario モード（シナリオテスト）

**重要**: シナリオ YAML の書き方は `scenarios/GUIDE.md` にリファレンスがある。シナリオの作成・編集時は必ず Read ツールでこのガイドを読んでから作業すること。

### 方法A: YAMLファイルからの実行
```bash
wpf-agent scenario run --file <scenario.yaml> --profile <profile>
```

### 方法B: 指示からの対話的実行
1. `list_windows` → `resolve_target` で対象アプリを特定
2. `focus_window` でフォーカス
3. ユーザーの指示に従って各ステップを実行
4. 各ステップ後に `screenshot` / `read_text` / `get_state` で検証
5. 全ステップのアクション記録をJSON形式で出力

### 方法C: シナリオYAMLの生成
1. **`scenarios/GUIDE.md` を Read ツールで読む**（YAML 構造・アクション・アサーションのリファレンス）
2. 対象アプリのUIを `list_controls` で調査
3. ユーザーの指示からステップと期待結果を構成
4. `scenarios/GUIDE.md` のパターン集を参考に YAML ファイルを生成

---

## usability モード（ペルソナ型ユーザビリティテスト）

ペルソナ（架空のユーザー像）を設定し、ゴールだけを与えて「思考発話法」で操作する。
Claude Code 自身がペルソナになりきり、`wpf-agent ui` コマンドで直接操作する。

### 引数の解析
- `--pid <PID>` or `--exe <path>`: 対象アプリ（必須）
- `--goal "目的"`: ユーザーの目的（必須）
- `--persona <name_or_text>`: プリセット名 or インラインテキスト（省略時は "tanaka"）

### ペルソナの解決
1. **プリセット名として検索**: `wpf-agent personas list` の名前と一致するか確認
2. **インラインテキスト**: 一致しなければ指定テキストをそのままペルソナ説明として使用
3. **省略時のデフォルト**: "tanaka" を使用

### 準備
1. ターゲット特定（explore モードと同じ手順）
2. セッションディレクトリ作成: `wpf-agent ui init-session --prefix usability`
3. Write ツールで persona.md, thinkaloud.md, actions.md を作成
4. ウィンドウフォーカス

### メインループ（思考発話法）— 最大30ステップ

各ステップで:

#### a. スクリーンショット撮影 + 確認
```bash
wpf-agent ui screenshot --pid <pid> --save <session_dir>/step_NN.png
```

#### b. ペルソナとして思考を声に出す（スクリーンショットだけを見て判断）
**コントロール一覧は見ずに、画面の視覚情報だけで「何を押すか」を決める**（人間はコントロールツリーを見ない）。

> **[ペルソナ名] Step N:**
> 「（画面を見た第一印象）」
> 「（何をしようとしているか）」
> 「（どのボタン/要素を選ぶか、その理由）」
> 「（迷いや不安があれば正直に）」

Write ツールで `thinkaloud.md` に追記。

#### c. コントロール一覧で automation_id を特定
ステップ b で「押す」と決めた要素の automation_id を調べる。
```bash
wpf-agent ui controls --pid <pid> --depth 4 --has-aid --brief
```

#### d. 操作を実行
```bash
wpf-agent ui click --pid <pid> --aid <automation_id>
wpf-agent ui type --pid <pid> --aid <automation_id> --text "テスト値"
wpf-agent ui toggle --pid <pid> --aid <automation_id>
```

#### e. 結果を確認し反応を記録
Write ツールで `actions.md` に行を追記。

#### f. ユーザビリティ問題を記録
迷い、誤解、不安、フラストレーション、効率の悪さ、発見不能を問題として記録。

#### g. 終了判定
ゴール達成 / 断念 / 30ステップ到達でループ終了。

### 最終報告書の作成
Write ツールで `usability_report.md` を作成（テスト概要、発見された問題、改善提案、エビデンス一覧）。

### チケット作成
```bash
wpf-agent tickets create --title "タイトル" --summary "概要" --actual-result "実際の結果" --expected-result "期待される結果" --repro-steps "ステップ1" --evidence "パス" --root-cause "原因の仮説" --pid <pid>
```

---

## verify モード（ビルド後自動検証）

### 1. ビルド
```bash
dotnet build <project.csproj> -c Debug
```

### 2. スモークテスト
```bash
wpf-agent verify --exe <path/to/App.exe>
```
自動確認項目: 起動、ウィンドウ表示、UI応答、エラーダイアログなし、スクショ保存。

### 3. 詳細検証（spec YAML指定時）
```bash
wpf-agent verify --exe <path/to/App.exe> --spec verify-spec.yaml
```

### 4. 結果の解釈
- **VERIFICATION PASSED**: 全チェック合格
- **VERIFICATION FAILED**: 失敗内容を分析してコード修正を提案

### 5. チケット作成
```bash
wpf-agent tickets create --title "タイトル" --summary "概要" --actual-result "実際の結果" --expected-result "期待される結果" --evidence "スクリーンショットパス" --root-cause "原因の仮説"
```

### オプション
- `--title-re <regex>`: ウィンドウタイトルで特定
- `--timeout <ms>`: 起動待機時間（デフォルト5000ms）
- `--no-close`: 検証後もアプリを開いたまま

---

## replay モード（AI不要リプレイ再現）

### 手順
1. リプレイ対象のアクションファイルを特定（指定がない場合: 最新セッションの `actions.json`）
2. 実行:
```bash
wpf-agent replay --file <actions.json> --profile <profile>
```
または PID / タイトル指定:
```bash
wpf-agent replay --file <actions.json> --pid <pid>
wpf-agent replay --file <actions.json> --title-re ".*MyApp.*"
```
3. リプレイ結果（成功/エラー数）を報告

---

## 共通事項

### セレクタの優先順位
1. `--aid` (automation_id) — 最も安定
2. `--name` + `--control-type` — aid がない場合
3. スクリーンショットの座標情報から判断 — 最後の手段

### ユーザー中断の対応 (UI ガード)
UI 操作コマンド (`focus`, `click`, `type`, `toggle`) は実行前にマウス移動を検知する。
ユーザーがマウスを動かすと操作は中断され、exit code 2 + JSON が返る。

**中断を検知したら:**
1. ループを即座に停止する
2. それまでの結果でチケット/報告書を作成する
3. ユーザーに報告する

### 注意事項
- 各ステップでスクリーンショットを保存し、変化を追跡すること
- プロセスの生存確認は `wpf-agent ui alive --pid <pid>` を使う
- **Bash コマンドは必ず1行で記述する**
