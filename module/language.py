# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2025/3/1 1:15
# File:language.py
translations: dict = {
    'single': ['單一檔案'],
    'group': ['媒體組'],
    'comment': ['評論區'],
    'topic': ['話題'],
    'video': ['影片'],
    'photo': ['圖片'],
    'document': ['文件'],
    'audio': ['音訊'],
    'voice': ['語音'],
    'animation': ['GIF'],
    'video_note': ['影片筆記'],
    'live_photo': ['實況圖片'],
    'media': ['媒體'],
    'pending': ['排隊中'],
    'downloading': ['下載中'],
    'uploading': ['上載中'],
    'success': ['成功'],
    'failure': ['失敗'],
    'sent': ['已傳送'],
    'skip': ['略過'],
    'retry': ['重試'],
    'link': ['[連結]'],
    'link type': ['[連結類型]'],
    'size': ['[大小]'],
    'status': ['[狀態]'],
    'file': ['[檔案]'],
    'error size': ['[錯誤大小]'],
    'actual size': ['[實際大小]'],
    'already exist': ['[已存在]'],
    'channel': ['[頻道]'],
    'message id': ['[訊息ID]'],
    'type': ['[類型]'],
    're-download': ['[重新下載]'],
    're-upload': ['[重新上載]'],
    'retry times': ['[重試次數]'],
    'current download task': ['[目前下載任務數]'],
    'current upload task': ['[目前上載任務數]'],
    'reason': ['原因'],
    'resume': ['[斷點續傳]'],
    'download task': ['「📥下載任務」'],
    'upload task': ['「📤上載任務」'],
    'download and upload task': ['「📥📤下載後上載任務」'],
    'forward success': ['轉發成功'],
    'forward failure': ['轉發失敗'],
    'skip forward': ['跳過轉發'],
    'upload file part': ['[上載缺失分片]'],
    'IP': ['IP 位址'],
    'port': ['連接埠'],
    'username': ['帳號'],
    'password': ['密碼']
}


def _t(text: str):
    try:
        if text in translations:
            return translations[text][0]
        else:
            return text
    except Exception:  # noqa.
        return text
