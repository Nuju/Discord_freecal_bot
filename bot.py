"""
フリカレ監視BOT - 修正版
Version: 7.0.0
Author: Charo (with AI review)
Date: 2025-06-23

機能:
- !check: 今日の予定のみを表示
- !calendar: 今後の全予定を表示
- 自動監視と変更通知
- デバッグ用スクリーンショット保存
"""

import discord
from discord.ext import commands, tasks
import asyncio
import json
import logging
import hashlib
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import re

# Selenium関連
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# 設定ファイルをインポート
import config

# --- ログ設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- グローバル設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
PREVIOUS_DATA_FILE = os.path.join(BASE_DIR, "previous_data.json")
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")


class FreecalendScraper:
    """フリカレのスケジュール取得専用クラス (v7.0.0 - ID形式修正版)"""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.is_initialized = False
        if not os.path.exists(SCREENSHOTS_DIR):
            os.makedirs(SCREENSHOTS_DIR)

    async def initialize(self) -> bool:
        if self.is_initialized: 
            return True
        try:
            loop = asyncio.get_event_loop()
            self.driver = await loop.run_in_executor(None, self._create_driver)
            self.is_initialized = True
            logger.info("フリカレスクレイパーを初期化しました (v7.0.0)")
            return True
        except Exception as e:
            logger.error(f"スクレイパー初期化エラー: {e}", exc_info=True)
            return False

    def _create_driver(self) -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1200')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
        
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver

    async def get_schedule(self, user_id: str, username: str, today_only: bool = False) -> Optional[str]:
        if not await self.initialize(): 
            return None

        url = f"https://freecalend.com/open/mem{user_id}/"
        logger.info(f"フリカレアクセス開始: {username} ({user_id}) - 今日のみ: {today_only}")
        
        try:
            html = await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_page_and_get_html, url, username
            )
            
            if not html:
                logger.error(f"ページのHTML取得に失敗しました: {username}")
                return ""

            schedule_list = self._parse_final(html, user_id, today_only)
            
            if not schedule_list:
                logger.warning(f"{username} のスケジュール解析結果が空です。")
            
            sorted_events = self.sort_events(schedule_list)
            return "\n".join(sorted_events)

        except Exception as e:
            logger.error(f"スケジュール取得の包括的なエラー ({username}): {e}", exc_info=True)
            self.save_debug_screenshot(f"{username}_critical_error")
            return ""

    def _fetch_page_and_get_html(self, url: str, username: str) -> Optional[str]:
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            page_html = self.driver.page_source
            self.save_debug_screenshot(username)
            return page_html
        except Exception as e:
            logger.error(f"ページへのアクセス自体に失敗しました: {e}", exc_info=True)
            self.save_debug_screenshot(f"{username}_access_failed")
            return None

    def _parse_final(self, html: str, user_id: str, today_only: bool = False) -> List[str]:
        """フリカレの隠されたデータ構造 `ccexp` を直接読み取る（ID形式修正版）"""
        soup = BeautifulSoup(html, 'lxml')
        page_title = soup.find('title').get_text(strip=True) if soup.find('title') else "タイトル不明"
        logger.info(f"最終解析開始 - ページタイトル: '{page_title}'")

        # ID形式: ccexp-[ユーザーID]-[年]-[月]-[日] または ccexp-[年]-[月]-[日]-[連番]
        schedule_divs = soup.select('div[id^="ccexp-"]')
        if not schedule_divs:
            logger.error("最終解析エラー: スケジュールデータコンテナ 'ccexp' が見つかりませんでした。")
            return []

        logger.info(f"スケジュールデータコンテナ 'ccexp' を {len(schedule_divs)}件 発見しました。")
        
        # 今日の日付
        today = datetime.now().date()
        
        events = []
        for div in schedule_divs:
            try:
                div_id = div.get('id', '')
                parts = div_id.split('-')
                
                # ID形式の判定と日付抽出
                if len(parts) >= 5 and parts[1] == user_id:
                    # 形式: ccexp-[ユーザーID]-[年]-[月]-[日]
                    year, month, day = int(parts[2]), int(parts[3]), int(parts[4])
                elif len(parts) >= 5:
                    # 形式: ccexp-[年]-[月]-[日]-[連番]
                    year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
                else:
                    continue
                
                event_date = datetime(year, month, day).date()
                
                # 過去の予定はスキップ
                if event_date < today:
                    continue
                
                # 今日のみモードで今日以外はスキップ
                if today_only and event_date != today:
                    continue
                    
            except (IndexError, ValueError) as e:
                logger.debug(f"日付解析スキップ: {div_id} - {e}")
                continue

            text_content = div.get_text(separator=" ", strip=True)
            if not text_content:
                continue
                
            # 時刻と内容を分離
            time_match = re.match(r'(\d{1,2}:\d{2})\s*(.+)', text_content)
            if time_match:
                time_str, event_str = time_match.group(1), time_match.group(2)
            else:
                time_str, event_str = "終日", text_content

            if not event_str: 
                continue
                
            events.append(f"🔹 {month:02d}/{day:02d} {time_str} - {event_str}")
            
        return events

    def sort_events(self, events: List[str]) -> List[str]:
        def get_sort_key(event_line: str):
            match = re.search(r'(\d{2})/(\d{2})', event_line)
            if match: 
                return f"{match.group(1)}{match.group(2)}"
            return "9999"
        return sorted(events, key=get_sort_key)

    def save_debug_screenshot(self, name_prefix: str):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(SCREENSHOTS_DIR, f"debug_{name_prefix}_{timestamp}.png")
            self.driver.save_screenshot(filename)
            logger.info(f"スクリーンショットを保存しました: {filename}")
        except Exception as e:
            logger.error(f"スクリーンショットの保存に失敗: {e}")

    def cleanup(self):
        if self.driver: 
            self.driver.quit()
        self.is_initialized = False


class DataManager:
    def __init__(self, data_file, users_file):
        self.data_file = data_file
        self.users_file = users_file
        self.previous_hashes: Dict[str, str] = self._load_json(self.data_file)
        self.monitored_users: Dict[str, str] = self._load_json(self.users_file)

    def _load_json(self, file_path: str) -> Dict:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f: 
                    return json.load(f)
        except (json.JSONDecodeError, IOError): 
            pass
        return {}

    def _save_json(self, file_path: str, data: Dict):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            logger.error(f"{file_path} への書き込みエラー: {e}")

    def save_all_data(self):
        self._save_json(self.data_file, self.previous_hashes)
        self._save_json(self.users_file, self.monitored_users)

    def has_changed(self, user_id: str, current_data: str) -> bool:
        current_hash = hashlib.md5(current_data.encode('utf-8')).hexdigest()
        if self.previous_hashes.get(user_id) != current_hash:
            self.previous_hashes[user_id] = current_hash
            return True
        return False

    def add_user(self, user_id: str, username: str):
        self.monitored_users[user_id] = username
        self._save_json(self.users_file, self.monitored_users)

    def remove_user(self, user_id: str) -> Optional[str]:
        if user_id in self.monitored_users:
            username = self.monitored_users.pop(user_id)
            self._save_json(self.users_file, self.monitored_users)
            return username
        return None


class CalendarMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scraper = FreecalendScraper()
        self.data_manager = DataManager(PREVIOUS_DATA_FILE, USERS_FILE)
        self.notification_channel_id = config.NOTIFICATION_CHANNEL_ID
        self.schedule_check.start()

    def cog_unload(self):
        self.schedule_check.cancel()
        self.scraper.cleanup()
        self.data_manager.save_all_data()

    @tasks.loop(hours=config.CHECK_INTERVAL_HOURS)
    async def schedule_check(self):
        if not self.notification_channel_id:
            logger.warning("通知チャンネル未設定のため定期チェックをスキップします。")
            return
        
        channel = self.bot.get_channel(self.notification_channel_id)
        if not channel:
            logger.error(f"通知チャンネル(ID: {self.notification_channel_id})が見つかりません。")
            return
        
        logger.info("=== 定期チェック開始 ===")
        users_to_check = self.data_manager.monitored_users.copy()
        
        for user_id, username in users_to_check.items():
            try:
                # 定期チェックは全予定を取得
                schedule_data = await self.scraper.get_schedule(user_id, username, today_only=False)
                if schedule_data is not None and self.data_manager.has_changed(user_id, schedule_data):
                    logger.info(f"{username}のスケジュールが更新されました。")
                    await self._send_notification(channel, username, schedule_data, user_id)
                else:
                    logger.info(f"{username}のスケジュールに変更はありません。")
                await asyncio.sleep(config.ACCESS_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"{username}のチェック中にエラー: {e}", exc_info=True)
        
        self.data_manager.save_all_data()
        logger.info("=== 定期チェック完了 ===")

    @schedule_check.before_loop
    async def before_schedule_check(self):
        await self.bot.wait_until_ready()

    async def _send_notification(self, channel, username, schedule_data, user_id):
        """スケジュール更新通知を送信"""
        embed = discord.Embed(
            title=f"📅 {username}のスケジュール更新", 
            color=discord.Color.gold(), 
            timestamp=datetime.now()
        )
        embed.description = schedule_data[:4000] if schedule_data else "登録されている今後の予定はありません。"
        
        # フッター情報
        embed.add_field(name="👤 ユーザー", value=f"`{user_id}`", inline=True)
        embed.add_field(name="🕐 確認時刻", value=datetime.now().strftime("%H:%M"), inline=True)
        embed.add_field(
            name="🔗 URL", 
            value=f"[フリカレを開く](https://freecalend.com/open/mem{user_id}/)", 
            inline=True
        )
        
        await channel.send(embed=embed)

    @commands.command(name='check', help="指定ユーザーの【今日の】予定を確認します。")
    async def check_today(self, ctx, *, target: str = None):
        """今日の予定のみを表示"""
        if not target:
            await self._show_user_list(ctx)
            return

        user_id, username = self._find_user(target)
        if not user_id:
            await ctx.send(f"❌ ユーザー「{target}」が見つかりませんでした。")
            return
        
        msg = await ctx.send(f"🔍 {username}の**今日の予定**を取得中...")
        
        # 今日の予定のみを取得
        schedule_data = await self.scraper.get_schedule(user_id, username, today_only=True)
        await msg.delete()
        
        if schedule_data is None:
            await ctx.send(f"❌ {username}のスケジュール取得に失敗しました。ログを確認してください。")
            return
        
        # 今日の予定を表示
        embed = discord.Embed(
            title=f"🔥 {username}の【今日の予定】", 
            color=discord.Color.green(), 
#            timestamp=datetime.now()
        )
        embed.description = schedule_data if schedule_data else "今日の予定はありません。"
#        embed.add_field(
#            name="📋 今後の全予定を確認", 
#            value=f"`!calendar {username}`", 
#            inline=False
#        )
        
        # フッター情報
        embed.add_field(name="👤 ユーザー", value=f"`{user_id}`", inline=True)
        embed.add_field(name="🕐 確認時刻", value=datetime.now().strftime("%H:%M"), inline=True)
        embed.add_field(
            name="🔗 URL", 
            value=f"[フリカレを開く](https://freecalend.com/open/mem{user_id}/)", 
            inline=True
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='calendar', help="指定ユーザーの【今後の全予定】を表示します。")
    async def show_calendar(self, ctx, *, target: str = None):
        """今後の全予定を表示（従来の!checkの動作）"""
        if not target:
            await self._show_user_list(ctx)
            return

        user_id, username = self._find_user(target)
        if not user_id:
            await ctx.send(f"❌ ユーザー「{target}」が見つかりませんでした。")
            return
        
        msg = await ctx.send(f"🔍 {username}の**今後の全予定**を取得中...")
        
        # 全予定を取得
        schedule_data = await self.scraper.get_schedule(user_id, username, today_only=False)
        await msg.delete()
        
        if schedule_data is None:
            await ctx.send(f"❌ {username}のスケジュール取得に失敗しました。ログを確認してください。")
            return
        
        # データが変更されていれば保存
        if self.data_manager.has_changed(user_id, schedule_data):
            self.data_manager.save_all_data()
        
        # 全予定を表示
        embed = discord.Embed(
            title=f"⏰ {username}の【今後の全予定】", 
            color=discord.Color.blue(), 
#            timestamp=datetime.now()
        )
        embed.description = schedule_data[:4000] if schedule_data else "登録されている今後の予定はありません。"
        
        # フッター情報
        embed.add_field(name="👤 ユーザー", value=f"`{user_id}`", inline=True)
        embed.add_field(name="🕐 確認時刻", value=datetime.now().strftime("%H:%M"), inline=True)
        embed.add_field(
            name="🔗 URL", 
            value=f"[フリカレを開く](https://freecalend.com/open/mem{user_id}/)", 
            inline=True
        )
        
        await ctx.send(embed=embed)

    async def _show_user_list(self, ctx):
        """監視ユーザー一覧を表示"""
        users = self.data_manager.monitored_users
        if not users:
            await ctx.send("監視対象のユーザーが登録されていません。`!adduser`で追加してください。")
            return
        
        user_list = "\n".join([f"`{uid}`: **{name}**" for uid, name in users.items()])
        embed = discord.Embed(
            title="📋 監視ユーザー一覧", 
            description=user_list, 
            color=0x0099ff
        )
        embed.set_footer(text="使い方: !check [名前] で今日の予定、!calendar [名前] で全予定")
        await ctx.send(embed=embed)

    def _find_user(self, target: str) -> Tuple[Optional[str], Optional[str]]:
        users = self.data_manager.monitored_users
        if target in users: 
            return target, users[target]
        
        target_lower = target.lower()
        for uid, name in users.items():
            if target_lower in name.lower(): 
                return uid, name
        return None, None

    @commands.command(name='status', help="BOTの現在の監視ステータスを表示します。")
    @commands.has_permissions(administrator=True)
    async def monitoring_status(self, ctx):
        embed = discord.Embed(
            title="📊 監視ステータス", 
            color=0x0099ff, 
#            timestamp=datetime.now()
        )
        status = "🟢 実行中" if self.schedule_check.is_running() else "🔴 停止中"
        embed.add_field(name="定期監視", value=status)
        
        if self.schedule_check.is_running() and self.schedule_check.next_iteration:
            embed.add_field(
                name="次回実行", 
                value=f"<t:{int(self.schedule_check.next_iteration.timestamp())}:R>"
            )
        
        embed.add_field(name="監視ユーザー数", value=f"{len(self.data_manager.monitored_users)}人")
        
        channel = self.bot.get_channel(self.notification_channel_id) if self.notification_channel_id else None
        embed.add_field(name="通知チャンネル", value=channel.mention if channel else "未設定")
        
        await ctx.send(embed=embed)

    @commands.command(name='setchannel', help="通知チャンネルを設定します。")
    @commands.has_permissions(administrator=True)
    async def set_notification_channel(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        self.notification_channel_id = channel.id
        config.NOTIFICATION_CHANNEL_ID = channel.id  # メモリ上のconfigも更新
        await ctx.send(f"✅ 通知チャンネルを {channel.mention} に設定しました。")

    @commands.command(name='adduser', help="監視対象のユーザーを追加します。")
    @commands.has_permissions(administrator=True)
    async def add_user(self, ctx, user_id: str, *, username: str):
        if not user_id.isdigit():
            await ctx.send("❌ ユーザーIDは数字である必要があります。")
            return
        if user_id in self.data_manager.monitored_users:
            await ctx.send(f"⚠️ ユーザーID `{user_id}` は既に登録されています。")
            return
        self.data_manager.add_user(user_id, username)
        await ctx.send(f"✅ **{username}** (ID: `{user_id}`) を監視対象に追加しました。")

    @commands.command(name='removeuser', help="監視対象のユーザーを削除します。")
    @commands.has_permissions(administrator=True)
    async def remove_user(self, ctx, target: str):
        user_id, username = self._find_user(target)
        if not user_id:
            await ctx.send(f"❌ ユーザー「{target}」が見つかりませんでした。")
            return
        if self.data_manager.remove_user(user_id):
            await ctx.send(f"✅ **{username}** (ID: `{user_id}`) を監視対象から削除しました。")
        else:
            await ctx.send(f"❌ ユーザー「{target}」の削除に失敗しました。")


# BOT本体
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'🤖 {bot.user}としてログインしました')
    await bot.add_cog(CalendarMonitor(bot))
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="フリカレ")
    )
    logger.info('⚙️ CalendarMonitor Cogをロードしました。監視を開始します。')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound): 
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ このコマンドを実行する権限がありません。")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ 引数が不足しています: `{error.param.name}`")
    else:
        logger.error(f"コマンドエラー: {ctx.command} - {error}", exc_info=True)
        await ctx.send(f"❌ エラーが発生しました: {error}")

if __name__ == "__main__":
    if not config.DISCORD_BOT_TOKEN or config.DISCORD_BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logger.error("❌ config.pyにDiscord BOTトークンが設定されていません。")
        exit(1)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f: 
            json.dump({}, f)
        logger.info(f"{USERS_FILE} を作成しました。")
        
    try:
        bot.run(config.DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.error(f"❌ BOTの起動に失敗しました: {e}", exc_info=True)