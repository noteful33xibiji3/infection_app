import streamlit as st
import pandas as pd
import json
import random
import re
import os

# 新增：極度寬鬆的比對過濾器 (只保留英數字並轉小寫)
def clean_for_spelling(text):
    # 先移除 HTML 的紅字標籤
    text = remove_html_tags(text)
    # 移除非英數字元 (包含空格、標點、括號與中文)
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()

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
# 1.5 進度與成就系統載入
# ==========================================
PROGRESS_FILE = 'progress.json'

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 初始成績單
        return {
            "total_answered": 0,
            "total_correct": 0,
            "achievements": []
        }

def save_progress(progress_data):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)

# 載入進度到 Session State，方便全域呼叫
if 'user_progress' not in st.session_state:
    st.session_state['user_progress'] = load_progress()

# 檢查成就解鎖的輔助函式
def check_achievements():
    progress = st.session_state['user_progress']
    achievements = progress["achievements"]
    new_unlock = None
    
    # 設定成就條件與稱號
    if progress["total_correct"] >= 10 and "初出茅廬 (答對 10 題)" not in achievements:
        new_unlock = "初出茅廬 (答對 10 題)"
    elif progress["total_correct"] >= 50 and "藥理小神童 (答對 50 題)" not in achievements:
        new_unlock = "藥理小神童 (答對 50 題)"
    elif progress["total_correct"] >= 100 and "中西醫雙修學霸 (答對 100 題)" not in achievements:
        new_unlock = "中西醫雙修學霸 (答對 100 題)"
        
    if new_unlock:
        progress["achievements"].append(new_unlock)
        save_progress(progress)
        st.balloons() # 觸發 Streamlit 內建的慶祝氣球特效！
        st.success(f"🏆 恭喜解鎖新成就：{new_unlock}！")
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

# 重新產生題目的狀態重置函式 (加入 source_data 參數以支援分類題庫)
# 重新產生題目的狀態重置函式 (支援分類與計分系統)
def generate_new_question(prefix, source_data=None):
    if source_data is None:
        source_data = data
        
    target_item = random.choice(source_data)
    
    # 排除 Disease 和 Category 作為考題
    available_features = [key for key in target_item.keys() if key not in ["Disease", "Category"] and target_item.get(key)]
    
    question_feature = random.choice(available_features)
    correct_answer = target_item[question_feature]
    
    st.session_state[f'{prefix}_item'] = target_item
    st.session_state[f'{prefix}_feature'] = question_feature
    st.session_state[f'{prefix}_answer'] = correct_answer
    st.session_state[f'{prefix}_show_result'] = False
    
    # === 關鍵：換題時，把「已計分」的標記清除 ===
    st.session_state.pop(f'{prefix}_scored', None)
    
    if prefix == 'mcq':
        wrong_options = get_wrong_options(correct_answer, question_feature)
        all_options = wrong_options + [remove_html_tags(correct_answer)]
        random.shuffle(all_options)
        st.session_state['mcq_options'] = all_options
# ==========================================
# 3. 側邊欄與版面配置
# ==========================================
st.sidebar.title("⚙️ 設定區")
mode = st.sidebar.radio("選擇測驗模式", ["檢視全部模式", "卡片瀏覽模式","選擇模式", "拼寫模式", "全真模擬考模式", "新增學習卡", "🏆 個人計分板"])

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
    
    # 🌟 補上這行：動態抓取目前所有的分類，徹底解決 NameError
    all_categories = sorted(list(set([item.get("Category", "未分類") for item in data])))
    
    # 加入分類選單
    selected_category = st.selectbox("請選擇要檢視的分類：", ["全部"] + all_categories, key="view_all_cat")
    
    # 根據選單過濾資料
    filtered_data = [item for item in data if item.get("Category") == selected_category] if selected_category != "全部" else data
    
    # 將過濾後的資料轉換為 DataFrame
    df = pd.DataFrame(filtered_data).fillna("")
    
    # 排列欄位，讓 Disease 和 Category 固定在最前面，方便閱讀
    if not df.empty and 'Disease' in df.columns:
        cols = ['Disease']
        if 'Category' in df.columns:
            cols.append('Category')
        cols += [col for col in df.columns if col not in ['Disease', 'Category']]
        df = df[cols]
        
    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
# 卡片瀏覽邏輯
elif mode == "卡片瀏覽模式":
    st.subheader("🗂️ 學習卡總覽")
    
    # 動態抓取目前所有的分類 (排除沒有分類的項目)
    all_categories = sorted(list(set([item.get("Category", "未分類") for item in data])))
    
    # 建立下拉式選單讓使用者選擇分類
    selected_category = st.selectbox("請選擇要複習的單元：", ["全部"] + all_categories)
    
    st.markdown("---")
    
    # 根據選擇過濾資料
    if selected_category != "全部":
        filtered_data = [item for item in data if item.get("Category") == selected_category]
    else:
        filtered_data = data
        
    # 使用 st.columns 建立雙欄網格排列，讓畫面像鋪滿卡片一樣
    cols = st.columns(2)
    for i, item in enumerate(filtered_data):
        with cols[i % 2]:
            # 使用 container 加上邊框，模擬實體卡片的視覺效果
            with st.container(border=True):
                st.markdown(f"### {item.get('Disease', '未知疾病')}")
                st.caption(f"📂 分類：{item.get('Category', '未分類')}")
                st.divider() # 畫一條分隔線
                
                # 迴圈印出該疾病的所有特徵
                for key, value in item.items():
                    if key not in ["Disease", "Category"]:
                        st.markdown(f"**{key}**: {value}", unsafe_allow_html=True)

# 🔵 選擇模式 (升級版：雙重篩選、不重複輪迴、紅字優先)
elif mode == "選擇模式":
    st.subheader("🎯 選擇模式")
    
    # 1. 第一層篩選：分類
    all_categories = sorted(list(set([item.get("Category", "未分類") for item in data])))
    selected_category = st.selectbox("請選擇要測驗的分類：", ["全部"] + all_categories, key="mcq_cat")
    filtered_data = [item for item in data if item.get("Category") == selected_category] if selected_category != "全部" else data
    
    # 2. 第二層篩選：動態抓取該分類下的所有「特徵/類別」
    all_features = set()
    for item in filtered_data:
        for k in item.keys():
            if k not in ["Disease", "Category"] and item.get(k):
                all_features.add(k)
    selected_feature = st.selectbox("請選擇要測驗的考點類別：", ["全部 (隨機混考)"] + sorted(list(all_features)), key="mcq_feat")

    # 3. 牌組初始化與重置邏輯 (當切換分類或特徵時)
    if ('mcq_deck' not in st.session_state or 
        st.session_state.get('mcq_current_category') != selected_category or 
        st.session_state.get('mcq_current_feature') != selected_feature):
        
        st.session_state['mcq_current_category'] = selected_category
        st.session_state['mcq_current_feature'] = selected_feature
        st.session_state['mcq_deck'] = [] # 清空牌組，迫使下方重新洗牌

    # 4. 洗牌邏輯：牌組空了就重新把所有符合的題目裝進去
    if len(st.session_state.get('mcq_deck', [])) == 0:
        new_deck = []
        for item in filtered_data:
            for k, v in item.items():
                if k not in ["Disease", "Category"] and v:
                    if selected_feature == "全部 (隨機混考)" or k == selected_feature:
                        new_deck.append({"item": item, "feature": k, "answer": v})

        if not new_deck:
            st.warning("此篩選條件下沒有題目！")
        else:
            # 🌟 優先考紅字：將題目分為「有紅字」與「無紅字」兩疊
            red_deck = [q for q in new_deck if "<span style='color:red'>" in str(q["answer"])]
            normal_deck = [q for q in new_deck if "<span style='color:red'>" not in str(q["answer"])]
            
            # 各自打亂後，把紅字牌疊放在最上面
            random.shuffle(red_deck)
            random.shuffle(normal_deck)
            st.session_state['mcq_deck'] = red_deck + normal_deck
            st.toast(f"🔄 題庫已重新洗牌！共 {len(st.session_state['mcq_deck'])} 題 (包含 {len(red_deck)} 題紅字優先考點)。")

    # 5. 抽題與顯示邏輯
    if 'mcq_deck' in st.session_state and len(st.session_state['mcq_deck']) > 0:
        # 如果當前沒有題目 (第一次進來，或按了下一題被清除)
        if 'mcq_item' not in st.session_state:
            current_q = st.session_state['mcq_deck'].pop(0) # 從牌堆頂端抽一張
            st.session_state['mcq_item'] = current_q["item"]
            st.session_state['mcq_feature'] = current_q["feature"]
            st.session_state['mcq_answer'] = current_q["answer"]
            st.session_state['mcq_show_result'] = False
            st.session_state.pop('mcq_scored', None)
            
            # 產生選項
            wrong_options = get_wrong_options(current_q["answer"], current_q["feature"])
            all_options = wrong_options + [remove_html_tags(current_q["answer"])]
            random.shuffle(all_options)
            st.session_state['mcq_options'] = all_options

        # UI 顯示
        remain_count = len(st.session_state['mcq_deck'])
        st.caption(f"📦 題庫剩餘未考題數：{remain_count} 題 (考完將自動重新洗牌)")
        st.markdown(f"請問 **{st.session_state['mcq_item']['Disease']}** 的 **{st.session_state['mcq_feature']}** 是什麼？")
        
        user_choice = st.radio("請選擇正確答案：", st.session_state['mcq_options'], index=None)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("送出答案"):
                st.session_state['mcq_show_result'] = True
        with col2:
            if st.button("下一題"):
                # 刪除當前題目，讓系統下一秒自動觸發重新抽題
                del st.session_state['mcq_item']
                st.rerun()
                
        if st.session_state.get('mcq_show_result'):
            correct_clean = remove_html_tags(st.session_state['mcq_answer'])
            
            if 'mcq_scored' not in st.session_state:
                st.session_state['user_progress']['total_answered'] += 1
                if user_choice == correct_clean:
                    st.session_state['user_progress']['total_correct'] += 1
                save_progress(st.session_state['user_progress'])
                st.session_state['mcq_scored'] = True
                check_achievements()

            if user_choice == correct_clean:
                st.success("✅ 答對了！")
            else:
                st.error("❌ 答錯了！")
            st.markdown(f"**完整解析**：{st.session_state['mcq_answer']}", unsafe_allow_html=True)

# 🟡 拼寫模式
elif mode == "拼寫模式":
    st.subheader("✍️ 拼寫模式 (注意拼字)")
    
    # 動態抓取分類並建立選單
    all_categories = sorted(list(set([item.get("Category", "未分類") for item in data])))
    selected_category = st.selectbox("請選擇要測驗的分類：", ["全部"] + all_categories, key="spell_category_select")
    
    if selected_category != "全部":
        filtered_data = [item for item in data if item.get("Category") == selected_category]
    else:
        filtered_data = data
        
    # 初始化或切換分類時重新抽題
    if 'spell_current_category' not in st.session_state or st.session_state['spell_current_category'] != selected_category:
        st.session_state['spell_current_category'] = selected_category
        generate_new_question('spell', filtered_data)
        
    if 'spell_item' in st.session_state:
        st.markdown(f"請輸入 **{st.session_state['spell_item']['Disease']}** 的 **{st.session_state['spell_feature']}**：")
        
        user_input = st.text_input("你的答案：", key="spell_input")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("檢查答案"):
                st.session_state['spell_show_result'] = True
        with col2:
            if st.button("換下一題"):
                generate_new_question('spell', filtered_data)
                st.rerun()

        if st.session_state.get('spell_show_result'):
            # 使用寬鬆過濾器
            correct_clean = clean_for_spelling(st.session_state['spell_answer'])
            input_clean = clean_for_spelling(user_input)
            
            # === 計分系統整合 ===
            if 'spell_scored' not in st.session_state:
                st.session_state['user_progress']['total_answered'] += 1
                if input_clean == correct_clean and input_clean != "":
                    st.session_state['user_progress']['total_correct'] += 1
                save_progress(st.session_state['user_progress'])
                st.session_state['spell_scored'] = True
                check_achievements()

            # === 判斷對錯與提示 ===
            if input_clean == correct_clean and input_clean != "":
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
    
    # 確保 all_categories 變數有被正確定義 (動態抓取目前所有的分類)
    all_categories = sorted(list(set([item.get("Category", "未分類") for item in data])))
    
    # 1. 選擇考試範圍與題型
    exam_category = st.selectbox("請選擇模擬考範圍：", ["全部 (考所有表格)"] + all_categories, key="exam_category")
    exam_type = st.radio("請選擇測驗方式：", ["配合題 (下拉選單)", "填空題 (打字輸入)"], horizontal=True)

    # 準備過濾後的資料
    if exam_category != "全部 (考所有表格)":
        exam_data = [item for item in data if item.get("Category") == exam_category]
    else:
        exam_data = data

    # 2. 新增：讓使用者選擇題數
    max_q = len(exam_data)
    exam_count_option = st.radio("請選擇測驗題數：", [5, 10, "考全部！"], horizontal=True, key="exam_count_option")
    
    if exam_count_option == "考全部！":
        num_questions = max_q
    else:
        num_questions = min(exam_count_option, max_q)

    # 3. 產生考卷 (加入題數變化作為重新出題的判斷條件)
    if 'exam_questions' not in st.session_state or \
       st.session_state.get('exam_current_cat') != exam_category or \
       st.session_state.get('exam_current_type') != exam_type or \
       st.session_state.get('exam_current_count') != num_questions:
        
        st.session_state['exam_current_cat'] = exam_category
        st.session_state['exam_current_type'] = exam_type
        st.session_state['exam_current_count'] = num_questions
        st.session_state['exam_submitted'] = False
        
        selected_items = random.sample(exam_data, num_questions)
        questions, all_answers = [], []

        for item in selected_items:
            available_features = [k for k in item.keys() if k not in ["Disease", "Category"] and item.get(k)]
            feature = random.choice(available_features)
            ans = item[feature]
            questions.append({"disease": item["Disease"], "feature": feature, "answer": ans})
            all_answers.append(remove_html_tags(ans))

        random.shuffle(all_answers)
        st.session_state['exam_questions'] = questions
        st.session_state['exam_answers_bank'] = all_answers

    # 4. 顯示考卷表單
    with st.form("exam_form"):
        user_answers = []
        for i, q in enumerate(st.session_state['exam_questions']):
            st.markdown(f"**Q{i+1}: 請問 {q['disease']} 的 {q['feature']} 是什麼？**")
            
            if "配合題" in exam_type:
                # 配合題使用下拉選單
                ans = st.selectbox("選擇答案：", ["請選擇..."] + st.session_state['exam_answers_bank'], key=f"exam_q_{i}")
            else:
                # 填空題使用文字輸入框
                ans = st.text_input("輸入答案 (英文字母對即可)：", key=f"exam_q_{i}")
                
            user_answers.append(ans)
            st.divider()

        submit_exam = st.form_submit_button("交卷看成績")

    # 5. 批改與成績計算
    if submit_exam:
        st.session_state['exam_submitted'] = True
        score = 0
        st.subheader("📊 考試結果與訂正")
        
        for i, q in enumerate(st.session_state['exam_questions']):
            correct_ans = q['answer']
            user_ans = user_answers[i]

            if user_ans == "請選擇..." or user_ans.strip() == "":
                st.error(f"Q{i+1}: ❌ 未作答。\n\n正確解答：{correct_ans}")
                continue

            if clean_for_spelling(user_ans) == clean_for_spelling(correct_ans):
                score += 1
                st.success(f"Q{i+1}: ✅ 答對了！ ({remove_html_tags(correct_ans)})")
            else:
                st.error(f"Q{i+1}: ❌ 答錯了。\n\n正確解答：{correct_ans} \n\n你的作答：{user_ans}")

        total_q = len(st.session_state['exam_questions'])
        st.metric(label="總分", value=f"{int((score/total_q)*100)} 分", delta=f"{score} / {total_q} 題")
        
        # 紀錄分數到計分板
        st.session_state['user_progress']['total_answered'] += total_q
        st.session_state['user_progress']['total_correct'] += score
        save_progress(st.session_state['user_progress'])
        check_achievements()
        
        # 重新測驗按鈕
        if st.button("再考一次"):
            del st.session_state['exam_questions']
            st.rerun()
# 🟢 新增學習卡模式
elif mode == "新增學習卡":
    st.subheader("➕ 新增學習卡")
    st.write("在這裡輸入新的疾病與特徵，擴充你的題庫！")

    # 使用表單來收集輸入
    with st.form("add_card_form"):
        new_disease = st.text_input("疾病名稱 (必填，例如：Tuberculosis (結核病))")
        new_agent = st.text_input("致病菌 (Causative Agent)")
        new_treatment = st.text_input("抗生素治療 (Antibiotic Treatment)")
        new_symptoms = st.text_area("主要症狀 (Primary Symptoms)")

        # 提交按鈕
        submitted = st.form_submit_button("新增至題庫")

        if submitted:
            if new_disease.strip() == "":
                st.error("疾病名稱不能為空！")
            else:
                # 建立新的字典，只加入有填寫的欄位
                new_entry = {"Disease": new_disease}
                if new_agent: new_entry["Causative Agent"] = new_agent
                if new_treatment: new_entry["Antibiotic Treatment"] = new_treatment
                if new_symptoms: new_entry["Primary Symptoms"] = new_symptoms

                # 將新資料加入原本的 list
                data.append(new_entry)

                # 將更新後的資料寫回 JSON 檔案
                with open('data.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                st.success(f"成功新增：{new_disease}！")
                # 清除快取以載入新資料
                st.cache_data.clear()
# 🟢 個人計分板模式
elif mode == "🏆 個人計分板":
    st.subheader("🏆 個人戰力分析")
    progress = st.session_state['user_progress']
    
    # 計算正確率
    total = progress['total_answered']
    correct = progress['total_correct']
    accuracy = (correct / total * 100) if total > 0 else 0
    
    # 使用 metric 顯示漂亮的大數字
    col1, col2, col3 = st.columns(3)
    col1.metric("總答題數", f"{total} 題")
    col2.metric("正確題數", f"{correct} 題")
    col3.metric("整體正確率", f"{accuracy:.1f} %")
    
    st.markdown("---")
    st.subheader("🎖️ 已解鎖成就")
    if progress['achievements']:
        for ach in progress['achievements']:
            st.markdown(f"- 🌟 **{ach}**")
    else:
        st.info("目前還沒有解鎖成就，快去「選擇模式」或「模擬考」刷題吧！")
        
    st.markdown("---")
    # 匯出資料的按鈕功能
    st.write("📊 **資料匯出**")
    csv_data = f"Total Answered,Total Correct,Accuracy\n{total},{correct},{accuracy:.1f}%\n"
    st.download_button(
        label="📥 下載進度 (CSV)",
        data=csv_data,
        file_name='my_study_progress.csv',
        mime='text/csv',
    )

