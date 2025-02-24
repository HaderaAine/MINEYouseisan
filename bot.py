import discord
from discord.ext import commands
import os
import re
import datetime
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Intentsの設定
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True  # メッセージ内容の取得

bot = commands.Bot(command_prefix="!", intents=intents)

CATEGORY_NAMES = {
    "upcoming": "📢近日開催予定イベント",
    "current": "📣今日明日開催中イベント",
    "past_5": "🏦過去ログ5",
    "past_4": "🏦過去ログ4",
    "past_3": "🏦過去ログ3",
    "past_2": "🏦過去ログ2",
    "past_1": "🏦過去ログ1"
}

SEPARATOR_CHANNEL_NAME = "❗－－－－－－－－－－"


def parse_channel_date(channel_name):
    """チャンネル名から日付・時間を取得"""
    match = re.search(r"(\d{4})([月火水木金土日])(\d{4})", channel_name)
    if match:
        date_str, _, time_str = match.groups()
        month, day = int(date_str[:2]), int(date_str[2:])
        hour, minute = int(time_str[:2]), int(time_str[2:])
        # 4月～12月を最優先、1月～3月を後に回す
        # return datetime.date(datetime.datetime.now().year, month, day), datetime.time(hour, minute)
        fiscal_order = (month + 9) % 12  # 4→0, 5→1, ..., 12→8, 1→9, 2→10, 3→11
        return fiscal_order, datetime.date(datetime.datetime.now().year, month, day), datetime.time(hour, minute)
    return None, None, None


async def move_tomorrow_channels(guild):
    """翌日のチャンネルを近日開催から今日明日開催へ移動"""
    current_category = discord.utils.get(guild.categories, name=CATEGORY_NAMES["current"])
    upcoming_category = discord.utils.get(guild.categories, name=CATEGORY_NAMES["upcoming"])
    if not current_category or not upcoming_category:
        return

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    for channel in upcoming_category.text_channels:
        channel_fiscal_order, channel_date, _ = parse_channel_date(channel.name)
        if channel_date == tomorrow:
            await channel.edit(category=current_category)


async def sort_channels_by_time(guild):
    """今日明日開催中イベントのチャンネルを時間順に並び替え"""
    current_category = discord.utils.get(guild.categories, name=CATEGORY_NAMES["current"])
    if not current_category:
        return

    channels_with_time = []
    separator_channel = None

    for channel in current_category.text_channels:
        if channel.name == SEPARATOR_CHANNEL_NAME:
            separator_channel = channel
            continue
        channnel_fiscal_order, channel_date, channel_time = parse_channel_date(channel.name)
        if channel_date:
            channels_with_time.append((channel, channel_date, channel_time))

    channels_with_time.sort(key=lambda x: (x[1], x[2]), reverse=False)

    # 並び替え適用
    sorted_channels = [ch[0] for ch in channels_with_time]
    if separator_channel:
        today = datetime.date.today()
        separator_index = next((i for i, ch in enumerate(channels_with_time) if ch[1] > today), len(sorted_channels))
        sorted_channels.insert(separator_index, separator_channel)

    for i, channel in enumerate(sorted_channels):
        await channel.edit(position=i)


async def move_yesterday_channels(guild):
    """昨日のチャンネルを過去ログへ移動"""
    current_category = discord.utils.get(guild.categories, name=CATEGORY_NAMES["current"])
    past_categories = [discord.utils.get(guild.categories, name=CATEGORY_NAMES[f"past_{i}"]) for i in range(5, 0, -1)]

    if not current_category or None in past_categories:
        return

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    past_5_category = past_categories[0]

    for channel in current_category.text_channels:
        channnel_fiscal_order, channel_date, _ = parse_channel_date(channel.name)
        if channel_date == yesterday:
            # 過去ログ5が50チャンネルなら順に移動
            for i in range(5):
                 if len(past_categories[i].text_channels) < 50:
                    for j in range(i+1):
                        if i == 0:
                            break
                        # oldest_channel2 = sorted(past_categories[i-1-j].text_channels, key=lambda c: parse_channel_date(c.name)[0])[0]
                        oldest_channel2 = min(past_categories[i-1-j].text_channels, key=lambda c: parse_channel_date(c.name)[0])
                        await oldest_channel2.edit(category=past_categories[i-j], position=0)
                    await channel.edit(category=past_categories[0], position=0)
                    break
                 elif i == 4: # 過去ログ1まで埋まっている場合、最古のチャンネルを削除
                    # oldest_channel = sorted(past_categories[4].text_channels, key=lambda c: parse_channel_date(c.name)[0])[0]
                    oldest_channel = min(past_categories[4].text_channels, key=lambda c: parse_channel_date(c.name)[0])
                    # チャンネル削除は要検討
                    # await oldest_channel.delete()
                    for j in range(4):
                        #oldest_channel2 = sorted(past_categories[3-j].text_channels, key=lambda c: parse_channel_date(c.name)[0])[0]
                        oldest_channel2 = min(past_categories[3-j].text_channels, key=lambda c: parse_channel_date(c.name)[0])
                        await oldest_channel2.edit(category=past_categories[4-j], position=0)
                    await channel.edit(category=past_categories[0], position=0)
                    break
                     
    """近日開催予定イベント並び替え"""
    upcoming_category = discord.utils.get(guild.categories, name=CATEGORY_NAMES["upcoming"])
    if not upcoming_category:
        return

    channels_with_time = []

    for channel in upcoming_category.text_channels:
        channnel_fiscal_order, channel_date, channel_time = parse_channel_date(channel.name)
        if channel_date:
            channels_with_time.append((channel, channel_date, channel_time))
    
    channels_with_time.sort(key=lambda x: (x[1], x[2], x[3]), reverse=False)
    
        
    sorted_channels = [ch[0] for ch in channels_with_time]
    
    for i, channel in enumerate(sorted_channels):
        await channel.edit(position=i)

    """過去ログ並び替え（未使用）
    for j in range(5):
        
        current_category = past_categories[j]
        if not current_category:
            return
    
        channels_with_time = []
        separator_channel = None
    
        for channel in current_category.text_channels:
            if channel.name == SEPARATOR_CHANNEL_NAME:
                separator_channel = channel
                continue
            channel_date, channel_time = parse_channel_date(channel.name)
            if channel_date:
                channels_with_time.append((channel, channel_date, channel_time))
    
        channels_with_time.sort(key=lambda x: (x[1], x[2]), reverse=False)
    
        
        sorted_channels = [ch[0] for ch in channels_with_time]
        if separator_channel:
            today = datetime.date.today()
            separator_index = next((i for i, ch in enumerate(channels_with_time) if ch[1] > today), len(sorted_channels))
            sorted_channels.insert(separator_index, separator_channel)
    
        for i, channel in enumerate(sorted_channels):
            await channel.edit(position=i)
    """

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for guild in bot.guilds:
        await move_tomorrow_channels(guild)
        await sort_channels_by_time(guild)
        await move_yesterday_channels(guild)
    await bot.close()


bot.run(TOKEN)
