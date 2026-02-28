WPF UI自動化エージェントのセットアップを行います。

手順:
1. パッケージのインストール確認:
```bash
pip install -e .[dev]
```

2. 初期化:
```bash
wpf-agent init
```

3. MCP サーバーの登録:
```bash
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

4. profiles.json にユーザーの対象アプリを設定

5. 動作確認: `list_windows` ツールを呼んでウィンドウ一覧を取得

指示: $ARGUMENTS

ユーザーが対象アプリの情報（プロセス名、ウィンドウタイトル、EXEパス等）を提供した場合は、
profiles.json に適切なプロファイルを追加してください。
