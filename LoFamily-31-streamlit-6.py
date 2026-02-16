import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import urllib.parse
import time
import re

# 引入 googlemaps
try:
    import googlemaps
except ImportError:
    googlemaps = None

# 嘗試匯入 ZoneInfo
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# 嘗試匯入 twder
try:
    import twder
except ImportError:
    twder = None

# ==========================================
# 設定：Google Maps API Key
# 請確認您的 Key 是否有效，並注意額度使用
# ==========================================
GOOGLE_MAPS_API_KEY = "AIzaSyBK2mfGSyNnfytW7sRkNM5ZWqh2SVGNabo"  # 您的原始 Key

# ==========================================
# 頁面基本設定 (Page Config)
# ==========================================
st.set_page_config(
    page_title="四維家族 常用工具 (長輩友善版)",
    layout="wide",  # 使用寬螢幕模式以容納左右欄
    initial_sidebar_state="collapsed"
)

# ==========================================
# CSS 樣式注入 (模擬原本的配色與大字體)
# ==========================================
st.markdown("""
    <style>
    /* 全域背景色設定需透過 Streamlit 主題設定，這裡針對文字顏色做加強 */
    .big-font { font-size: 24px !important; font-weight: bold; font-family: "Microsoft JhengHei", sans-serif; }
    .title-font { font-size: 32px !important; font-weight: bold; color: #333333; margin-bottom: 10px; }
    
    /* 顏色定義 */
    .gold-text { color: #f1c40f; font-weight: bold; }   /* 去程預設色 */
    .blue-text { color: #00d2d3; font-weight: bold; }   /* 回程預設色 */
    .red-text { color: #ff3333; font-weight: bold; }    /* 警示色/油價 */
    .green-text { color: #2ecc71; font-weight: bold; }  /* 匯率 */
    
    /* 卡片式外框模擬 */
    .card {
        background-color: #2c3e50;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        color: white;
    }
    
    /* 超連結樣式去除底線，讓它看起來像文字按鈕 */
    a { text-decoration: none; }
    a:hover { text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 邏輯功能函式庫 (Logic Functions)
# ==========================================

def get_world_clock():
    """計算世界時間"""
    now_utc = datetime.now(timezone.utc)
    try:
        if ZoneInfo:
            tz_tw = ZoneInfo("Asia/Taipei")
            tz_bos = ZoneInfo("America/New_York")
            tz_ger = ZoneInfo("Europe/Berlin")
            time_tw = now_utc.astimezone(tz_tw)
            time_bos = now_utc.astimezone(tz_bos)
            time_ger = now_utc.astimezone(tz_ger)
        else:
            raise ImportError
    except:
        time_tw = now_utc + timedelta(hours=8)
        time_bos = now_utc - timedelta(hours=5)
        time_ger = now_utc + timedelta(hours=1)

    fmt = "%H:%M:%S"
    return {
        "TW": time_tw.strftime(fmt),
        "BOS": time_bos.strftime(fmt),
        "GER": time_ger.strftime(fmt)
    }

def get_currency_rate():
    """取得匯率 (無快取，每次刷新抓取)"""
    if not twder:
        return "警告: 未安裝 twder"
    
    try:
        usd = twder.now('USD')[2]
        eur = twder.now('EUR')[2]
        jpy = twder.now('JPY')[2]
        return f"🇺🇸 美金 : {usd} | 🇪🇺 歐元 : {eur} | 🇯🇵 日圓 : {jpy}"
    except Exception as e:
        return f"匯率讀取失敗: {e}"

@st.cache_data(ttl=600)  # 快取 10 分鐘，避免頻繁呼叫 API
def get_weather_data():
    """取得天氣資料"""
    locations = [
        {"name": "苗栗", "lat": 24.51, "lon": 120.82},
        {"name": "新竹", "lat": 24.80, "lon": 120.99},
        {"name": "芎林", "lat": 24.77, "lon": 121.07},
        {"name": "木柵", "lat": 24.99, "lon": 121.57},
        {"name": "內湖", "lat": 25.08, "lon": 121.56},
        {"name": "波士頓", "lat": 42.36, "lon": -71.06},
        {"name": "德國", "lat": 51.05, "lon": 13.74},
    ]
    
    results = []
    for loc in locations:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['lat']}&longitude={loc['lon']}&current=temperature_2m,weather_code&hourly=precipitation_probability&timezone=auto&forecast_days=1"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                temp = data['current']['temperature_2m']
                w_code = data['current'].get('weather_code', -1)
                
                # 簡易降雨機率與圖示邏輯 (保留您原始邏輯)
                icon = ""
                rain_text = ""
                try:
                    # 抓取目前小時的降雨機率
                    current_hour = datetime.now().strftime("%Y-%m-%dT%H:00")
                    hourly_times = data['hourly']['time']
                    if current_hour in hourly_times:
                        idx = hourly_times.index(current_hour)
                        # 取未來 5 小時最大值
                        probs = data['hourly']['precipitation_probability'][idx:idx+5]
                        max_prob = max(probs) if probs else 0
                        
                        if w_code in [71, 73, 75, 77, 85, 86]: icon = "❄️"
                        elif w_code in [95, 96, 99]: icon = "⛈️"
                        else:
                            if max_prob <= 10: icon = "☀️"
                            elif max_prob <= 40: icon = "☁️"
                            elif max_prob <= 70: icon = "🌦️"
                            else: icon = "☔"
                        rain_text = f" ({icon}{max_prob}%)"
                except:
                    pass

                results.append(f"**{loc['name']}**: {temp}°C{rain_text}")
            else:
                results.append(f"{loc['name']}: N/A")
        except:
            results.append(f"{loc['name']}: 連線錯誤")
    
    return "  \n".join(results) # 使用 Markdown 換行

@st.cache_data(ttl=3600) # 快取 1 小時
def get_gas_price():
    """取得油價"""
    url = "https://gas.goodlife.tw/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            cpc = soup.find("div", {"id": "cpc"})
            if cpc:
                prices = cpc.find_all("li")
                p_data = {"92": "--", "95": "--", "98": "--"}
                for p in prices:
                    text = p.get_text().strip()
                    if "92" in text: p_data['92'] = text.split(':')[-1].strip()
                    if "95" in text: p_data['95'] = text.split(':')[-1].strip()
                    if "98" in text: p_data['98'] = text.split(':')[-1].strip()
                return p_data
    except:
        pass
    return None

def parse_duration_to_minutes(text):
    """解析 Google Maps 回傳的時間文字為分鐘數"""
    try:
        total = 0
        rem = text
        if "小時" in text:
            parts = text.split("小時")
            total += int(parts[0].strip()) * 60
            rem = parts[1]
        if "分鐘" in rem:
            mins = rem.replace("分鐘", "").strip()
            if mins.isdigit():
                total += int(mins)
        return total
    except:
        return 0

def get_google_map_url(start, end):
    """產生 Google Maps 導航連結"""
    s_enc = urllib.parse.quote(start)
    e_enc = urllib.parse.quote(end)
    return f"https://www.google.com.tw/maps/dir/{s_enc}/{e_enc}"

@st.cache_data(ttl=300) # 路況快取 5 分鐘
def get_traffic_data(base_addr, locations, api_key):
    """取得路況資料 (一次處理所有地點以節省快取管理)"""
    if not api_key or "YOUR_KEY" in api_key or not googlemaps:
        return "API_ERROR"

    gmaps = googlemaps.Client(key=api_key)
    results = []

    for item in locations:
        name = item['name']
        target_addr = item['addr']
        return_label = item['return_label']
        std_go = item['std_go']
        std_back = item['std_back']

        # --- 去程 ---
        go_info = {"text": "計算中", "color": "gold-text", "diff": 0, "url": get_google_map_url(target_addr, base_addr)}
        try:
            m_go = gmaps.distance_matrix(origins=target_addr, destinations=base_addr, mode='driving', departure_time=datetime.now(), language='zh-TW')
            el_go = m_go['rows'][0]['elements'][0]
            if 'duration_in_traffic' in el_go:
                txt = el_go['duration_in_traffic']['text']
                mins = parse_duration_to_minutes(txt)
                diff = mins - std_go
                sign = "+" if diff > 0 else ""
                color = "red-text" if diff > 20 else "gold-text"
                go_info.update({"text": f"{txt} ({sign}{diff}分)", "color": color, "diff": diff})
        except Exception as e:
            go_info["text"] = "查詢失敗"

        # --- 回程 ---
        back_info = {"text": "計算中", "color": "blue-text", "diff": 0, "url": get_google_map_url(base_addr, target_addr)}
        try:
            m_back = gmaps.distance_matrix(origins=base_addr, destinations=target_addr, mode='driving', departure_time=datetime.now(), language='zh-TW')
            el_back = m_back['rows'][0]['elements'][0]
            if 'duration_in_traffic' in el_back:
                txt = el_back['duration_in_traffic']['text']
                mins = parse_duration_to_minutes(txt)
                diff = mins - std_back
                sign = "+" if diff > 0 else ""
                color = "red-text" if diff > 20 else "blue-text"
                back_info.update({"text": f"{txt} ({sign}{diff}分)", "color": color, "diff": diff})
        except Exception as e:
            back_info["text"] = "查詢失敗"
            
        results.append({
            "name": name,
            "return_label": return_label,
            "go": go_info,
            "back": back_info
        })
    return results

# ==========================================
# 主程式 UI 建構
# ==========================================

# 標題
st.markdown("<div style='text-align: center; font-size: 36px; font-weight: bold; margin-bottom: 20px;'>四維家族 專屬工具箱 🛠️</div>", unsafe_allow_html=True)

# 建立左右兩欄 (比例 1:1)
col_left, col_right = st.columns([1, 1], gap="large")

# --- 左欄內容 ---
with col_left:
    # 1. 第一列：世界時間 + 天氣 (再切分兩欄)
    sub_c1, sub_c2 = st.columns(2)
    
    with sub_c1:
        st.markdown("<div class='title-font'>🕒 世界時間 (Live)</div>", unsafe_allow_html=True)
        clock_data = get_world_clock()
        st.markdown(f"""
        <div class='card big-font' style='color: #f1c40f;'>
        台灣 : {clock_data['TW']}<br>
        波士頓 : {clock_data['BOS']}<br>
        德國 : {clock_data['GER']}
        </div>
        """, unsafe_allow_html=True)

    with sub_c2:
        st.markdown("<div class='title-font'>⛅ 即時氣溫</div>", unsafe_allow_html=True)
        weather_text = get_weather_data()
        st.markdown(f"""
        <div class='card big-font' style='font-size: 20px !important; color: #00d2d3;'>
        {weather_text}
        </div>
        """, unsafe_allow_html=True)

    # 2. 第二列：即時匯率
    st.markdown("---")
    st.markdown("<div class='title-font'>💱 即時匯率 (台銀)</div>", unsafe_allow_html=True)
    currency_text = get_currency_rate()
    st.markdown(f"<div class='big-font green-text'>{currency_text}</div>", unsafe_allow_html=True)

    # 3. 第三列：油價
    st.markdown("---")
    st.markdown("<div class='title-font'>⛽ 今日油價 (中油)</div>", unsafe_allow_html=True)
    gas_data = get_gas_price()
    if gas_data:
        st.markdown(f"""
        <div class='big-font red-text' style='text-align: center; border: 2px solid #e74c3c; padding: 10px; border-radius: 10px;'>
        92無鉛: {gas_data['92']} | 95無鉛: {gas_data['95']} | 98無鉛: {gas_data['98']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("油價載入失敗")
        
    # 左欄重新整理按鈕
    if st.button("🔄 更新左欄資訊 (天氣/匯率)", use_container_width=True):
        st.cache_data.clear() # 清除快取以強制更新
        st.rerun()

# --- 右欄內容 (路況) ---
with col_right:
    st.markdown("<div class='title-font'>🚗 即時路況 (Google Map)</div>", unsafe_allow_html=True)
    st.info("※ 點擊下方文字可直接開啟 Google 地圖導航")

    # 定義地址與標準時間 (完全參照您提供的設定)
    base_addr = "苗栗縣公館鄉鶴山村11鄰鶴山146號"
    locations = [
        {"name": "月華家", "addr": "文山區木柵路二段109巷137號", "return_label": "反木柵", "std_go": 76, "std_back": 76},
        {"name": "秋華家", "addr": "新竹的名人大矽谷", "return_label": "反芎林", "std_go": 34, "std_back": 36},
        {"name": "孟竹家", "addr": "新竹市東區太原路128號", "return_label": "反新竹", "std_go": 31, "std_back": 33},
        {"name": "小凱家", "addr": "台北市內湖區文湖街21巷", "return_label": "反內湖", "std_go": 77, "std_back": 79}
    ]

    # 取得路況資料
    traffic_res = get_traffic_data(base_addr, locations, GOOGLE_MAPS_API_KEY)

    if traffic_res == "API_ERROR":
        st.error("⚠️ Google Maps API 未設定或套件遺失")
    else:
        for item in traffic_res:
            # 使用 HTML 渲染卡片與連結
            st.markdown(f"""
            <div class='card'>
                <div style='font-size: 22px; font-weight: bold; border-bottom: 1px solid #7f8c8d; margin-bottom: 10px; padding-bottom: 5px;'>
                    🏠 {item['name']}
                </div>
                <div style='font-size: 20px; margin-bottom: 5px;'>
                    <a href="{item['go']['url']}" target="_blank" class="{item['go']['color']}">
                        往苗栗 : {item['go']['text']}
                    </a>
                </div>
                <div style='font-size: 20px;'>
                    <a href="{item['back']['url']}" target="_blank" class="{item['back']['color']}">
                        {item['return_label']} : {item['back']['text']}
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    if st.button("🔄 更新路況資訊", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 底部 Footer
# ==========================================
st.markdown("---")
col_foot1, col_foot2 = st.columns([1, 4])
with col_foot1:
    st.link_button("📺 YouTube 轉 MP3", "https://yt1s.ai/zh-tw/youtube-to-mp3/")
with col_foot2:
    st.markdown("<div style='padding-top: 5px; color: #7f8c8d; font-size: 16px;'>← 點擊按鈕開啟轉檔網站</div>", unsafe_allow_html=True)