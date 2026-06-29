import streamlit as st
import openai
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import json
import os

# ==========================================
# 五、UI修改：網頁基本配置與卡片風格設定
# ==========================================
st.set_page_config(page_title="急難紓困 AI 智慧審核系統 V2", layout="wide")

# CSS 注入：美化卡片介面與標題
# 替換成這段全新、相容性更好的寫法：
st.html("""
<style>
    .reportview-container .main .block-container { padding-top: 2rem; }
    .card-title { font-size: 1.2rem; font-weight: bold; margin-bottom: 0.5rem; }
</style>
""")

st.title("🛡️ 強化社會安全網－急難紓困 AI 輔助審核系統 V2")
st.caption("⚖️ 專業版（本系統僅提供分析與建議，不具行政處分效力，最終仍由承辦人審核決定）")
st.markdown("---")

# ==========================================
# 三、JSON Schema 修改 (Pydantic 結構重新設計)
# ==========================================
class FamilyMember(BaseModel):
    name: str = Field(description="姓名，若未知填資料不足")
    relationship: str = Field(description="與案主關係")
    age: str = Field(description="年齡，未知填資料不足")
    is_living_together: str = Field(description="是否共同生活，填 是/否/待查證")
    is_working: str = Field(description="是否工作，填 是/否/待查證")
    income: str = Field(description="收入狀況，有固定收入/無收入/臨時工/資料不足")

class BasicInformation(BaseModel):
    case_source: str = Field(description="通報來源或通報人姓名")
    applicant_name: str = Field(description="個案/案主姓名")
    id_number: str = Field(description="身分證字號")
    address: str = Field(description="戶籍或通訊地址")
    phone: str = Field(description="聯絡電話")
    visit_date: str = Field(description="訪視日期，未知填資料不足")

class EmergencyAssessment(BaseModel):
    category_number: str = Field(description="對應手冊中急難事由大類編號（如：第3類）")
    category_name: str = Field(description="急難事由名稱（如：罹患重傷病）")
    matched_conditions: List[str] = Field(description="具體符合的條件清單")
    emergency_description: str = Field(description="急難事實摘要描述")
    hospitalized: str = Field(description="是否住院，填 是/否/資料不足")
    unable_to_work: str = Field(description="是否無法工作，填 是/否/資料不足")
    estimated_rest_days: str = Field(description="預估休養天數或週數，未知填資料不足")
    main_breadwinner: str = Field(description="是否為主要家計負責人，填 是/否/待查證")
    income_interruption: str = Field(description="收入是否中斷，填 是/否/資料不足")
    income_loss_reason: str = Field(description="收入中斷原因摘要")
    emergency_verified: str = Field(description="急難事實是否已獲初步驗證，填 是/否/待查證")
    verification_reason: str = Field(description="事實驗證或需再查證之理由")

class HouseholdAssessment(BaseModel):
    living_together_count: str = Field(description="共同生活人口數，未知填資料不足")
    working_population_count: str = Field(description="工作人口數，未知填資料不足")
    dependent_population_count: str = Field(description="扶養人口數，未知填資料不足")
    family_members: List[FamilyMember] = Field(description="家庭成員詳細清單")

class FinancialAssessment(BaseModel):
    total_household_income: str = Field(description="家庭總收入，未知填資料不足")
    average_per_capita_income: str = Field(description="每人每月平均所得，未知填資料不足")
    total_savings: str = Field(description="存款總額，未知填資料不足")
    income_source_analysis: Dict[str, str] = Field(description="各項收入來源分析，包含：薪資、臨時工、農業、老人津貼、身障津貼、保險理賠、家屬扶養、其他。若無則填 0 或無，未知填資料不足")
    is_income_interrupted: str = Field(description="收入是否中斷，填 是/否/資料不足")
    interruption_reason: str = Field(description="收入中斷原因")
    estimated_interruption_duration: str = Field(description="預估收入中斷多久，未知填資料不足")

class DocumentAssessment(BaseModel):
    provided_documents: List[str] = Field(description="已提供之文件清單")
    missing_documents: List[str] = Field(description="缺漏之文件清單")
    required_patches: List[str] = Field(description="後續需要補件之項目")
    can_approve_first: str = Field(description="依手冊是否可先行核定再補件，填 是/否/待查證")

class EligibilityAssessment(BaseModel):
    is_eligible: str = Field(description="是否符合急難紓困資格，填 符合/不符合/資料不足待查")
    eligible_reasons: List[str] = Field(description="符合之具體原因與條款依據")
    ineligible_reasons: List[str] = Field(description="不符合之具體原因，若符合則填無")
    is_urgent: str = Field(description="情況是否緊急，填 是/否/待查證")
    needs_immediate_assistance: str = Field(description="是否立即需要協助，填 是/否/待查證")
    is_fast_track_compliant: str = Field(description="是否符合速訪速評速發原則，填 是/否/待查證")
    ai_confidence_score: int = Field(description="AI 信心分數 (0~100)")

class Recommendation(BaseModel):
    recommended_amount: str = Field(description="建議補助金額（填具體數字如 20000，或資料不足無法評估）")
    recommendation_reason: List[str] = Field(description="核定金額之依據與詳細原因理由")
    payment_method: str = Field(description="發給方式（如：一次性發給、實物救助等）")
    follow_up_referrals: List[str] = Field(description="後續轉介單位或中長期補助項目")

class OfficerOpinion(BaseModel):
    ai_generated_opinion: str = Field(description="公文語氣承辦人意見，可供直接複製簽辦。範例：『案主因重大疾病住院治療，經醫師診斷需休養二個月以上，期間無法工作且收入中斷，家庭生活陷困，符合急難紓困第3類規定，建議核予急難紓困金新臺幣2萬元。』")

class ScreeningResultV2(BaseModel):
    ai_summary_status: str = Field(description="AI 總體狀態摘要標籤，限填: '符合'、'不符合'、'資料不足'")
    ai_summary_details: List[str] = Field(description="高精簡的核心摘要要點（如：符合第3類、主要家計者、休養二個月、收入中斷、建議補助20000元）")
    basic_information: BasicInformation
    emergency_assessment: EmergencyAssessment
    household_assessment: HouseholdAssessment
    financial_assessment: FinancialAssessment
    document_assessment: DocumentAssessment
    eligibility_assessment: EligibilityAssessment
    recommendation: Recommendation
    officer_opinion: OfficerOpinion

# ==========================================
# 🔑 API 金鑰設定
# ==========================================
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("請輸入 Groq API Key (gsk_...)", type="password")

# 前端輸入區
raw_text = st.text_area(
    "📝 請輸入民眾主述、通報內容或訪視紀錄：", 
    placeholder="請在此輸入詳細個案陳述...",
    height=200
)

# ==========================================
# 🚀 啟動 AI Agent 工作流
# ==========================================
if st.button("🔍 執行 V2 專業輔助評估", type="primary"):
    if not api_key:
        st.error("❌ 未偵測到 API Key！請在雲端設定環境變數 GROQ_API_KEY 或於左側輸入。")
    elif not raw_text.strip():
        st.warning("⚠️ 請先輸入個案主述內容。")
    else:
        with st.spinner("⏳ 正在依據急難紓困作業手冊進行高嚴謹度比對與公文意見生成..."):
            try:
                client = openai.OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=api_key
                )
                
                # ==========================================
                # 四、Prompt 重新設計 (嚴格限制推論與幻想)
                # ==========================================
                system_prompt = """
您是專為台灣政府內政與社政體系設計的「急難紓困 AI 智慧審核輔助 Agent」。
您的任務是協助承辦人審閱個案陳述，並對照《強化社會安全網－急難紓困實施方案作業手冊》進行結構化分析。

【最核心指導原則】
1. 恪守輔助角色：AI僅提供分析與建議，最終仍由承辦人決定，不得自行作成行政處分。
2. 絕對禁止猜測、幻想或自行推論事實：如果個案陳述中沒有提及某項事實（例如沒寫存款多少、沒寫休養幾天、沒寫是否住在一起），在該欄位必須填寫 "資料不足"、"未知" 或 "待查證"。
3. 判斷必須附帶理由：所有關於符合/不符合、補助金額大小、事實驗證的判斷，都必須在對應的 reason 欄位中提供嚴格依據。

【業務認定基準】
- 急難紓困七大事由：
  - 第1類：死亡。
  - 第2類：失蹤。
  - 第3類：罹患重傷病（需休養1個月以上且無法工作）。
  - 第4類：失業。
  - 第5類：其他原因無法工作。
  - 第6類：其他因非自願失業等原因生活陷困。
  - 第7類：經通報疑似脆弱家庭。
- 家計計算原則：存款以每人平均不超過15萬元為原則，且計算人口僅限「實際共同生活者」。
- 核心精神：速訪、速評、速發（核發金額範圍通常在 10,000 ~ 30,000 元）。

【輸出格式要求】
- 必須完全以繁體中文回答。
- 必須嚴格遵循 JSON Schema 格式。
- 絕對不得輸出 Schema 定義以外的任何自訂欄位。
"""

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"請嚴格分析以下個案，若有未提及的資訊一律填寫'資料不足'或'待查證'，並依 JSON 格式輸出：\n{raw_text}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0  # 設為 0.0 最大程度杜絕 AI 隨機發揮與幻想
                )
                
                # 解析並驗證 JSON
                raw_json = response.choices[0].message.content
                result = ScreeningResultV2.model_validate_json(raw_json)
                
                # ==========================================
                # 七、AI 分析摘要 (最上方新增)
                # ==========================================
                st.markdown("### 📊 AI 輔助分析摘要")
                summary_status = result.ai_summary_status
                summary_details_text = " ｜ ".join(result.ai_summary_details)
                
                if summary_status == "符合":
                    st.success(f"【符合】{summary_details_text}")
                elif summary_status == "不符合":
                    st.error(f"【不符合】{summary_details_text}")
                else:
                    st.warning(f"【資料不足/待查證】{summary_details_text}")
                
                st.markdown("---")
                
                # 開始渲染各個區塊卡片
                # ==========================================
                # 五、UI修改：① 基本資料 (藍色系 info)
                # ==========================================
                st.markdown("### 🟦 ① 基本資料")
                with st.container():
                    bi = result.basic_information
                    # 檢查基本資料中是否有資料不足，進行黃色提醒
                    if "資料不足" in [bi.applicant_name, bi.id_number, bi.address, bi.phone, bi.visit_date]:
                        st.warning("⚠️ 提示：基本資料中有部分項目尚屬【資料不足】，請承辦人核對時留意補正。")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**案主姓名：** {bi.applicant_name}")
                    c1.markdown(f"**身分證字號：** {bi.id_number}")
                    c2.markdown(f"**通報來源：** {bi.case_source}")
                    c2.markdown(f"**聯絡電話：** {bi.phone}")
                    c3.markdown(f"**通訊地址：** {bi.address}")
                    c3.markdown(f"**訪視日期：** {bi.visit_date}")
                st.markdown("---")
                
                # ==========================================
                # 五、UI修改：② 急難認定
                # ==========================================
                st.markdown("### 🟪 ② 急難事由認定")
                with st.container():
                    ea = result.emergency_assessment
                    col_ea1, col_ea2 = st.columns([1, 2])
                    with col_ea1:
                        st.info(f"**法定事由：** {ea.category_number} - {ea.category_name}")
                        st.markdown(f"**主要家計負責人：** {ea.main_breadwinner}")
                        st.markdown(f"**是否住院治療：** {ea.hospitalized}")
                        st.markdown(f"**目前無法工作：** {ea.unable_to_work}")
                        st.markdown(f"**預估休養時間：** {ea.estimated_rest_days}")
                    with col_ea2:
                        st.markdown(f"**急難事實摘要：**\n> {ea.emergency_description}")
                        st.markdown(f"**符合條件明細：** {', '.join(ea.matched_conditions) if ea.matched_conditions else '無'}")
                        
                        # (二) AI不得自行猜測：針對驗證進行黃色提醒
                        if ea.emergency_verified == "待查證" or ea.emergency_verified == "資料不足":
                            st.warning(f"🔍 **事實查證狀態：【{ea.emergency_verified}】** — 原因：{ea.verification_reason}")
                        else:
                            st.success(f"✨ **事實查證狀態：【{ea.emergency_verified}】** — 原因：{ea.verification_reason}")
                st.markdown("---")
                
                # ==========================================
                # 五、UI修改：③ 家庭狀況
                # ==========================================
                st.markdown("### 🟩 ③ 實際共同生活家庭狀況")
                with st.container():
                    ha = result.household_assessment
                    st.markdown(f"**實際共同生活人口：** {ha.living_together_count} 人 ｜ **工作人口：** {ha.working_population_count} 人 ｜ **扶養人口：** {ha.dependent_population_count} 人")
                    
                    # 建立成員表格
                    member_data = []
                    for m in ha.family_members:
                        member_data.append({
                            "姓名": m.name,
                            "關係": m.relationship,
                            "年齡": m.age,
                            "實際共同生活": m.is_living_together,
                            "是否工作": m.is_working,
                            "所得收入狀況": m.income
                        })
                    st.table(member_data)
                st.markdown("---")
                
                # ==========================================
                # 五、UI修改：④ 財務分析
                # ==========================================
                st.markdown("### 🟫 ④ 經濟與財務評估")
                with st.container():
                    fa = result.financial_assessment
                    col_fa1, col_fa2 = st.columns([1, 2])
                    with col_fa1:
                        st.markdown(f"**家庭總收入：** {fa.total_household_income}")
                        st.markdown(f"**每人每月平均所得：** {fa.average_per_capita_income}")
                        st.markdown(f"**家庭存款總額：** {fa.total_savings}")
                        st.markdown(f"**收入中斷狀態：** {fa.is_income_interrupted} (預估持續：{fa.estimated_interruption_duration})")
                    with col_fa2:
                        st.markdown("**💸 收入來源細項分析：**")
                        for source, value in fa.income_source_analysis.items():
                            st.markdown(f"- **{source}：** {value}")
                st.markdown("---")
                
                # ==========================================
                # 五、UI修改：⑤ 補件提醒 (黃色區塊)
                # ==========================================
                st.markdown("### 🟨 ⑤ 證明文件與補件提醒")
                with st.container():
                    da = result.document_assessment
                    st.markdown(f"**📄 已檢附文件：** {', '.join(da.provided_documents) if da.provided_documents else '無'}")
                    
                    if da.missing_documents or da.required_patches:
                        st.warning(f"⚠️ **缺漏文件：** {', '.join(da.missing_documents) if da.missing_documents else '無'}\n\n"
                                   f"👉 **後續需補件項目：** {', '.join(da.required_patches) if da.required_patches else '無'}")
                    else:
                        st.success("✅ 應備證明文件齊全。")
                        
                    st.markdown(f"**💡 是否符合手冊「得先行核定，事後補件」之急迫情況：** {da.can_approve_first}")
                st.markdown("---")
                
                # ==========================================
                # 五、UI修改：⑥ 資格判定 & ⑦ 建議金額 (核心判定與理由)
                # ==========================================
                st.markdown("### ⚖️ ⑥ 資格判定 與 ⑦ 建議救助金額")
                with st.container():
                    ela = result.eligibility_assessment
                    rec = result.recommendation
                    
                    col_el1, col_el2 = st.columns(2)
                    with col_el1:
                        # 六、新增提醒颜色
                        if ela.is_eligible == "符合":
                            st.success(f"### 🎯 資格審查結果：【{ela.is_eligible}】")
                        elif ela.is_eligible == "不符合":
                            st.error(f"### ❌ 資格審查結果：【{ela.is_eligible}】")
                        else:
                            st.warning(f"### 🔍 資格審查結果：【{ela.is_eligible}】")
                            
                        st.markdown(f"**符合資格原因/手冊法源：**")
                        for r in ela.eligible_reasons: st.markdown(f"- {r}")
                        if ela.ineligible_reasons and ela.ineligible_reasons != ["無"]:
                            st.markdown(f"**不符合原因說明：**")
                            for ir in ela.ineligible_reasons: st.markdown(f"- {ir}")
                            
                        st.markdown(f"**AI 判定信心分數：** `{ela.ai_confidence_score}%`")
                        
                    with col_el2:
                        st.metric(label="💵 建議核發紓困金額 (新臺幣)", value=f"{rec.recommended_amount} 元", delta="核定建議")
                        st.markdown("**(三) 金額推論原因與理由依據：**")
                        for reason in rec.recommendation_reason:
                            st.markdown(f"- {reason}")
                        st.markdown(f"**撥款發給方式：** {rec.payment_method}")
                        st.markdown(f"**🔄 社會安全網轉介或中長期救助建議：** {', '.join(rec.follow_up_referrals) if rec.follow_up_referrals else '無'}")
                st.markdown("---")
                
                # ==========================================
                # 五、UI修改：⑧ 承辦人審核意見 (公文語氣)
                # ==========================================
                st.markdown("### 🖋️ ⑧ 承辦人擬辦意見（公文簽辦參考）")
                with st.container():
                    st.info("💡 以下內容採用機關公文簽辦語氣生成，承辦人可評估修改後直接複製貼上至公文系統：")
                    st.code(result.officer_opinion.ai_generated_opinion, language="text")

            # ==========================================
            # 八、錯誤處理：JSON 解析失敗時
            # ==========================================
            except Exception as e:
                st.error("❌ 系統發生錯誤或 JSON 格式解析失敗！")
                st.warning("⚠️ 訊息提示：AI 回傳的資料無法完全對齊 V2 專業版嚴格的結構規範。請檢查下方原始 JSON 資料進行除錯。")
                if 'response' in locals():
                    st.markdown("### 📄 AI 原始回傳 JSON 內容：")
                    st.code(response.choices[0].message.content, language="json")
                st.exception(e)
