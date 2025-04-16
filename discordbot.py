import discord
import os
import asyncio
import json
import re
from discord import app_commands
from discord.app_commands import Choice
from dotenv import load_dotenv
from collections import deque
from voicevox import voice_generate, read_speaker_id

load_dotenv()

token = os.getenv("Discord_Token")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

voice_queue = deque()
is_playing = False
disconnect_timer = None

with open('config.json', 'r', encoding="utf-8") as f:
    config = json.load(f)
tts_channel_id = config['tts_channel_id']
tts_channel_name = config['tts_channel_name']
read_user = config['read_user']

async def play_next(guild):
    global is_playing
    if not voice_queue:
        is_playing = False
        return

    file_path = voice_queue.popleft()
    sounds = await discord.FFmpegOpusAudio.from_probe(file_path)
    print("再生しました。",file_path)

    def delete_temp(error):
        if error:
            print(f"エラーが発生しました: {error}")
        os.remove(file_path)
        asyncio.run_coroutine_threadsafe(play_next(guild), client.loop)

    guild.voice_client.play(sounds, after=delete_temp)

async def enqueue_and_play(guild, file_path):
    global is_playing
    voice_queue.append(file_path)
    if not is_playing:
        is_playing = True
        await play_next(guild)

async def check_voice_member_state(guild):
    if guild.voice_client and guild.voice_client.channel:
        member_count = sum(1 for member in guild.voice_client.channel.members if not member.bot)

        if member_count == 0:
            await start_disconnect_timer(guild)
        else:
            await cancel_disconnect_timer()

async def start_disconnect_timer(guild):
    global disconnect_timer
    await cancel_disconnect_timer()
    print("ユーザー数が0のため、ボイスチャンネルの退出カウントを開始します。")
    disconnect_timer = asyncio.create_task(disconnect_after_delay(guild))

async def cancel_disconnect_timer():
    global disconnect_timer
    if disconnect_timer and not disconnect_timer.done():
        disconnect_timer.cancel()
        disconnect_timer = None
        print("ボイスチャンネルの退出カウントを停止しました。")

async def disconnect_after_delay(guild):
    await asyncio.sleep(300)
    if guild.voice_client:
        await guild.voice_client.disconnect()
        print("一定時間が経過したため、ボイスチャンネルを退出しました。")

@client.event
async def on_ready():
    print("Botがオンライン")
    await tree.sync()

@client.event
async def voice_channel_state_update(member, before, after):
    if member.bot or not member.guild.voice_client:
        return
    bot_channel = member.guild.voice_client.channel

    if before.channel == bot_channel and after.channel != bot_channel:
        await check_voice_member_state(member.guild)

    elif after.channel == bot_channel and before.channel != bot_channel:
        await cancel_disconnect_timer()

    if client.user == member and after.channel is None:
        global is_playing, voice_queue
        is_playing = False
        voice_queue.clear()
        print("ボイスチャンネルからキックされたため、再生を中断し状態をリセットしました。")

@tree.command(name="tts_join", description="ボイスチャンネルに参加します。")
async def tts_join(interaction: discord.Interaction):
    if interaction.user.voice is None:
        await interaction.response.send_message("ボイスチャンネルに接続してください。")
        print("ボイスチャンネルに接続してください。")
        return
    else:
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message(f"ボイスチャンネルに接続しました。\n現在の読み上げチャンネルは「{tts_channel_name}」です。")
        print(f"ボイスチャンネルに接続しました。現在の読み上げチャンネルは「{tts_channel_name}」です。")

@tree.command(name="tts_left", description="ボイスチャンネルから切断します。")
async def tts_left(interaction: discord.Interaction):
    await interaction.guild.voice_client.disconnect()
    await cancel_disconnect_timer()
    await interaction.response.send_message("ボイスチャンネルから切断しました。")
    print("ボイスチャンネルから切断しました。")

@tree.command(name="tts_set", description="読み上げるチャンネルを設定します。")
async def tts_set(interaction: discord.Interaction):
    global tts_channel_id, tts_channel_name, config
    tts_channel_id = interaction.channel_id
    tts_channel_name = interaction.channel.name
    config['tts_channel_id'] = tts_channel_id
    config['tts_channel_name'] = tts_channel_name
    with open('config.json', 'w', encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    await interaction.response.send_message(f"読み上げチャンネルを「{tts_channel_name}」に設定しました。")
    print(f"読み上げチャンネルを「{tts_channel_name}」に設定しました。", tts_channel_id)

@tree.command(name="tts_reset", description="読み上げるチャンネルをリセットします。")
async def tts_reset(interaction: discord.Interaction):
    global tts_channel_id, tts_channel_name, config
    tts_channel_id = None
    tts_channel_name = None
    config['tts_channel_id'] = tts_channel_id
    config['tts_channel_name'] = tts_channel_name
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    await interaction.response.send_message("読み上げチャンネルの設定をリセットしました。")
    print("読み上げチャンネルの設定をリセットしました。")

@tree.command(name="tts_speaker", description="話者を変更します。")
async def tts_speaker(interaction: discord.Interaction, speaker_id: str):
    global config
    speaker_id = int(speaker_id)
    config['speaker_id'] = speaker_id
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    read_speaker_id(speaker_id)
    await interaction.response.send_message(f"話者をID「{speaker_id}」に変更しました。")
    print(f"{speaker_id}に変更しました。")

@tree.command(name='tts_read', description="ボイスチャンネルに参加していないユーザーのメッセージの読み上げに関する設定変更")
@app_commands.choices(commands=[
    Choice(name="読む", value="True"),
    Choice(name="読まない", value="False"),
])
async def tts_read(interaction: discord.Interaction, commands: Choice[str]):
    global read_user, config
    if commands.value == "True":
        read_user = "True"
        config['read_user'] = read_user
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        await interaction.response.send_message(f"設定を「{commands.name}」変更しました。")
        print (f"設定を「{commands.name}」変更しました。")
    else:
        read_user = "False"
        config['read_user'] = read_user
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        await interaction.response.send_message(f"設定を「{commands.name}」変更しました。")
        print(f"設定を「{commands.name}」変更しました。")

@client.event
async def on_message(message):
    if message.author == client.user or message.channel.id != tts_channel_id or message.stickers:
        return

    else:
        if read_user == "False" and message.author.voice is None:
            return

        messages = message.content
        messages = re.sub(r'<a?:[a-zA-Z0-9_]+:[0-9]+>', "カスタム絵文字", messages)
        messages = re.sub(r'(https?://[^\s]+)', "ユーアールエル", messages)
        file_path = voice_generate(messages)

        await enqueue_and_play(message.guild, file_path)
        return

if token is None:
    print("Discord_Tokenにトークンが設定されていません。")
else:
    client.run(token)