import os
import requests
from datetime import datetime
from dotenv import load_dotenv

from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import web_search

load_dotenv()

# Grok
client = Client(api_key=os.getenv("GROK_API_KEY"))

# Facebook
PAGE_ID = os.getenv("FB_PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_TOKEN")
GRAPH_API_VERSION = "v24.0"
GRAPH_API_FEED_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PAGE_ID}/feed"
GRAPH_API_PHOTO_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PAGE_ID}/photos"
tags = f"#Bitcoin #ETH #比特幣 #乙太幣 #加密貨幣"

# Binance
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"

# Prompts
news_prompt = f"""
今天是 {datetime.now().strftime("%Y年%m月%d日")}, 使用web_search搜尋24小時內全球最重要的加密貨幣新聞。
依照以下格式輸出:
📌 24小時內加密貨幣市場消息:
• [中文摘要] (來源: 連結)
若沒有明顯重大新聞則寫：無重大新聞事件
"""

macro_env_prompt = f"""
今天是 {datetime.now().strftime("%Y年%m月%d日")}, 使用web_search搜尋24小時內全球最重要的總體金融/宏觀經濟。
依照以下格式輸出:
📌 24小時內總體金融/宏觀經濟消息:
• [中文摘要] (來源: 連結)
若沒有明顯重大新聞則寫：無重大新聞事件
"""

security_prompt = f"""
今天是 {datetime.now().strftime("%Y年%m月%d日")}, 使用web_search搜尋24小時內加密貨幣安全與風險(駭客/漏洞/盜領等)。
依照以下格式輸出:
📌 24小時內安全事件與風險預警:
• [中文摘要] (來源: 連結)
若沒有明顯重大新聞則寫：無重大新聞事件
"""

def grok_search_and_summarize(prompt: str) -> str:
    chat = client.chat.create(
        model="grok-4-1-fast-reasoning",
        tools=[web_search(),],
        temperature=0.3,
    )

    chat.append(user(prompt.strip()))

    content = ""
    for response, chunk in chat.stream():
        if chunk.content:
            content += chunk.content
        for tool_call in chunk.tool_calls:
            print(f"[Grok] Tool calling: {tool_call.function.name} - arguments: {tool_call.function.arguments}")

    return content.strip()

def get_price(symbol: str) -> float | None:
    try:
        resp = requests.get(BINANCE_TICKER_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return float(data["price"])
    except Exception as e:
        print(f"[get_price] 取得 {symbol} 價格失敗: {e}")
        return None


def fetch_all_prices() -> dict:
    prices = {
        "BTC": get_price("BTCUSDT"),
        "ETH": get_price("ETHUSDT"),
        "XRP": get_price("XRPUSDT"),
        "SOL": get_price("SOLUSDT"),
        "ADA": get_price("ADAUSDT"),
        "LINK": get_price("LINKUSDT"),
        "SUI": get_price("SUIUSDT"),
        "APT": get_price("APTUSDT"),
    }
    return prices

def format_price_block(prices: dict) -> str:
    lines = ["📌 即時價格 (USD)"]
    for symbol, value in prices.items():
        if value is None:
            lines.append(f"- {symbol}: 取得失敗")
        else:
            lines.append(f"- {symbol}: {value:,.2f}")
    return "\n".join(lines)

def format_post(prices: dict, news_report: str, macro_env: str, security: str, tags: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    price_block = format_price_block(prices)

    final_post = (
        f"📅 {today} 加密貨幣市場摘要\n\n"
        f"{price_block}\n\n"
        f"{news_report}\n\n"
        f"{macro_env}\n\n"
        f"{security}\n\n"
        f"{tags}"
    )
    return final_post

def post_to_facebook(message: str, image_path: str | None = None) -> dict | None:
    if not PAGE_ACCESS_TOKEN:
        raise RuntimeError("[ERROR] FB_PAGE_TOKEN not set, failed to publish to Facebook")

    if image_path is not None:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"[WARN] Unable to find: {image_path}")

        with open(image_path, "rb") as f:
            files = {"source": f}
            payload = {
                "caption": message,
                "access_token": PAGE_ACCESS_TOKEN,
            }
            response = requests.post(GRAPH_API_PHOTO_URL, data=payload, files=files)
    else:
        # Text-only
        payload = {
            "message": message,
            "access_token": PAGE_ACCESS_TOKEN,
        }
        response = requests.post(GRAPH_API_FEED_URL, data=payload)

    try:
        data = response.json()
    except Exception:
        print("[ERROR] Failed to parse Facebook JSON response")
        print(response.text)
        return None

    if not response.ok:
        print("[ERROR] Failed to publish to Facebook")
        print(data)
        return None

    print("[INFO] Published to Facebook successfully")
    print(data)
    return data

def main(post_to_fb: bool = False, image_path: str | None = None):
    print("[INFO] Fetch crytocurrency spot market prices from Binance")
    prices = fetch_all_prices()
    print(prices)

    print("[INFO] Ask Grok to search cryptocurrency news in the last 24 hours")
    news_report = grok_search_and_summarize(news_prompt)

    print("[INFO] Ask Grok to search macroeconomics news in the last 24 hours")
    maco_env_report = grok_search_and_summarize(macro_env_prompt)

    print("[INFO] Ask Grok to search cryptocurrency security news in the last 24 hours")
    security_report = grok_search_and_summarize(security_prompt)

    print("[INFO] Post preview:")
    final_post = format_post(prices, news_report, maco_env_report, security_report, tags)
    print(final_post)

    if post_to_fb:
        post_to_facebook(final_post, image_path=image_path)

if __name__ == "__main__":
    main(post_to_fb=True, image_path="btc.png")
