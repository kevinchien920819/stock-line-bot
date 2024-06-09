from flask import Flask, request, abort
import yfinance as yf
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
from linebot.models import FlexSendMessage
from linebot.models import BubbleContainer, BoxComponent, TextComponent, ImageComponent
import pandas as pd
import requests 
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from bs4 import BeautifulSoup
app = Flask(__name__)

line_bot_api = LineBotApi('9mB+JjaPOS0dbI59es4hlL01i0oKP9Ip/+JebiV4UX29fcNCqfZsV0KWg3oDo58c8A/mG5CD3QSx/bfQn2QLGm6h5KjFGazqFoGW9Wks9PP/PpODcnLTIAIJiUXzJjwFc0u97t78kjyhEJUUz9YmTAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('d2bbe9897c879dba79245f993f32f893')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def get_stock_info(stock_code):
    stock = yf.Ticker(stock_code)
    stock_info = stock.info
    # 確保有足夠的資訊可供格式化
    if 'dayHigh' in stock_info and 'dayLow' in stock_info:
        high = stock_info['dayHigh']
        low = stock_info['dayLow']
    url = f'https://tw.stock.yahoo.com/quote/{stock_code}'  # 台積電 Yahoo 股市網址
    web = requests.get(url)                        # 取得網頁內容
    soup = BeautifulSoup(web.text, "html.parser")  # 轉換內容

    # 初始化價格和趨勢
    cur_price = None
    trend = 0

    # 嘗試獲取當前價格和趨勢
    price_container = soup.find('div', class_='D(f) Fx(a) Mb($m-module)')
    if price_container:
        name = price_container.find('h1').get_text()  # 獲取股票名稱
        cur_price_spans = price_container.find_all('span')
        if len(cur_price_spans) > 0:
            cur_price = cur_price_spans[2].get_text()  # 獲取當前價格
            
            if 'C($c-trend-up)' in cur_price_spans[2]['class']:
                trend = 1  # 趨勢向上
            elif 'C($c-trend-down)'in cur_price_spans[2]['class']:
                trend = -1  # 趨勢向下
            trans = cur_price_spans[3].get_text()
            percent = cur_price_spans[5].get_text()
            if(trans == 'USD'):
                trans = cur_price_spans[4].get_text()
                percent = cur_price_spans[6].get_text()
            
        

    return(name, cur_price, trend,trans,percent,high,low)

def draw_stock_chart(stock_code):
    res = requests.get(f'https://tw.stock.yahoo.com/_td-stock/api/resource/FinanceChartService.ApacLibraCharts;autoRefresh=1717850668182;symbols=%5B%22{stock_code}.TW%22%5D;type=tick?bkt=twfinance-rr-control&device=desktop&ecma=modern&feature=enableGAMAds%2CenableGAMEdgeToEdge%2CenableEvPlayer&intl=tw&lang=zh-Hant-TW&partner=none&prid=5mso4t9j68kf0&region=TW&site=finance&tz=Asia%2FTaipei&ver=1.4.147&returnMeta=true')
    
    js = res.json()['data']
    close = js[0]['chart']['indicators']['quote'][0]['close']
    timestamp = js[0]['chart']['timestamp']

    df = pd.DataFrame({'timestamp': timestamp, 'close': close})
    df['dt'] = pd.to_datetime(df['timestamp'] + 3600 * 8, unit='s')

    plt.figure(figsize=(10, 5))
    plt.plot(df['dt'], df['close'])
    plt.title('Stock Price Over Time')
    plt.xlabel('Date')
    plt.ylabel('Price')
    image_path = 'img.jpg'
    plt.savefig(image_path)
    plt.close()
    return image_path


def upload_image_to_imgur(image_path):
    """
    Upload an image to Imgur and return the image URL.

    Args:
    image_path (str): The local path to the image file.
    client_id (str): The Client ID from your Imgur application.

    Returns:
    str: URL of the uploaded image on Imgur.
    """
    headers = {'Authorization': 'Client-ID ''e79efc24dbf4a23'}
    files = {'image': open(image_path, 'rb')}
    response = requests.post("https://api.imgur.com/3/image", headers=headers, files=files)
    return response.json()['data']['link'] if response.status_code == 200 else None




def reply(stock_num, url, stock_info):
    # 基本消息結構
    content = {
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": url,
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover",
            "action": {
                "type": "uri",
                "uri": "https://line.me/"
            }
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"{stock_num} {stock_info[0]}",
                    "weight": "bold",
                    "size": "xl"
                }
            ]
        }
    }

    # 根據股票趨勢條件添加內容
    base_contents = {
        "type": "box",
        "layout": "baseline",
        "margin": "md",
        "contents": []
    }

    if stock_info[2] == 1:
        base_contents["contents"].append({
            "type": "icon",
            "url": "https://svn.apache.org/repos/asf/incubator/ooo/symphony/trunk/main/extras/source/gallery/arrows/A42-TrendArrow-Red-GoUp.png"
        })
        base_contents["contents"].append({
            "type": "text",
            "text": f"{stock_info[3]} {stock_info[4]}",
            "color": "#EE0000"
        })
    else:
        base_contents["contents"].append({
            "type": "icon",
            "url": "https://svn.apache.org/repos/asf/incubator/ooo/symphony/trunk/main/extras/source/gallery/arrows/A43-TrendArrow-Green-GoDown.png"
        })
        base_contents["contents"].append({
            "type": "text",
            "text": f"{stock_info[3]} {stock_info[4]}",
            "color": "#00EE00"
        })

    # 將基本內容添加到主體中
    content['body']['contents'].append(base_contents)

    # 添加更多固定內容
    max_place_box = {
        "type": "box",
        "layout": "baseline",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": "最高價",
                "color": "#aaaaaa",
                "size": "lg",
                "flex": 2
            },
            {
                "type": "text",
                "text": f"{stock_info[5]}",
                "wrap": True,
                "color": "#666666",
                "size": "md",
                "flex": 5
            }
        ]
    }
    min_place_box ={
        "type": "box",
        "layout": "baseline",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": "最低價",
                "color": "#aaaaaa",
                "size": "lg",
                "flex": 2
            },
            {
                "type": "text",
                "text": f"{stock_info[6]}",
                "wrap": True,
                "color": "#666666",
                "size": "md",
                "flex": 5
            }
        ]
    }

    # # 假設您需要重複相同的資訊
    # for _ in range(5):
        # content['body']['contents'].append(place_box.copy())  # 添加複製以防止相同參照的問題
    content['body']['contents'].append(max_place_box)  # 添加複製以防止相同參照的問題
    content['body']['contents'].append(min_place_box)  # 添加複製以防止相同參照的問題
    

    return content

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # if event.message.text == '圖片':
    #     message = ImageSendMessage(
    #             original_content_url = image_url,
    #             preview_image_url = image_url
    #         )
    #     line_bot_api.reply_message(event.reply_token, message)
    # else:
    if event.message.text[-3:] == '.TW':
        id = event.message.text[:-3] 
    else:
        id = event.message.text
    stock_info = get_stock_info(event.message.text)
    print(stock_info)
    img_path = draw_stock_chart(id)
    # 使用函數上傳圖片
    image_url = upload_image_to_imgur(img_path)
    messages = FlexSendMessage(alt_text="Send Stock Information", contents=reply(id,image_url,stock_info))
    line_bot_api.reply_message(event.reply_token,messages)

if __name__ == "__main__":
    app.run()
