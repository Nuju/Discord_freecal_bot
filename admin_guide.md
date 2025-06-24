# フリカレ監視BOT 管理者ガイド v5.0

## 📋 目次

1. [管理者の役割](#管理者の役割)
2. [BOTのセットアップ](#botのセットアップ)
3. [BOTの起動と停止](#botの起動と停止)
4. [ユーザー管理](#ユーザー管理)
5. [監視機能の管理](#監視機能の管理)
6. [トラブルシューティング](#トラブルシューティング)
7. [メンテナンス](#メンテナンス)
8. [ログとデバッグ](#ログとデバッグ)
9. [セキュリティ](#セキュリティ)

---

## 🎯 管理者の役割

BOT管理者として、以下の業務を担当します：

- BOTの初期設定と起動管理
- 監視ユーザーの追加・削除（users.json管理）
- 通知チャンネルの設定
- デバッグ用スクリーンショットの確認
- トラブルシューティング
- 定期メンテナンス
- セキュリティ管理

---

## 🚀 BOTのセットアップ

### 前提条件

- Python 3.11以上
- Google Chrome 最新版
- Discord BOTトークン
- 管理者権限を持つDiscordアカウント

### 初期セットアップ手順

#### 1. ファイル構造（v7.0.0）

```
freecal_bot/
├── bot.py              # メインプログラム
├── config.py           # 設定ファイル（要作成）
├── requirements.txt    # 依存ライブラリ
├── users.json          # 監視ユーザーリスト（自動生成）
├── previous_data.json  # 前回チェック結果（自動生成）
├── bot.log            # ログファイル（自動生成）
└── screenshots/        # デバッグ用スクリーンショット（自動生成）
```

#### 2. config.py の作成

```python
# Discord BOT設定
DISCORD_BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"

# 通知チャンネルID（コマンドで設定可能）
NOTIFICATION_CHANNEL_ID = None

# 監視間隔（時間）
CHECK_INTERVAL_HOURS = 6

# アクセス間隔（秒） - robots.txt準拠
ACCESS_INTERVAL_SECONDS = 30
```

**重要**: 
- `MONITORED_USERS`は廃止されました
- ユーザー管理は`users.json`で行います
- BOT稼働中でもユーザーの追加・削除が可能

#### 3. Discord Developer Portal の設定

1. https://discord.com/developers/applications/ にアクセス
2. あなたのBOTアプリケーションを選択
3. 左側メニューから「Bot」を選択
4. 「Privileged Gateway Intents」セクションで以下を有効化：
   - ✅ **MESSAGE CONTENT INTENT** （必須）

5. 「OAuth2」→「URL Generator」で以下の権限を選択：
   - **Scopes**: bot
   - **Bot Permissions**:
     - Send Messages
     - Embed Links
     - Attach Files
     - Read Message History
     - Use Slash Commands

#### 4. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

**requirements.txt の内容:**
```
discord.py>=2.3.0
selenium>=4.0.0
webdriver-manager>=4.0.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
```

---

## 🖥️ BOTの起動と停止

### 起動方法

```bash
python bot.py
```

### 正常起動の確認

以下のようなログが表示されれば成功：

```
2025-06-23 12:00:00 - INFO - フリカレスクレイパーを初期化しました (v7.0.0)
2025-06-23 12:00:01 - INFO - 🤖 フリカレ監視BOT#1234 としてログインしました
2025-06-23 12:00:01 - INFO - ⚙️ CalendarMonitor Cogをロードしました。監視を開始します。
```

### 停止方法

- **通常停止**: `Ctrl + C`
- **データ保存**: 停止時に自動的に以下が保存されます
  - `users.json`: ユーザー情報
  - `previous_data.json`: 前回チェック結果

### バックグラウンド実行

#### Linux/Mac (systemd)

```ini
# /etc/systemd/system/freecal-bot.service
[Unit]
Description=Freecal Monitor Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/freecal_bot
ExecStart=/path/to/python /path/to/freecal_bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Windows (タスクスケジューラ)

1. タスクスケジューラーを開く
2. 「基本タスクの作成」を選択
3. トリガー: システム起動時
4. 操作: プログラムの開始
5. プログラム: `python.exe`
6. 引数: `C:\path\to\freecal_bot\bot.py`
7. 開始オプション: `C:\path\to\freecal_bot`

---

## 👥 ユーザー管理（v7.0.0）

### 監視ユーザーの追加

```
!adduser [ユーザーID] [表示名]
```

**例:**
```
!adduser 123456 山田太郎さん
```

**特徴:**
- `users.json`に永続的に保存
- BOT再起動不要
- 即座に監視開始

### 監視ユーザーの削除

```
!removeuser [ユーザーIDまたは名前]
```

**例:**
```
!removeuser 山田
!removeuser 123456
```

**検索方法:**
- ID完全一致
- 名前部分一致（大文字小文字無視）

### ユーザー管理ファイル

**users.json の構造:**
```json
{
    "234567": "ユーザーA",
    "123456": "山田太郎さん",
    "789012": "鈴木花子さん"
}
```

### フリカレユーザーIDの確認方法

1. フリカレページURL: `https://freecalend.com/open/mem[数字]/`
2. `mem`の後の数字がユーザーID

**例**: 
- URL: `https://freecalend.com/open/mem123456/`
- ユーザーID: `123456`

### ユーザー一覧の確認

```
!check
```

現在の監視対象ユーザーをすべて表示します。

---

## 🔔 監視機能の管理

### 通知チャンネルの設定

```
!setchannel [#チャンネル名]
```

**現在のチャンネルに設定:**
```
!setchannel
```

**特定のチャンネルに設定:**
```
!setchannel #通知チャンネル
```

### 監視状況確認

```
!status
```

**表示内容:**
- 定期監視の状態（実行中/停止中）
- 次回実行時刻
- 監視ユーザー数
- 通知チャンネル

**表示例:**
```
📊 監視ステータス

定期監視: 🟢 実行中
次回実行: 3時間後
監視ユーザー数: 3人
通知チャンネル: #freecal-notifications
```

### 定期監視の仕組み

```python
# 監視フロー
1. CHECK_INTERVAL_HOURS ごとに起動（デフォルト6時間）
2. 各ユーザーを順次チェック
   - スケジュール取得（全予定）
   - 前回データとの比較
   - 変更があれば通知
3. ACCESS_INTERVAL_SECONDS 待機（30秒）
4. 次のユーザーへ
```

---

## 🛠️ トラブルシューティング

### デバッグ機能（v7.0.0）

#### スクリーンショット自動保存

**保存場所**: `screenshots/`ディレクトリ

**ファイル名パターン:**
- `debug_[ユーザー名]_[タイムスタンプ].png`: 正常取得時
- `debug_[ユーザー名]_access_failed_[タイムスタンプ].png`: アクセス失敗
- `debug_[ユーザー名]_critical_error_[タイムスタンプ].png`: 重大エラー時

**活用方法:**
1. エラー発生時刻を確認
2. 該当時刻のスクリーンショットを確認
3. フリカレのUI変更やエラーメッセージを確認

### よくある問題と解決法

#### 1. BOTが起動しない

**エラー**: `discord.LoginFailure`
```
解決法:
1. config.py の DISCORD_BOT_TOKEN を確認
2. トークンの前後の空白を削除
3. Developer Portal で新しいトークンを生成
```

**エラー**: `ModuleNotFoundError`
```
解決法:
pip install -r requirements.txt
```

#### 2. スケジュール取得エラー

**症状**: 「スケジュール取得に失敗しました」

**確認手順:**
1. `bot.log`でエラー詳細を確認
2. `screenshots/`で画面を確認
3. フリカレに手動アクセスして確認

**よくある原因:**
- フリカレメンテナンス中
- ユーザーIDの誤り
- ネットワークエラー
- フリカレのDOM構造変更

#### 3. ChromeDriver関連

**エラー**: `SessionNotCreatedException`
```
解決法:
# ChromeDriverを最新に更新
pip install --upgrade webdriver-manager

# Chromeブラウザも最新に更新
```

#### 4. ccexp要素が見つからない

**ログメッセージ**:
```
最終解析エラー: スケジュールデータコンテナ 'ccexp' が見つかりませんでした。
```

**対処法:**
1. スクリーンショットを確認
2. フリカレのHTML構造を手動で確認
3. ID形式の変更を確認（ccexp-[ユーザーID]-[年]-[月]-[日]）

### エラーログの読み方

```
2025-06-23 12:00:00 - ERROR - スケジュール取得の包括的なエラー (ユーザーA): 
Traceback (most recent call last):
  File "bot.py", line 123, in get_schedule
    ...
```

**確認ポイント:**
1. エラー発生時刻
2. エラー発生ユーザー
3. エラーの種類
4. スタックトレース

---

## 📊 メンテナンス

### 定期メンテナンス項目

#### 日次
- [ ] BOT稼働確認（`!status`）
- [ ] エラーログ確認（`bot.log`）
- [ ] ディスク容量確認

#### 週次
- [ ] スクリーンショット整理
- [ ] ログファイルサイズ確認
- [ ] `users.json`バックアップ

#### 月次
- [ ] 依存ライブラリ更新
- [ ] Chrome/ChromeDriver互換性確認
- [ ] パフォーマンス分析

### バックアップ

**重要ファイル:**
```bash
# バックアップスクリプト例
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/freecal_bot"

mkdir -p $BACKUP_DIR/$DATE
cp config.py $BACKUP_DIR/$DATE/
cp users.json $BACKUP_DIR/$DATE/
cp previous_data.json $BACKUP_DIR/$DATE/
```

### スクリーンショット管理

```bash
# 30日以上前のスクリーンショットを削除
find screenshots/ -name "*.png" -mtime +30 -delete

# ディスク使用量確認
du -sh screenshots/
```

### ログローテーション

```python
# logrotate設定例 (/etc/logrotate.d/freecal-bot)
/path/to/freecal_bot/bot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## 📝 ログとデバッグ

### ログレベル

| レベル | 用途 | 例 |
|--------|------|-----|
| INFO | 通常動作 | BOT起動、スケジュール取得成功 |
| WARNING | 注意事項 | 空のスケジュール、リトライ |
| ERROR | エラー | 取得失敗、例外発生 |
| DEBUG | 詳細情報 | 日付解析スキップ |

### 重要なログメッセージ（v7.0.0）

| メッセージ | 意味 | 対処 |
|-----------|------|------|
| `フリカレスクレイパーを初期化しました (v7.0.0)` | 正常起動 | - |
| `スケジュールデータコンテナ 'ccexp' を N件 発見しました` | 解析成功 | - |
| `最終解析エラー: スケジュールデータコンテナ 'ccexp' が見つかりませんでした` | 解析失敗 | スクリーンショット確認 |
| `今日のみ: True/False` | 取得モード表示 | - |

### デバッグ手順

1. **エラー特定**
   ```bash
   grep ERROR bot.log | tail -20
   ```

2. **該当時刻の確認**
   ```bash
   grep "2025-06-23 14:" bot.log
   ```

3. **スクリーンショット確認**
   ```bash
   ls -la screenshots/*ユーザーA*
   ```

4. **手動実行テスト**
   ```python
   # デバッグモードで実行
   python -u bot.py
   ```

---

## 🔒 セキュリティ

### セキュリティベストプラクティス

#### 1. トークン管理

```python
# 環境変数を使用（推奨）
import os
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
```

**.env ファイル:**
```
DISCORD_BOT_TOKEN=your_token_here
```

#### 2. ファイルアクセス権限

```bash
# 重要ファイルの権限設定
chmod 600 config.py
chmod 644 users.json
chmod 755 screenshots/
```

#### 3. .gitignore設定

```
# .gitignore
config.py
users.json
previous_data.json
bot.log
screenshots/
*.pyc
__pycache__/
venv/
.env
```

### プライバシー保護

1. **スクリーンショット管理**
   - 個人情報を含む可能性
   - 定期的な削除
   - アクセス制限

2. **ログ管理**
   - 個人名のマスキング検討
   - 適切なローテーション
   - セキュアな保存

3. **アクセス制御**
   - 管理者コマンドの権限チェック
   - 監視対象の適切な管理
   - 通知チャンネルの限定

### セキュリティ監査

**定期チェック項目:**
- [ ] 不正なアクセス試行
- [ ] 異常なリソース使用
- [ ] 権限設定の確認
- [ ] 依存ライブラリの脆弱性

```bash
# 脆弱性チェック
pip install safety
safety check
```

---

## 📞 トラブル時の対応

### エスカレーションフロー

1. **Level 1**: ログ確認で自己解決
2. **Level 2**: スクリーンショット確認
3. **Level 3**: 手動実行でデバッグ
4. **Level 4**: 開発者に相談

### 緊急時の対応

```bash
# BOTの強制停止
ps aux | grep bot.py
kill -9 [PID]

# データバックアップ
tar -czf backup_$(date +%Y%m%d).tar.gz *.json

# 最小構成での再起動
python bot.py
```

---

## 📋 管理者チェックリスト

### 初期導入時
- [ ] Python 3.11+ インストール
- [ ] Chrome 最新版インストール
- [ ] requirements.txt でライブラリインストール
- [ ] config.py 作成・設定
- [ ] Discord Developer Portal 設定
- [ ] BOT をサーバーに招待
- [ ] 権限設定確認
- [ ] 初回起動テスト
- [ ] 監視ユーザー追加
- [ ] 通知チャンネル設定

### 日常運用
- [ ] 毎日：稼働確認（`!status`）
- [ ] 毎日：エラーログ確認
- [ ] 毎週：スクリーンショット整理
- [ ] 毎週：バックアップ実行
- [ ] 毎月：ライブラリ更新確認
- [ ] 毎月：パフォーマンス評価

### トラブル対応
- [ ] エラーログ確認
- [ ] スクリーンショット確認
- [ ] 手動実行テスト
- [ ] 必要に応じて再起動
- [ ] 解決策の文書化

---

## 🆕 v7.0.0 の主な変更点

1. **コマンド体系の変更**
   - `!check`: 今日の予定のみ（🔥アイコン）
   - `!calendar`: 全予定（⏰アイコン）

2. **ID形式への対応**
   - ccexp-[ユーザーID]-[年]-[月]-[日] 形式をサポート

3. **表示の改善**
   - 詳細なフッター情報（ユーザーID、確認時刻、URL）
   - タイムスタンプ表示の削除

---

*フリカレ監視BOT 管理者ガイド v5.0 - 2025年6月23日*