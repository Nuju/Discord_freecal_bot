# フリカレ監視BOT 開発ナレッジ・引き継ぎドキュメント v4.0

## 📋 プロジェクト概要

### バージョン情報
- **Version**: 7.0.0 (修正版)
- **完成日**: 2025年6月23日
- **作者**: Charo (with AI review)
- **主要変更**: ID形式対応、コマンド体系の整理

### 技術スタック
```
- Python 3.11+
- Discord.py 2.3+
- Selenium 4.0+ with ChromeDriver
- BeautifulSoup4 + lxml
- webdriver-manager (ChromeDriver自動管理)
```

---

## 🏗️ アーキテクチャ詳細（v7.0.0）

### クラス構成

```python
FreecalendScraper              # v7.0.0 - ID形式修正版
├── initialize()               # 非同期初期化
├── get_schedule()             # today_only パラメータ追加
├── _parse_final()             # ccexp ID形式対応
└── save_debug_screenshot()    # デバッグ機能

DataManager                    # データ永続化
├── monitored_users           # users.json管理
├── previous_hashes           # 変更検知用
└── add_user/remove_user      # 動的ユーザー管理

CalendarMonitor (Cog)         # Discord機能
├── schedule_check            # 定期監視（全予定）
├── check_today              # !check（今日のみ）
├── show_calendar            # !calendar（全予定）
└── _send_notification       # 通知フォーマット
```

---

## 🎯 v7.0.0の技術的決定事項

### 1. フリカレID形式への完全対応

**発見したID形式:**
```html
<!-- 実際のフリカレDOM -->
<div class="ccexp ccexp_list doteki_usersel" id="ccexp-230522-2025-6-23">
    21:00 観戦&nbsp;
</div>
```

**対応実装:**
```python
# ID形式の判定と日付抽出
if len(parts) >= 5 and parts[1] == user_id:
    # 形式: ccexp-[ユーザーID]-[年]-[月]-[日]
    year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
elif len(parts) >= 5:
    # 形式: ccexp-[年]-[月]-[日]-[連番]（レガシー対応）
    year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
```

### 2. コマンド体系の再設計

**設計思想:**
- ユーザーの利用シーンに合わせた最適化
- 直感的なアイコン使用

**実装:**
```python
# !check - 今日の予定（朝の確認用）
async def check_today(self, ctx, *, target: str = None):
    schedule_data = await self.scraper.get_schedule(user_id, username, today_only=True)
    embed.title = f"🔥 {username}の【今日の予定】"

# !calendar - 全予定（週次・月次計画用）
async def show_calendar(self, ctx, *, target: str = None):
    schedule_data = await self.scraper.get_schedule(user_id, username, today_only=False)
    embed.title = f"⏰ {username}の【今後の全予定】"
```

### 3. 表示フォーマットの統一

**embedフィールド構成:**
```python
# 共通フッター（3つのインラインフィールド）
embed.add_field(name="👤 ユーザー", value=f"`{user_id}`", inline=True)
embed.add_field(name="🕐 確認時刻", value=datetime.now().strftime("%H:%M"), inline=True)
embed.add_field(name="🔗 URL", value=f"[フリカレを開く](url)", inline=True)
```

**削除された要素:**
- `timestamp=datetime.now()` → 確認時刻フィールドで代替
- 「今後の全予定を確認」フィールド → シンプル化のため削除

---

## 🔧 実装の詳細と工夫

### today_only フィルタリング

```python
def _parse_final(self, html: str, user_id: str, today_only: bool = False) -> List[str]:
    # 今日の日付
    today = datetime.now().date()
    
    for div in schedule_divs:
        # ... 日付解析 ...
        
        # 過去の予定はスキップ
        if event_date < today:
            continue
        
        # 今日のみモードで今日以外はスキップ
        if today_only and event_date != today:
            continue
```

**メリット:**
- 単一のメソッドで両方のモードに対応
- 重複コードの削減
- 保守性の向上

### エラーハンドリングの強化

```python
try:
    div_id = div.get('id', '')
    parts = div_id.split('-')
    # ID形式判定...
except (IndexError, ValueError) as e:
    logger.debug(f"日付解析スキップ: {div_id} - {e}")
    continue
```

**ポイント:**
- 個別要素のエラーが全体に影響しない
- デバッグ情報の適切なログ出力
- 柔軟なID形式対応

### スクリーンショット機能

```python
def save_debug_screenshot(self, name_prefix: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(SCREENSHOTS_DIR, f"debug_{name_prefix}_{timestamp}.png")
```

**命名規則:**
- `debug_[ユーザー名]_[タイムスタンプ].png`: 通常
- `debug_[ユーザー名]_access_failed_[タイムスタンプ].png`: アクセス失敗
- `debug_[ユーザー名]_critical_error_[タイムスタンプ].png`: 重大エラー

---

## 📊 技術的な制約と対策

### フリカレのDOM構造依存

**リスク:**
- ccexp要素のID形式変更
- クラス名の変更
- HTML構造の大幅な変更

**対策:**
1. **柔軟なID形式対応**
   ```python
   # 複数のID形式をサポート
   if len(parts) >= 5 and parts[1] == user_id:
       # 新形式
   elif len(parts) >= 5:
       # レガシー形式
   ```

2. **スクリーンショットによる早期発見**
   - エラー時の自動保存
   - 定期的な手動確認推奨

3. **詳細なログ出力**
   ```python
   logger.info(f"スケジュールデータコンテナ 'ccexp' を {len(schedule_divs)}件 発見しました。")
   ```

### パフォーマンス考慮

**ボトルネック:**
- Selenium起動時間: 約2-3秒
- ページ読み込み: 約3-5秒/ユーザー
- 解析処理: 約0.1秒

**最適化:**
```python
# ドライバーの再利用
if self.is_initialized: 
    return True

# 適切な待機時間
WebDriverWait(self.driver, 20)  # 最大20秒
time.sleep(3)  # JavaScript完全実行待機
```

---

## 🚀 今後の拡張可能性

### 短期的改善（1-3ヶ月）

**1. 期間指定機能**
```python
async def get_schedule_range(self, user_id: str, start_date: date, end_date: date):
    """特定期間の予定を取得"""
    # start_date <= event_date <= end_date でフィルタリング
```

**2. 予定の分類機能**
```python
class EventCategory(Enum):
    MEETING = "会議"
    DEADLINE = "締切"
    EVENT = "イベント"
    OTHER = "その他"
```

**3. 通知カスタマイズ**
```python
# ユーザーごとの通知設定
notification_preferences = {
    "user_id": {
        "notify_changes": True,
        "notify_today": True,
        "notify_time": "08:00"
    }
}
```

### 中期的拡張（3-6ヶ月）

**1. データベース導入**
```python
# SQLiteによる履歴管理
CREATE TABLE schedule_history (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    event_date DATE,
    event_time TEXT,
    event_title TEXT,
    captured_at TIMESTAMP,
    hash TEXT
);
```

**2. 差分表示機能**
```python
def get_schedule_diff(old_schedule: str, new_schedule: str) -> Dict:
    """追加・削除・変更された予定を抽出"""
    return {
        "added": [...],
        "removed": [...],
        "modified": [...]
    }
```

**3. API化**
```python
# FastAPIによるREST API
@app.get("/api/schedule/{user_id}")
async def get_user_schedule(user_id: str, today_only: bool = False):
    return await scraper.get_schedule(user_id, username, today_only)
```

### 長期的展望（6ヶ月以上）

**1. マルチカレンダー対応**
- Google Calendar
- Outlook
- iCal形式

**2. AI機能統合**
- 予定の自動カテゴライズ
- 空き時間の提案
- 会議時間の最適化

**3. 高度な通知システム**
- プッシュ通知
- メール通知
- Webhook対応

---

## 🎯 引き継ぎ時の重要ポイント

### 必須理解事項

**1. ccexp要素のID形式**
```python
# 現在確認されている形式
"ccexp-[ユーザーID]-[年]-[月]-[日]"

# 例: ccexp-230522-2025-6-23
```

**2. コマンドの使い分け**
- `!check`: 今日の予定のみ（🔥）
- `!calendar`: 全予定（⏰）

**3. フィルタリングロジック**
```python
# 今日のみモードの実装
if today_only and event_date != today:
    continue
```

### デバッグのポイント

**1. ログの確認順序**
1. スクレイパー初期化
2. ページアクセス
3. ccexp要素の発見数
4. 解析結果

**2. スクリーンショットの活用**
- エラー時は必ず確認
- DOM構造の変更を視覚的に把握

**3. ID形式の確認**
```python
logger.debug(f"日付解析スキップ: {div_id} - {e}")
```

### コード品質の維持

**1. 命名規則**
- メソッド名: snake_case
- クラス名: PascalCase
- 定数: UPPER_SNAKE_CASE

**2. ドキュメント**
- docstringの記載
- 重要な処理にコメント
- バージョン情報の更新

**3. エラーハンドリング**
- 適切な例外の使用
- ログレベルの使い分け
- ユーザーフレンドリーなメッセージ

---

## 📚 参考資料

### 技術ドキュメント
- [Discord.py](https://discordpy.readthedocs.io/)
- [Selenium Python](https://selenium-python.readthedocs.io/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

### フリカレ仕様
- URL形式: `https://freecalend.com/open/mem{user_id}/`
- robots.txt: アクセス間隔30秒以上
- ID形式: `ccexp-[ユーザーID]-[年]-[月]-[日]`

### Discord設計
- Cog ベースアーキテクチャ
- 非同期処理の活用
- embed による見やすい表示

---

## 🎖️ プロジェクトの成果

### 達成事項（v7.0.0）

✅ **フリカレID形式への完全対応**  
✅ **直感的なコマンド体系**（🔥今日、⏰全予定）  
✅ **安定したスケジュール取得**  
✅ **詳細なデバッグ機能**  
✅ **永続的なユーザー管理**  
✅ **見やすい表示フォーマット**  

### 技術的な学び

1. **動的サイトのスクレイピング**
   - DOM構造の変化への対応
   - 複数のID形式サポート
   - エラー時の適切な処理

2. **ユーザビリティの重要性**
   - 用途に応じたコマンド設計
   - 直感的なアイコン使用
   - 必要十分な情報表示

3. **保守性の確保**
   - 柔軟なコード設計
   - 詳細なログ出力
   - デバッグ機能の充実

---

## 🔄 バージョン履歴

### v7.0.0 (2025-06-23)
- フリカレID形式対応
- コマンド体系変更（!check/!calendar）
- 表示フォーマット改善

### v6.0.0
- 全面リファクタリング
- 型安全性の向上

### v5.0.0
- ccexp要素の発見
- users.json分離

### v4.0.0
- 初期実装

---

*フリカレ監視BOT 開発ナレッジ v4.0 - 2025年6月23日*  
*Version 7.0.0 対応*