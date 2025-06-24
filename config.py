# config.py
# Discord BOT設定

# BOTトークン（Discord Developer Portalから取得）
DISCORD_BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"

# 通知先チャンネルID（Discordで右クリック→IDをコピー）
NOTIFICATION_CHANNEL_ID = None  # ここを実際のチャンネルIDに変更 ""不要

# チェック間隔設定（時間）
CHECK_INTERVAL_HOURS = 6

# アクセス間隔（秒）- robots.txtに配慮して30秒以上推奨
ACCESS_INTERVAL_SECONDS = 30