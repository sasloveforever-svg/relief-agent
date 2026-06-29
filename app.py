import streamlit as st
import openai  # Groq 相容 OpenAI 的套件，所以不用換 import
from pydantic import BaseModel, Field
from typing import List
import json
import os

# 1. 網頁基本配置
st.set_page_config(page_title="急難紓困 AI 智慧審核系統(Groq版)", layout="wide")
st.title(" 強化社會安全網－急難紓困 AI 輔助審核系統")
st.caption("依據官方作業手冊設計（採用 Groq 免費高速 Llama 3.3 模型）")
st.markdown("---")

# 2. 定義 JSON 結構化輸出格式 (JSON Schema)
class ApplicationInfo(BaseModel):
    case_source: str = Field(description="通報來源或通報人姓名")
    applicant_name: str = Field(description="個案/案主姓名")
    id_number: str = Field(description="身分證字號")
    address: str = Field(description="戶籍或通訊地址")

class EmergencyAssessment(BaseModel):
    category: str = Field(description="對應手冊中 7 大類事由")
    description: str = Field(description="急難事實摘要")
    is_main_breadwinner: bool = Field(description="是否為主要家計負責人")
    proof_documents: List[str] = Field(description="應具備或後補之證明文件清單")

class FinancialStatus(BaseModel):
    household_size: int = Field(description="實際共同生活人口數")
    monthly_total_income: float = Field(description="全家人口每月總收入")
    per_capita_income: float = Field(description="每人每月平均所得")
    total_savings: float = Field(description="存款總額")
    is_eligible_by_poverty_line: bool = Field(description="每人每月所得是否未達最低生活費1.5倍")

class ActionResult(BaseModel):
    approved_amount: int = Field(description="核定救助金額 (10000 至 30000 元)")
    payment_method: str = Field(description="發給方式（如：一次性發給）")
    referrals: List[str] = Field(description="後續轉介單位或補助項目")

class SafetyNetAlert(BaseModel):
    is_vulnerable_family: bool = Field(description="是否疑似保護性或脆弱家庭")
    ecare_notified: bool = Field(description="是否須通報關懷e起來")

class ScreeningResult(BaseModel):
    application_info: ApplicationInfo
    emergency_assessment: EmergencyAssessment
    financial_status: FinancialStatus
    action_result: ActionResult
    safety_net_alert: SafetyNetAlert

# 3. 安全取得 Groq API Key (優先從雲端環境變數讀取)
api_key = os.getenv("GROQ_API_KEY")

# 若環境變數沒有，則在網頁左側提供手動輸入框
if not api_key:
    api_key = st.sidebar.text_input("請輸入 Groq API Key (gsk_...)", type="password")

# 4. 前端網頁輸入介面
raw_text = st.text_area(
    "👉 請輸入個案主述或訪視紀錄內容：", 
    placeholder="【範例】通報人為里長，案主王美，身分證A200000000。案主因左腳跟骨骨折須休養6週無法工作。案主為主要家計負責人，家裡只有她一人，本月收入0元，存款剩5000元...",
    height=250
)

# 5. 按鈕觸發 AI Agent 工作流
if st.button("🚀 啟動 AI 智慧審核評估", type="primary"):
    if not api_key:
        st.error("❌ 系統未偵測到 API Key！請在雲端設定環境變數或於左側選單輸入。")
    elif not raw_text.strip():
        st.warning("⚠️ 請先輸入個案主述內容。")
    else:
        with st.spinner("⏳ Agent 正在分析 7 大事由、計算家庭所得、比對認定基準中..."):
            try:
                # 指向 Groq 的伺服器網址
                client = openai.OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=api_key
                )
                
                # 提供嚴格的 JSON 範本供 Llama 模型參考，避免發明新欄位
                json_template = """
{
  "application_info": {
    "case_source": "通報來源或姓名",
    "applicant_name": "案主姓名",
    "id_number": "身分證字號",
    "address": "地址"
  },
  "emergency_assessment": {
    "category": "第3類：罹患重傷病(或其他大類)",
    "description": "事實摘要描述",
    "is_main_breadwinner": true,
    "proof_documents": ["診斷證明書"]
  },
  "financial_status": {
    "household_size": 1,
    "monthly_total_income": 0,
    "per_capita_income": 0,
    "total_savings": 5000,
    "is_eligible_by_poverty_line": true
  },
  "action_result": {
    "approved_amount": 20000,
    "payment_method": "一次性發給",
    "referrals": ["醫療補助"]
  },
  "safety_net_alert": {
    "is_vulnerable_family": false,
    "ecare_notified": false
  }
}
                """

                system_prompt = (
                    "您是急難紓困專業審核 Agent。請根據民眾主述，嚴格遵循《強化社會安全網－急難紓困實施方案作業手冊》之規範進行判定。\n"
                    "核心準則：\n"
                    "1. 遵循「速訪、速評、速發」原則。\n"
                    "2. 急難事實認定須精準對應 7 大類事由（第3類為罹患重傷病，需休養1個月以上且無法工作）。\n"
                    "3. 家計評估計算人口僅限「實際共同生活者」。存款以每人平均不超過15萬元為原則。\n"
                    "4. 若個案疑似保護性或脆弱家庭，必須將 is_vulnerable_family 與 ecare_notified 設為 true。\n"
                    "5. 核發金額範圍在 10,000 ~ 30,000 元之間。\n\n"
                    "【重要輸出規範】\n"
                    f"請務必完全以繁體中文回答。你必須『完全、嚴格』依照以下 JSON 範例的格式與鍵值(Keys)回傳資料，絕對不能發明新欄位或將欄位打散：\n{json_template}"
                )

                # 呼叫 Groq 模型 (使用低隨機性 temperature=0.1 確保聽話)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"請分析以下個案並嚴格依範例格式輸出 JSON：\n{raw_text}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                # 解析回傳的 JSON 字串並對齊 Pydantic Schema
                raw_json = response.choices[0].message.content
                result = ScreeningResult.model_validate_json(raw_json)
                
                st.success("✅ 審核評估完成！")
                
                # 6. 前端網頁排版呈現結果
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 基本與急難評估 (附表二/四)")
                    st.info(f"**案主姓名：** {result.application_info.applicant_name} ({result.application_info.id_number})")
                    st.info(f"**通報來源：** {result.application_info.case_source}")
                    st.warning(f"**急難類別：** {result.emergency_assessment.category}")
                    st.write(f"**事實摘要：** {result.emergency_assessment.description}")
                    st.write(f"**主要負擔家計者：** {'是' if result.emergency_assessment.is_main_breadwinner else '否'}")
                    st.write(f"**建議檢附證明：** {', '.join(result.emergency_assessment.proof_documents)}")
                    
                with col2:
                    st.subheader("💰 財務與核定結果")
                    st.metric(label="共同生活人數", value=f"{result.financial_status.household_size} 人")
                    st.metric(label="每人每月平均所得", value=f"${result.financial_status.per_capita_income:,.0f} 元")
                    st.metric(label="建議核發救助金", value=f"${result.action_result.approved_amount:,.0f} 元", delta="符合速發原則")
                    
                    st.markdown("---")
                    st.subheader("🛡️ 社會安全網轉介提示")
                    if result.safety_net_alert.is_vulnerable_family:
                        st.error("🚨 警告：本案疑似保護性或脆弱家庭！系統已自動標記通報『關懷 e 起來』。")
                    else:
                        st.success("🟢 本案暫無安全網保護性通報需求。")
                    st.write(f"**後續建議轉介單位：** {', '.join(result.action_result.referrals)}")
                    
            except Exception as e:
                st.error(f"❌ 系統發生錯誤或 JSON 解析失敗：{str(e)}")
                if 'response' in locals():
                    with st.expander("🔍 查看 AI 原始回傳內容（供排錯用）"):
                        st.code(response.choices[0].message.content, language="json")
