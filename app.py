import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# إعدادات صفحة لوحة التحكم
st.set_page_title_page_config = st.set_page_config(
    page_title="Amazon to Telegram Dashboard",
    page_icon="🛍️",
    layout="centered"
)

st.title("🛍️ لوحة تحكم أفيلييت أمازون وتليجرام")
st.write("أدخل رابط منتج أمازون، وسيقوم النظام بسحب التفاصيل، توليد إعلان بواسطة Gemini، ونشره فوراً على تليجرام.")

# الشريط الجانبي للإعدادات
st.sidebar.header("🔑 إعدادات الربط")
bot_token = st.sidebar.text_input("Telegram Bot Token", type="password")
target_channel = st.sidebar.text_input("Telegram Channel (e.g. @channel)", value="")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password")
aff_tag = st.sidebar.text_input("Amazon Affiliate Tag (e.g. mytag-20)", value="")

# دالة سحب بيانات المنتج من أمازون
def scrape_amazon_product(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US, en;q=0.5"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # استخراج العنوان
        title_element = soup.find(id="productTitle")
        title = title_element.get_text().strip() if title_element else "منتج مميز من أمازون"
        
        # استخراج الصورة الرئيسية
        img_element = soup.find(id="landingImage")
        img_url = ""
        if img_element:
            img_url = img_element.get("data-old-hires") or img_element.get("src")
            
        return title, img_url
    except Exception as e:
        return None, None

# دالة توليد الإعلان بواسطة Gemini
def generate_ad(title, product_link, api_key):
    try:
        genai.configure(api_key=api_key)
        # استخدام الموديل المستقر
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        قم كتابة منشور إعلاني جذاب وقصير ومناسب للنشر على قناة تليجرام لترويج منتج أمازون التالي:
        عنوان المنتج: {title}
        رابط الشراء: {product_link}
        
        اجعل الأسلوب تسويقياً مشجعاً، ضع إيموجيز مناسبة، واختم بطلب الشراء عبر الرابط المرفق.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"خطأ في توليد المحتوى: {str(e)}"

# دالة إرسال الرسالة إلى تليجرام
def send_to_telegram(token, channel, text, img_url):
    try:
        if img_url:
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            payload = {
                "chat_id": channel,
                "photo": img_url,
                "caption": text,
                "parse_mode": "Markdown"
            }
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": channel,
                "text": text,
                "parse_mode": "Markdown"
            }
        
        res = requests.post(url, json=payload)
        return res.json().get("ok", False)
    except Exception as e:
        return False

# واجهة الاستخدام الرئيسية
product_url = st.text_input("🔗 أدخل رابط منتج أمازون:")

if st.button("🚀 سحب وتوليد الإعلان ونشرة"):
    if not product_url:
        st.error("الرجاء إدخال رابط المنتج أولاً!")
    elif not gemini_key:
        st.error("الرجاء إدخال مفتاح Gemini API Key في الشريط الجانبي!")
    else:
        with st.spinner("جاري سحب بيانات المنتج..."):
            title, img_url = scrape_amazon_product(product_url)
            
        if not title:
            st.error("عذراً، لم نتمكن من سحب تفاصيل المنتج. تأكد من صحة الرابط.")
        else:
            st.success(f"تم السحب بنجاح: {title}")
            
            # إضافة كود الأفيلييت للرابط إذا وجد
            final_link = product_url
            if aff_tag:
                if "?" in product_url:
                    final_link = f"{product_url}&tag={aff_tag}"
                else:
                    final_link = f"{product_url}?tag={aff_tag}"
            
            with st.spinner("جاري توليد الإعلان التسويقي عبر Gemini..."):
                ad_text = generate_ad(title, final_link, gemini_key)
                
            st.subheader("📝 الإعلان المولّد:")
            st.markdown(ad_text)
            
            if img_url:
                st.image(img_url, width=300)
                
            # زر النشر الفوري
            if bot_token and target_channel:
                if st.button("📤 نشر الآن في قناة تليجرام"):
                    success = send_to_telegram(bot_token, target_channel, ad_text, img_url)
                    if success:
                        st.success("تم نشر الإعلان في القناة بنجاح! 🎉")
                    else:
                        st.error("فشل النشر، تأكد من صحة Bot Token ومعرف القناة وأن البوت مشرف فيها.")
            else:
                st.info("للنشر التلقائي، قم بإدخال Telegram Bot Token ومعرف القناة في الشريط الجانبي.")
