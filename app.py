import streamlit as st
import pandas as pd
import json
import random
import re

# ==========================================
# 1. 資料載入與快取 (提升網頁載入速度)
# ==========================================
@st.cache_data
def load_data():
    try:
        with open('data.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        st.error("找不到 data.json 檔案，請確定檔案存在。")
        return []

data = load_data()

# ==========================================
# 2. 輔助函式
# ==========================================
# 移除字串中的 HTML 標籤 (用於拼寫模式的比對)
def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', str(text))

# 取得選擇題的錯誤選項 (干擾項)
def get_wrong_options(correct_answer, current_feature, num=3):
    all_values = [item.get(current_feature) for item in data if item.get(current_feature)]
    # 過濾掉正確答案與空值
    wrong_values = list(set([remove_html_tags(v) for v in all_values if remove_html_tags(v) != remove_html_tags(correct_answer)]))
    
    # 如果同一個特徵的錯誤選項不夠，隨便抓其他欄位的資料來湊數
    if len(wrong_values) < num:
        fallback_values = [v for item in data for k, v in item.items() if k != "Disease"]
        fallback_values = list(set([remove_html_tags(v) for v in fallback_values if remove_html_tags(v) != remove_html_tags(correct_answer)]))
        wrong_values.extend(fallback_values)
        
    # 回傳隨機挑選的指定數量錯誤選項
    return random.sample(wrong_values, min(num, len(wrong_values)))

# 重新產生題目的狀態重置函式
def generate_new_question(prefix):
    target_item = random.choice(data)
    available_features = [key for key in target_item.keys() if key != "Disease" and target_item[key]]
    question_feature = random.choice(available_features)
    correct_answer = target_item[question_feature]
    
    st.session_state[f'{prefix}_item'] = target_item
    st.session_state[f'{prefix}_feature'] = question_feature
    st.session_state[f'{prefix}_answer'] = correct_answer
    st.session_state[f'{prefix}_show_result'] = False
    
    if prefix == 'mcq':
        wrong_options = get_wrong_options(correct_answer, question_feature)
        all_options = wrong_options + [remove_html_tags(correct_answer)]
        random.shuffle(all_options)
        st.session_state['mcq_options'] = all_options

# ==========================================
# 3. 側邊欄與版面配置
# ==========================================
st.sidebar.title("⚙️ 設定區")
mode = st.sidebar.radio("選擇測驗模式", ["檢視全部模式", "選擇模式", "拼寫模式", "全真模擬考模式"])

st.title("🦠 感染症記憶閃卡系統")
st.markdown("---")

if not data:
    st.stop() # 如果沒有資料就暫停執行

# ==========================================
# 4. 各模式邏輯實作
# ==========================================

# 🟢 檢視全部模式
if mode == "檢視全部模式":
    st.subheader("📋 完整比較表")
    df = pd.DataFrame(data).fillna("")
    # 將欄位名稱為 Disease 的移到第一欄
    if 'Disease' in df.columns:
        cols = ['Disease'] + [col for col in df.columns if col != 'Disease']
        df = df[cols]
    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

# 🔵 選擇模式
elif mode == "選擇模式":
    st.subheader("🎯 選擇模式")
    
    # 初始化 Session State
    if 'mcq_item' not in st.session_state:
        generate_new_question('mcq')
        
    st.markdown(f"請問 **{st.session_state['mcq_item']['Disease']}** 的 **{st.session_state['mcq_feature']}** 是什麼？")
    
    # 顯示選項
    user_choice = st.radio("請選擇正確答案：", st.session_state['mcq_options'], index=None)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("送出答案"):
            st.session_state['mcq_show_result'] = True
    with col2:
        if st.button("下一題"):
            generate_new_question('mcq')
            st.rerun()
            
    if st.session_state.get('mcq_show_result'):
        correct_clean = remove_html_tags(st.session_state['mcq_answer'])
        if user_choice == correct_clean:
            st.success("✅ 答對了！")
            st.markdown(f"**完整解析**：{st.session_state['mcq_answer']}", unsafe_allow_html=True)
        else:
            st.error("❌ 答錯了！")
            st.markdown(f"**正確解答應為**：{st.session_state['mcq_answer']}", unsafe_allow_html=True)

# 🟡 拼寫模式
elif mode == "拼寫模式":
    st.subheader("✍️ 拼寫模式 (注意拼字)")
    
    if 'spell_item' not in st.session_state:
        generate_new_question('spell')
        
    st.markdown(f"請輸入 **{st.session_state['spell_item']['Disease']}** 的 **{st.session_state['spell_feature']}**：")
    
    user_input = st.text_input("你的答案：", key="spell_input")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("檢查答案"):
            st.session_state['spell_show_result'] = True
    with col2:
        if st.button("換下一題"):
            generate_new_question('spell')
            st.rerun()

    if st.session_state.get('spell_show_result'):
        # 將輸入與答案都轉小寫、去頭尾空白、去 HTML 標籤後進行比對
        correct_clean = remove_html_tags(st.session_state['spell_answer']).strip().lower()
        input_clean = user_input.strip().lower()
        
        if input_clean == correct_clean:
            st.success("✅ 完全正確！")
            st.markdown(f"**原始解答**：{st.session_state['spell_answer']}", unsafe_allow_html=True)
        elif input_clean in correct_clean and len(input_clean) > 3:
            st.warning("⚠️ 接近了！(包含部分關鍵字)")
            st.markdown(f"**完整解答**：{st.session_state['spell_answer']}", unsafe_allow_html=True)
        else:
            st.error("❌ 錯誤！")
            st.markdown(f"**正確解答**：{st.session_state['spell_answer']}", unsafe_allow_html=True)

# 🟣 全真模擬考模式
elif mode == "全真模擬考模式":
    st.subheader("📝 全真模擬考 (計分模式)")
    st.info("💡 提示：目前你已經完成了基本的三大模式！模擬考模式可以結合 Session State 來記錄題號 (1~10題) 與總分。")
    st.write("如果你希望進一步開發這個模式，我們可以設定它連續出 10 題混合題型，並在最後一頁產生「錯誤訂正表」。")
