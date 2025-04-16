import requests
import random
import json

with open('config.json', 'r') as f:
    config = json.load(f)

ip = config['ip']
port = config['port']
url = f'http://{ip}:{port}/'
speaker_id = config['speaker_id']

def read_speaker_id(change_id):
    global speaker_id
    speaker_id = change_id
    print(f"voicevox.py: {speaker_id}")

def voice_generate(messages):
    params = {
        'text': messages,
        'speaker': speaker_id
    }
    print(params)

    audio_query = requests.post(url + 'audio_query', params=params)
    print(f"audio_query.status_code = {audio_query.status_code}")
    if audio_query.status_code == 200:
        print("クエリ作成に成功しました。")
        audio_query_json = audio_query.json()
        message_length = len(messages)
        if message_length >= 200:
            audio_query_json['speedScale'] = 2.0
            audio_query_json['pauseLengthScale'] = 2.0
        elif message_length >= 100:
            audio_query_json['speedScale'] = 1.5
            audio_query_json['pauseLengthScale'] = 1.5

        print(audio_query.json())
        print(f"話者の速度: {audio_query_json['speedScale']} 句読点の速度: {audio_query_json['pauseLengthScale']}")

        synthesis = requests.post(url + 'synthesis', params=params, json=audio_query_json)
        print(f"synthesis.status_code = {synthesis.status_code}")
        if synthesis.status_code == 200:
            ramdom_file = random.randrange(100000, 999999)
            file_path = f'voice_{ramdom_file}.mp3'
            with open(file_path, 'wb') as f:
                f.write(synthesis.content)

            print("音声合成に成功しました。",file_path)

            return file_path

        elif 400 <= synthesis.status_code <= 499:
            print("(音声合成)クライアント側にエラーが発生しました。")

        elif 500 <= synthesis.status_code <= 599:
            print("(音声合成)サーバー側にエラーが発生しました。")

        else:
            print("(音声合成)予期せぬエラーが発生しました。")

    elif 400 <= audio_query.status_code <= 499:
        print("(クエリ)クライアント側にエラーが発生しました。")

    elif 500 <= audio_query.status_code <= 599:
        print("(クエリ)サーバー側にエラーが発生しました。")

    else:
        print("(クエリ)予期せぬエラーが発生しました。")