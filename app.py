import os
import requests
import streamlit as st
from bs4 import BeautifulSoup
from google import genai

# إعداد واجهة Streamlit
st.set_page_config(page_title="لوحة نشر عروض أمازون", page_icon="🛍️", layout="centered")
st.title("🛍️ لوحة التحكم في عروض أمازون وتليجرام")

# المتغيرات الأساسية (يمكن قراءتها من البيئة أو إدخالها في الشريط الجانبي)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "")

# شريط إعدادات جانبي لتأكيد البيانات
with st.sidebar:
    st.header("⚙️ الإعدادات")
    bot_token = st.text_input("Bot Token", value=BOT_TOKEN, type="password")
    target_channel = st.text_input("معرف القناة (مثال: @mychannel)", value=TARGET_CHANNEL)
    gemini_key = st.text_input("Gemini API Key", value=GEMINI_API_KEY, type="password")
    aff_tag = st.text_input("Affiliate Tag", value=AFFILIATE_TAG)

def get_amazon_details(url_or_asin):
    """سحب البيانات من أمازون"""
    if "http" in url_or_asin:
        url = url_or_asin
    else:
        url = f"https://www.amazon.eg/dp/{url_or_asin}"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None, None
        soup = BeautifulSoup(res.text, 'html.parser')
        
        title_elem = soup.find(id='productTitle')
        title = title_elem.get_text(strip=True) if title_elem else "منتج ممتاز من أمازون"
        
        img_elem = soup.find(id='landingImage') or soup.find('img', {'class': 'a-dynamic-image'})
        img_url = img_elem.get('src') if img_elem else None
        
        return title, img_url
    except Exception as e:
        return None, None

def generate_ad(title, link, api_key):
    """توليد الإعلان عبر Gemini"""
    client = genai.Client(api_key=api_key)
    prompt = f"""
    اكتب منشور إعلاني تسويقي جذاب وقصير لقناة تليجرام تسويق بالعمولة.
    المنتج: {title}
    رابط الشراء: {link}
    
    شروط المنشور:
    - عنوان قوي يشد الانتباه.
    - نقاط مختصرة مع إيموجي ممتازة.
    - دعوة لشراء المنتج قبل نفاد الكمية.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def send_to_telegram(token, channel, text, image_url):
    """إرسال الصورة والنص لقناة تليجرام"""
    api_url = f"https://api.telegram.org/bot{token}/sendPhoto"
    payload = {
        "chat_id": channel,
        "caption": text,
        "photo": image_url,
        "parse_mode": "Markdown"
    }
    res = requests.post(api_url, data=payload)
    return res.json()

# واجهة المدخلات
product_input = st.text_input("أدخل رابط المنتج أو كود (ASIN):", placeholder="https://www.amazon.eg/dp/B0...")

if st.button("🔍 سحب وتوليد الإعلان", type="primary"):
    if not product_input:
        st.warning("رجاءً أدخل الرابط أولاً.")
    else:
        with st.spinner("جاري جلب البيانات وتوليد الإعلان..."):
            title, img_url = get_amazon_details(product_input)
            
            if not title:
                st.error("مقدرتش أسحب بيانات المنتج. تأكد من صحة الرابط.")
            else:
                # تجهيز رابط الأفلييت
                aff_link = f"{product_input}?tag={aff_tag}" if "tag=" not in product_input else product_input
                
                # توليد النص
                ad_text = generate_ad(title, aff_link, gemini_key)
                
                st.session_state['ad_text'] = ad_text
                st.session_state['img_url'] = img_url
                st.session_state['aff_link'] = aff_link

# عرض المعاينة والنشر
if 'ad_text' in st.session_state:
    st.subheader("🖼️ معاينة المنشور")
    if st.session_state['img_url']:
        st.image(st.session_state['img_url'], width=300)
    
    edited_text = st.text_area("تعديل نص الإعلان قبل النشر:", value=st.session_state['ad_text'], height=200)
    
    if st.button("🚀 نشر فوراً في قناة تليجرام"):
        with st.spinner("جاري النشر..."):
            res = send_to_telegram(bot_token, target_channel, edited_text, st.session_state['img_url'])
            if res.get("ok"):
                st.success("تم النشر في القناة بنجاح! 🎉")
            else:
                st.error(f"فشل النشر: {res.get('description')}")
