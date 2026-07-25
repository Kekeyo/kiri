<h4 align="right"><a href="./README.md">English</a> | <a href="./README_CN.md">简体中文</a> | <strong><a href="./README_JA.md">日本語</a></strong></h4>

<p>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/kiri-logo.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/kiri-logo.png">
    <img align="right" src="assets/kiri-logo.png" alt="Kiri ロゴ" width="430">
  </picture>
</p>

<br />
<br />

<p align="center">
  <a href="https://github.com/GaoSSR/Kiri">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/kiri-wordmark-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="assets/kiri-wordmark-light.svg">
      <img src="assets/kiri-wordmark-light.svg" alt="Kiri" height="74">
    </picture>
  </a>
</p>

<br clear="right" />

<h3 align="center"><nobr>Rust 製の高性能なローカル開発ポート管理 CLI</nobr></h3>

---

<p align="center">
  <img alt="Rust" src="https://img.shields.io/badge/Rust-CLI-orange" />
  <img alt="MacOS、Linux、Windows 対応" src="https://img.shields.io/badge/MacOS%20%7C%20Linux%20%7C%20Windows-supported-brightgreen" />
  <img alt="コマンド：ports" src="https://img.shields.io/badge/command-ports-8A2BE2" />
  <img alt="ライセンス：Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-blue" />
</p>

## Kiri の概要

Kiri は、Rust 製の高性能なローカル開発ポート管理 CLI です。どのローカルサービスが動作しているか、どのポートを使用しているかをすばやく確認し、必要に応じてポートに紐づくプロセスを操作できます。

`ports` を実行すると、ポート、プロセス、PID、メモリ使用量、プロジェクト名、検出されたフレームワーク、稼働時間、ヘルス状態に絞ったローカル開発サービスの概要が表示されます。

<p align="center">
  <img src="assets/readme/ports-overview.png" alt="Kiri のポート概要画面" width="880">
</p>

`ports logs <port|pid> -f` を実行すると、該当するプロセスのログを追跡できます。Kiri は、タイムスタンプ、ログレベル、プロセス ID、トレース ID、ソースクラス、HTTP 値、構造化フィールドを ANSI カラーで表示し、大量のフレームワークログも読みやすくします。

<p align="center">
  <img src="assets/readme/logs-follow.png" alt="Kiri のカラーログ追跡画面" width="880">
</p>

## Kiri の紹介

デフォルトの `ports` ターミナル表示では、ポート一覧の前にかわいらしい Kiri の ASCII ロゴが表示されます。

```text
      .-~~~~-.
   .-(  ●  ● )-.
  (  •   ⌣   •  )  Kiri is watching 5 ports, 5 ports active
   '-.        .-'
      '------'
```

## 基本的な使い方

- **ローカル開発サービスと使用ポートを表示：** `ports`
- **開発用バックグラウンドプロセスを表示：** `ports ps` は、Codex、Claude Code、その他の AI コーディングツールが起動した MCP Server プロセスなど、ポートをリッスンしていない場合がある開発関連プロセスを表示します。ポート一覧にないプロセスのメモリ使用量を確認したり、長時間動作しているツールプロセスを探したりする場合に使用します。
- **ポートに紐づくプロセスまたは PID をすばやく終了：** `ports kill <port>`
- **ポートをリッスンしているプロセスのログを追跡：** `ports logs <port|pid> -f`
- **すべてのポートを表示：** `ports --all`

## インストール

Kiri は、MacOS、Linux x64、Windows x64 向けのビルド済みリリース成果物を提供しています。npm、Homebrew、または GitHub Release のインストールスクリプトでインストールできます。

```bash
# npm
npm install -g @gaossr/kiri

# MacOS では Homebrew を推奨
brew install gaossr/tap/kiri

# MacOS / Linux インストールスクリプト
curl -fsSL https://raw.githubusercontent.com/GaoSSR/Kiri/main/scripts/install.sh | bash
```

Windows ユーザーは PowerShell でインストールできます。

```powershell
irm https://raw.githubusercontent.com/GaoSSR/Kiri/main/scripts/install.ps1 | iex
```

MacOS では Homebrew が推奨のインストール方法です。npm とインストールスクリプトはビルド済みのネイティブバイナリを使用するため、ローカルで Rust をコンパイルしません。

## コマンド

```bash
ports                       # ローカル開発サービスと使用ポートを表示
ports --all                 # リッスン中のすべてのポートを表示
ports <port>                # 1つのポートの詳細を表示
ports ps                    # ポートをリッスンしていない MCP Server プロセスを含む、開発用バックグラウンドプロセスを表示
ports ps --all              # すべてのプロセスを表示
ports logs <port|pid>          # 最近のログを表示して終了
ports logs <port|pid> -f       # ポートをリッスンしているプロセスのログを追跡
ports logs 3000 --lines 10     # 直近10行を表示して終了
ports logs 3000 -f --lines 10  # 直近10行を表示して追跡を継続
ports logs 3000 --err          # stderr のみ
ports clean                 # 孤児・ゾンビ開発プロセスを削除する前に確認
ports watch                 # ポートの開始・停止イベントをストリーミング
ports kill 3000             # ポートに紐づくプロセス / PID をすばやく終了
ports kill 3000-3010        # 範囲内のリスナーを終了
ports kill --force 3000     # SIGTERM ではなく SIGKILL を使用
```

## ステータスラベル

Kiri は `ports` の表で次のステータスラベルを使用します。

- `healthy`：プロセスが実行中で、正常な親プロセスが存在します。
- `orphaned`：プロセスはまだ動作しており、ポートをリッスンしている可能性もありますが、そのプロセスを起動した親プロセスはすでに終了しています。これは孤児プロセスであり、ゾンビプロセスではありません。
- `zombie`：プロセス自体はすでに終了していますが、親プロセスに回収されていないプロセスレコードがオペレーティングシステムに残っています。

実際には、`orphaned` は「プロセスはまだ動いているものの、元のランチャーはすでに存在しない」という意味です。ターミナル、IDE タスク、スクリプトランナー、Codex セッション、Claude Code セッションを閉じた後も、そこで起動した子サーバープロセスが動作し続けると発生する場合があります。

## プラットフォーム対応

| プラットフォーム | ステータス |
| --- | --- |
| MacOS arm64/x64 | 対応済み |
| Linux x64 | 対応済み |
| Windows x64 | 対応済み |
| Linux arm64 / Windows arm64 | 対応予定 |

MacOS では、Kiri は `lsof`、`ps`、`tail`、MacOS の `log` コマンドを使用し、利用可能な場合は Docker メタデータも使用します。Linux では `ss`、`ps`、`/proc` を使用し、利用可能な場合は Docker メタデータも使用します。Windows では PowerShell/CIM と `Get-NetTCPConnection` を使用し、プロセスの作業ディレクトリは実行可能ファイルのパスから可能な範囲で推定されます。Docker の利用は任意です。Docker を利用できない場合や実行中のコンテナがない場合でも、Kiri は Docker のマッピングなしで動作を続けます。

`ports` は、デフォルトで Kiri の ASCII ロゴと ANSI ターミナル出力を意図的に表示します。`ports logs` は、Java、Python、Go、Node.js、logfmt、JSON などの一般的な開発ログ形式に ANSI カラーを追加します。ターミナルから起動したサービスでは、`.dev-logs/service.log` のような安定したファイルベースのログを使用することで、別のプロセスから `ports logs <port|pid> -f` で出力を追跡できます。

デフォルトの `ports` 表は引き続き開発用ポートに絞り、`Mem` も表示するため、日常的な確認でより広範な `ports ps` を使う必要はありません。

## 開発

ソースから作業するメンテナーおよびコントリビューター向けのコマンドは次のとおりです。

```bash
cargo fmt
cargo test
cargo clippy --all-targets -- -D warnings
cargo build --release --bin ports
scripts/perf-smoke.sh
scripts/verify-release.sh v0.1.22
cargo run --bin ports
cargo run --bin ports -- --all
cargo run --bin ports -- ps
```

## プロジェクト資料

- [変更履歴](./CHANGELOG.md)
- [コントリビューションガイド](./CONTRIBUTING.md)
- [セキュリティポリシー](./SECURITY.md)

## 謝辞

Kiri は [port-whisperer](https://github.com/LarsenCundric/port-whisperer) から着想を得ています。特に、ローカル開発ポートを見つけやすく、理解しやすく、整理しやすくするという考え方に影響を受けています。
