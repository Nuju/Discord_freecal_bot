# フリカレ監視BOT

フリーカレンダー（フリカレ）のスケジュールを監視し、変更をDiscordに通知するBOTです。

## 🚀 クイックスタート

### 1. 必要な環境

- Python 3.11以上
- Google Chrome（最新版）
- Discord BOTトークン

### 2. インストール

```bash
# リポジトリのクローンまたはファイルをダウンロード
git clone [repository_url]
cd freecal_bot

# 仮想環境の作成（推奨）
python -m venv venv

# 仮想環境の有効化
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 依存ライブラリのインストール
pip install -r requirements.txt
```

### 3. 設定

1. `config.py` を編集
   ```python
   DISCORD_BOT_TOKEN = "あなたのBOTトークン"
   ```

2. または環境変数を使用（推奨）
   ```bash
   cp .env.example .env
   # .env ファイルを編集してトークンを設定
   ```

### 4. BOTの起動

```bash
python bot.py
```

### 5. Discord上での初期設定

1. BOTを起動
2. 通知チャンネルを設定
   ```
   !setchannel #通知チャンネル
   ```
3. 監視ユーザーを追加
   ```
   !adduser 123456 ユーザー名
   ```

## 📝 コマンド一覧

| コマンド | 説明 |
|---------|------|
| `!check` | 監視ユーザー一覧 |
| `!check [名前]` | 今日の予定を確認 |
| `!calendar [名前]` | 今後の全予定を表示 |
| `!status` | 監視状況（管理者のみ） |
| `!adduser` | ユーザー追加（管理者のみ） |
| `!removeuser` | ユーザー削除（管理者のみ） |
| `!setchannel` | 通知チャンネル設定（管理者のみ） |

## 🔧 トラブルシューティング

### BOTが起動しない
- Pythonバージョンを確認: `python --version`
- トークンが正しく設定されているか確認
- 依存ライブラリがインストールされているか確認

### スケジュールが取得できない
- Chromeが最新版か確認
- `screenshots/` フォルダのスクリーンショットを確認
- ユーザーIDが正しいか確認

## 📄 ファイル構成

```
freecal_bot/
├── bot.py              # メインプログラム
├── config.py           # 設定ファイル
├── requirements.txt    # 依存ライブラリ
├── .gitignore         # Git除外設定
├── .env.example       # 環境変数例
├── README.md          # このファイル
├── users.json         # ユーザー情報（自動生成）
├── previous_data.json # 前回データ（自動生成）
├── bot.log           # ログ（自動生成）
└── screenshots/       # デバッグ画像（自動生成）
```

## 🔒 セキュリティ

- `config.py` をGitにコミットしない
- BOTトークンを公開しない
- 定期的にトークンを更新

## 📖 詳細なドキュメント

- [利用ガイド](docs/user_guide.md)
- [管理者ガイド](docs/admin_guide.md)
- [開発ナレッジ](docs/dev_knowledge.md)

## 📞 サポート

問題が発生した場合は、以下を確認してください：
1. `bot.log` のエラーメッセージ
2. `screenshots/` のデバッグ画像
3. ドキュメントのトラブルシューティング

---

Version 7.0.0 - 2025年6月23日