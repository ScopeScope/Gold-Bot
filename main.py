import os
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from datetime import datetime
import pytz
import random
import re

# استدعاء المفاتيح السرية من جيت هاب
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

# معرف القناة بتاعتك على تليجرام
TELEGRAM_CHAT_ID = "@LahzaBLahzaGold" 

client = genai.Client(api_key=GEMINI_API_KEY)

def get_egypt_time():
    tz = pytz.timezone('Africa/Cairo')
    now = datetime.now(tz)
    time_str = now.strftime("%I:%M %p").replace("AM", "صباحاً").replace("PM", "مساءً")
    date_str = now.strftime("%Y-%m-%d")
    return f"الساعة {time_str} يوم {date_str}"

def clean_price(text):
    num_str = re.sub(r'[^\d.]', '', text)
    return num_str if num_str else "غير متاح"

def get_prices():
    gold_24, gold_21, gold_18, gold_coin, gold_ounce = "غير متاح", "غير متاح", "غير متاح", "غير متاح", "غير متاح"
    usd_sagh, usd_bank = "غير متاح", "غير متاح"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    try:
        url = "https://www.gold-price-today.com/egypt/"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for row in soup.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                name = cells[0].get_text(strip=True)
                val_text = cells[1].get_text(strip=True)
                
                if 'عيار 24' in name and gold_24 == "غير متاح":
                    gold_24 = clean_price(val_text)
                elif 'عيار 21' in name and gold_21 == "غير متاح":
                    gold_21 = clean_price(val_text)
                elif 'عيار 18' in name and gold_18 == "غير متاح":
                    gold_18 = clean_price(val_text)
                elif 'الجنيه الذهب' in name and gold_coin == "غير متاح":
                    gold_coin = clean_price(val_text)
                elif 'الأونصة بالجنيه' in name and gold_ounce == "غير متاح":
                    gold_ounce = clean_price(val_text)
                elif 'دولار الصاغة' in name:
                    numbers = re.findall(r'\d+\.\d+|\d+', val_text)
                    if len(numbers) >= 2:
                        usd_sagh = numbers[0]
                        usd_bank = numbers[1]
                    elif len(numbers) == 1:
                        usd_sagh = numbers[0]

    except Exception as e:
        print(f"❌ خطأ في سحب الأسعار: {e}")

    return gold_24, gold_21, gold_18, gold_coin, gold_ounce, usd_sagh, usd_bank

def generate_advice(gold_21, usd_sagh, usd_bank):
    prompt = f"""
    سعر جرام الذهب عيار 21 اليوم هو {gold_21} جنيه. 
    سعر دولار الصاغة المحسوب هو {usd_sagh} جنيه، وسعر الدولار الرسمي في البنك هو {usd_bank} جنيه.
    
    أنت مستشار مالي روبوت. المطلوب:
    اكتب نصيحة مباشرة وقصيرة جداً (سطرين كحد أقصى) للمستثمرين.
    
    قواعد هامة جداً لعدم تضليل المتابعين:
    1. لا تنصح بالشراء أو البيع المباشر (لأنك لا تملك بيانات الأسعار السابقة لتعرف هل الاتجاه صاعد أم هابط).
    2. بدلاً من ذلك، قدم نصيحة مبنية على "إدارة المخاطر" (مثل تقسيم السيولة، مراقبة الفجوة بين دولار الصاغة والبنك).
    3. يجب أن تبدأ إجابتك نصاً بكلمة: "💡 النصيحة الآن:"
    4. اكتب بلهجة مصرية احترافية ومفهومة وبدون أي مقدمات.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )
        advice = response.text.strip().replace('"', '').replace('**', '')
        advice = advice.replace("💡 النصيحة الآن:\n", "💡 النصيحة الآن: ")
        return advice
    except Exception as e:
        backup_advices = [
            "💡 النصيحة الآن: السوق في حالة ترقب، يُفضل دايماً تقسيم مبلغ الشراء على أجزاء وعدم الدخول بكل السيولة دفعة واحدة.",
            "💡 النصيحة الآن: احتفظ بجزء من السيولة وراقب الفجوة بين دولار الصاغة ودولار البنك لتحديد أنسب وقت للشراء."
        ]
        return random.choice(backup_advices)

def send_to_telegram(message):
    if not TELEGRAM_TOKEN:
        print("❌ توكن تليجرام غير موجود!")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ تم النشر على تليجرام بنجاح!")
        else:
            print(f"❌ فشل النشر على تليجرام: {response.text}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال بتليجرام: {e}")

def send_to_facebook(message):
    if not FB_ACCESS_TOKEN or not FB_PAGE_ID:
        print("❌ بيانات الفيسبوك غير مكتملة!")
        return

    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
    payload = {"message": message, "access_token": FB_ACCESS_TOKEN}
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ تم النشر على فيسبوك بنجاح!")
        else:
            print(f"❌ فشل النشر على فيسبوك: {response.text}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال بفيسبوك: {e}")

if __name__ == "__main__":
    gold_24, gold_21, gold_18, gold_coin, gold_ounce, usd_sagh, usd_bank = get_prices()
    advice = generate_advice(gold_21, usd_sagh, usd_bank)
    current_time = get_egypt_time()
    
    post = f"""
الآن 🔴
تحديث الأسعار ({current_time}):

🟡 عيار 24: {gold_24} جنيه
🟡 عيار 21: {gold_21} جنيه
🟡 عيار 18: {gold_18} جنيه
🪙 الجنيه الذهب: {gold_coin} جنيه
🥇 أوقية الذهب: {gold_ounce} جنيه

💵 دولار الصاغة: {usd_sagh} جنيه
🏦 دولار البنك: {usd_bank} جنيه

{advice}
    """
    
    final_post = post.strip()
    print(final_post)
    
    # تنفيذ النشر
    send_to_telegram(final_post)
    send_to_facebook(final_post)
