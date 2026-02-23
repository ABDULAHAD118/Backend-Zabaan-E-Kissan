# app/chatbotWorkflow.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
import requests
from datetime import datetime, timedelta
import re
from langchain_community.tools import DuckDuckGoSearchRun

# ==============================================
# REMOTE SENSING ANALYZER
# ==============================================

class RemoteSensingAnalyzer:
    """Analyzes agricultural fields using NASA POWER API"""
    
    def __init__(self):
        self.nasa_power_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        
    def analyze_field(self, latitude: float, longitude: float) -> dict:
        """Analyze field conditions"""
        try:
            nasa_data = self._get_nasa_power_data(latitude, longitude)
            ndvi_data = self._estimate_ndvi(latitude, longitude)
            analysis = self._interpret_results(ndvi_data, nasa_data)
            
            return {
                "status": "success",
                "location": {
                    "lat": latitude, 
                    "lon": longitude,
                    "region": self._get_region_name(latitude, longitude)
                },
                "ndvi": ndvi_data,
                "soil_moisture": nasa_data["soil_moisture"],
                "weather": nasa_data["weather"],
                "rainfall": nasa_data["rainfall"],
                "analysis": analysis,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error: {str(e)}"
            }
    
    def _get_region_name(self, lat: float, lon: float) -> str:
        if 31 <= lat <= 35 and 72 <= lon <= 75:
            return "Punjab"
        elif 24 <= lat <= 28 and 67 <= lon <= 71:
            return "Sindh"
        elif 29 <= lat <= 35 and 61 <= lon <= 71:
            return "Balochistan"
        elif 34 <= lat <= 37 and 71 <= lon <= 75:
            return "Khyber Pakhtunkhwa"
        return "Pakistan"
    
    def _estimate_ndvi(self, lat: float, lon: float) -> dict:
        current_month = datetime.now().month
        
        if current_month in [11, 12, 1, 2]:
            ndvi_value = 0.6
        elif current_month in [3, 4]:
            ndvi_value = 0.7
        elif current_month in [5, 6, 7]:
            ndvi_value = 0.4
        else:
            ndvi_value = 0.65
        
        return {
            "value": ndvi_value,
            "interpretation": self._interpret_ndvi(ndvi_value),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Seasonal estimate"
        }
    
    def _interpret_ndvi(self, ndvi: float) -> str:
        if ndvi < 0.2:
            return "خالی زمین"
        elif ndvi < 0.4:
            return "ابتدائی نشوونما"
        elif ndvi < 0.6:
            return "اچھی فصل"
        elif ndvi < 0.8:
            return "بہترین صحت"
        return "بہت گھنی"
    
    def _get_nasa_power_data(self, lat: float, lon: float) -> dict:
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            params = {
                "parameters": "GWETROOT,PRECTOTCORR,T2M,RH2M",
                "community": "AG",
                "longitude": lon,
                "latitude": lat,
                "start": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
                "format": "JSON"
            }
            
            response = requests.get(self.nasa_power_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                print(data)
                params_data = data.get("parameters", {})
                
                gwetroot = list(params_data.get("GWETROOT", {0.3: 0.3}).values())[-1]
                temp = list(params_data.get("T2M", {25: 25}).values())[-1]
                humidity = list(params_data.get("RH2M", {60: 60}).values())[-1]
                rainfall_data = params_data.get("PRECTOTCORR", {})
                rainfall_week = sum(list(rainfall_data.values())) if rainfall_data else 0
                
                return {
                    "soil_moisture": {
                        "value": round(gwetroot, 2),
                        "level": self._interpret_soil_moisture(gwetroot),
                        "recommendation": self._soil_moisture_advice(gwetroot)
                    },
                    "weather": {
                        "temperature": round(temp, 1),
                        "humidity": round(humidity, 1),
                        "condition": self._weather_condition(temp)
                    },
                    "rainfall": {
                        "last_7_days": round(rainfall_week, 1),
                        "status": self._rainfall_status(rainfall_week)
                    }
                }
            return self._get_default_data()
        except Exception as e:
            print(f"NASA API error: {e}")
            return self._get_default_data()
    
    def _get_default_data(self):
        return {
            "soil_moisture": {"value": 0.3, "level": "اعتدال", "recommendation": "نگرانی کریں"},
            "weather": {"temperature": 25, "humidity": 60, "condition": "معتدل"},
            "rainfall": {"last_7_days": 0, "status": "خشک"}
        }
    
    def _interpret_soil_moisture(self, value: float) -> str:
        if value < 0.15: return "بہت خشک ❗"
        elif value < 0.25: return "خشک ⚠️"
        elif value < 0.35: return "اعتدال ✅"
        elif value < 0.45: return "نمی 💧"
        return "زیادہ نمی 🌊"
    
    def _soil_moisture_advice(self, value: float) -> str:
        if value < 0.15: return "فوری پانی"
        elif value < 0.25: return "24 گھنٹے میں پانی"
        elif value < 0.45: return "ضرورت نہیں"
        return "پانی نہ دیں"
    
    def _weather_condition(self, temp: float) -> str:
        if temp > 35: return "بہت گرم 🌡️"
        elif temp > 30: return "گرم 🌤️"
        elif temp > 20: return "معتدل ☀️"
        return "ٹھنڈا 🌥️"
    
    def _rainfall_status(self, mm: float) -> str:
        if mm > 50: return "زیادہ بارش 🌧️"
        elif mm > 20: return "اچھی بارش 🌦️"
        elif mm > 5: return "ہلکی بارش 💧"
        return "خشک ☀️"
    
    def _interpret_results(self, ndvi: dict, nasa_data: dict) -> str:
        return f"""🌾 فصل: {ndvi['interpretation']} (NDVI: {ndvi['value']})
💧 زمین: {nasa_data['soil_moisture']['level']} → {nasa_data['soil_moisture']['recommendation']}
🌡️ موسم: {nasa_data['weather']['condition']} ({nasa_data['weather']['temperature']}°C)
🌧️ بارش: {nasa_data['rainfall']['last_7_days']} ملی میٹر"""


# ==============================================
# HELPER FUNCTIONS
# ==============================================

def extract_location_from_message(message: str) -> Optional[tuple]:
    pattern = r'[-+]?([0-9]*\.[0-9]+|[0-9]+)[\s,]+[-+]?([0-9]*\.[0-9]+|[0-9]+)'
    match = re.search(pattern, message)
    if match:
        try:
            lat, lon = float(match.group(1)), float(match.group(2))
            if 23.0 <= lat <= 37.0 and 60.0 <= lon <= 78.0:
                return (lat, lon)
        except ValueError:
            pass
    return None


# ==============================================
# CHATBOT STATE
# ==============================================

class ChatbotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    field_analysis: Optional[dict]


# ==============================================
# CHATBOT WORKFLOW
# ==============================================

class ChatbotWorkflow:
    def __init__(self):
        self.rs_analyzer = RemoteSensingAnalyzer()
        # Initialize web search tool for real-time information
        try:
            self.search_tool = DuckDuckGoSearchRun()
        except:
            self.search_tool = None
            print("⚠️ Web search tool not available, will use model knowledge only")
        
        # Get current date and time for context
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_date_readable = datetime.now().strftime("%B %d, %Y")
        print(f"📅 Current date: {current_date_readable} ({current_date})")
        self.prompt = ChatPromptTemplate.from_messages([
    ("system", f"""
        آپ **"زبانِ کسان"** ہیں، پاکستان کے کسانوں، طلباء اور زراعت سے محبت کرنے والوں کی مدد کے لیے ایک دوستانہ اور باشعور زرعی معاون۔

**اہم - موجودہ تاریخ کی معلومات:**

  - آج کی تاریخ ہے: {current_date_readable} ({current_date})
  - ہمیشہ اپنے جوابات میں آج کی تاریخ کا استعمال کریں، کوئی پرانی تاریخ نہیں
  - موسم، فصل کے حالات، یا موجودہ واقعات کے بارے میں بات کرتے وقت، آج کی تاریخ کا حوالہ دیں
  - یہ نہ بتائیں کہ آپ کے ٹریننگ ڈیٹا کی کوئی کٹ آف تاریخ ہے
  - اگر آپ کو تازہ ترین معلومات درکار ہوں، تو آپ دستیاب ٹولز کے ذریعے ریئل ٹائم ڈیٹا تک رسائی حاصل کر سکتے ہیں

**بنیادی توجہ کے شعبے:**

  - بڑی فصلیں: **گندم، کپاس، چاول، اور مکئی**
  - **مویشیوں کی رہنمائی**
  - **آبپاشی اور کھادیں**
  - **کھیت کی نگرانی** **سیٹلائٹ ڈیٹا** کا استعمال کرتے ہوئے (این ڈی وی آئی، مٹی کی نمی، اور موسم کی تازہ ترین معلومات)
  - **پاکستان میں عمومی زراعت**

**جوابی ہدایات:**

1.  اگر صارف **گندم، کپاس، چاول، یا مکئی** کے بارے میں پوچھے، تو ان کے بارے میں بھرپور، درست معلومات فراہم کریں:

      - کاشتکاری کے طریقے
      - کٹائی کے طریقے
      - پیداوار اور پیداوار کے اعداد و شمار
      - پاکستان کی معیشت میں اہمیت
      - بیماریاں، چیلنجز، اور تجویز کردہ حل

2.  اگر صارف **پاکستان میں عمومی زراعت** کے بارے میں پوچھے، تو شائستہ، متعلقہ، اور معلوماتی جوابات دیں — بشمول مٹی کی اقسام، آبی وسائل، کھاد کا استعمال، اور حکومتی اقدامات۔

3.  اگر صارف **مویشیوں، آبپاشی، کھادوں، این ڈی وی آئی، مٹی کی نمی، یا موسمی حالات** کے بارے میں پوچھے، تو پاکستان سے متعلق مددگار اور عملی زرعی رہنمائی فراہم کریں۔

4.  **انتہائی اہم - فیلڈ تجزیہ کے جوابات (فصل کے حالات کے سوالات):**
    جب کوئی صارف فصل کی حالت کے بارے میں پوچھے اور مقام کے کوآرڈینیٹس فراہم کرے، تو آپ کو فیلڈ تجزیہ کا ڈیٹا موصول ہوگا۔ آپ کے جواب میں یہ ہونا چاہیے:

    **صارف کو یہ تکنیکی اصطلاحات نہ بتائیں:**

      - این ڈی وی آئی (NDVI)، ویجیٹیشن انڈیکس، سیٹلائٹ ڈیٹا، ریموٹ سینسنگ
      - تکنیکی نمبر یا میٹرکس
      - JSON یا ڈیٹا فارمیٹس

    **اس کے بجائے یہ کریں:**

      - کہیں "میں نے آپ کے کھیت کا جائزہ لیا" یا "آپ کے کھیت کا جائزہ لیا"
      - فصل کی صحت کو آسان الفاظ میں بیان کریں: "آپ کی فصل اچھی ہے"
      - روزمرہ کی زبان استعمال کریں: "زمین کو پانی کی ضرورت ہے"
      - واضح، قابل عمل مشورہ دیں: "2-3 دن میں پانی دیں"
      - وضاحت کریں کہ کسان کو کیا کرنا چاہیے: "کھاد ڈالیں"
      - مددگار اور ہمدرد بنیں
      - سادہ متن میں لکھیں، JSON فارمیٹ میں نہیں
      - ہمیشہ اردو میں جواب دیں

    **مثالی اچھا جواب (اردو):**

    ```
    آپ کے کھیت کا جائزہ لیا ہے۔

    فصل کی حالت:
    آپ کی فصل اچھی حالت میں ہے لیکن زمین میں نمی کم ہے۔

    تجویز:
    - براہ کرم 1-2 دن میں پانی دیں
    - موسم اچھی ہے
    - بارش کی امید نہیں ہے
    ```

5.  اگر صارف **زراعت یا پاکستان سے غیر متعلقہ** کسی بھی چیز کے بارے میں پوچھے، تو عاجزی سے ان میں سے ایک جواب دیں:

      - "میں صرف پاکستان کی زراعت کے سلسلے میں آپ کی مدد کے لیے حاضر ہوں۔"
      - "معذرت، میں صرف پاکستان میں فصلوں، مویشیوں اور کھیتی باڑی کے بارے میں تفصیلات فراہم کر سکتا ہوں۔"
      - "میری توجہ پاکستان میں زراعت پر ہے، خاص طور پر گندم، کپاس، چاول اور مکئی جیسی بڑی فصلوں پر۔"

**زبان کا استعمال (انتہائی اہم):**

  - آپ کو **صرف اردو میں** جواب دینا چاہیے۔
  - اگر صارف کسی دوسری زبان (جیسے انگریزی یا پنجابی) میں لکھتا ہے، تو آپ کو **اردو میں** جواب دینا چاہیے اور شائستگی سے مطلع کرنا چاہیے کہ آپ صرف اردو میں بات چیت کر سکتے ہیں۔
  - **مثال کے طور پر اگر صارف انگریزی میں پوچھتا ہے:** "معذرت، میں صرف اردو میں جواب دے سکتا ہوں۔"

**جوابی ساخت:**

  - دوستانہ سلام سے شروعات کریں (اختیاری)۔
  - معلومات کو منظم کرنے کے لیے سادہ متن اور لائن بریکس کا استعمال کریں۔
  - اگر مناسب ہو تو مددگار اختتامی کلمات کے ساتھ ختم کریں۔
  - فارمیٹنگ کو سادہ اور صاف رکھیں۔

**لہجہ:**

  - ہمیشہ **پُرجوش، شائستہ، مددگار، اور تعلیمی** رہیں۔
  - پائیدار کاشتکاری کے طریقوں کی حوصلہ افزائی کریں۔
  - پاکستانی کسانوں کے لیے دوستانہ سلام اور ثقافتی احترام کا استعمال کریں۔

**تاریخ اور وقت کے حوالے:**

  - ہمیشہ تمام جوابات میں آج کی تاریخ ({current_date_readable}) کا استعمال کریں
  - "آج"، "ابھی"، "موجودہ موسم"، "اس ہفتے"، "موجودہ موسم" کہیں
  - کبھی بھی "5 اپریل 2025" جیسی پرانی تاریخوں کا ذکر نہ کریں
  - موسم اور فیلڈ کا ڈیٹا ریئل ٹائم اور موجودہ ہے (انٹرنیٹ ذرائع سے براہ راست حاصل کیا گیا)
  - معلومات فراہم کرتے وقت، اسے موجودہ/آج کی معلومات کے طور پر پیش کریں
  - یہ نہ کہیں کہ "اپریل کے ڈیٹا کی بنیاد پر" یا ٹریننگ کٹ آف تاریخوں کا ذکر کریں
  - ایسا ظاہر کریں کہ آپ کے پاس موجودہ معلومات تک رسائی ہے (جو آپ کے پاس ریئل ٹائم APIs کے ذریعے ہے)

گفتگو کی تاریخ کا استعمال کرتے ہوئے متعلقہ رہیں اور یاد رکھیں کہ پہلے کیا بات ہوئی تھی۔
    """),
    ("placeholder", "{messages}")
]
)
        
        self.llm = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen3-235B-A22B-Instruct-2507",
            task="text-generation",
            max_new_tokens=512,
            temperature=0.5,
        )
        
        self.model = ChatHuggingFace(llm=self.llm)
        self.chatbot_chain = self.prompt | self.model | StrOutputParser()
        self.graph = self._build_graph()
    
    def _get_current_date_context(self):
        """Get current date information for context"""
        now = datetime.now()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "date_readable": now.strftime("%B %d, %Y"),
            "day": now.strftime("%A"),
            "time": now.strftime("%H:%M")
        }
    
    def _chat_node(self, state: ChatbotState) -> ChatbotState:
        last_message = state['messages'][-1]
        field_analysis = None
        
        # Add current date context to every message
        date_context = self._get_current_date_context()
        date_info = f"\n\n[Current Context: Today is {date_context['date_readable']} ({date_context['day']}). Current time: {date_context['time']}. Always use this date when responding about current events, weather, or today's information.]"
        
        if isinstance(last_message, HumanMessage):
            # Add date context to user message
            last_message.content += date_info
            
            location = extract_location_from_message(last_message.content)
            if location:
                lat, lon = location
                print(f"🛰️ Analyzing field at {lat}, {lon}...")
                
                # Analyze field directly using the analyzer
                try:
                    field_analysis = self.rs_analyzer.analyze_field(lat, lon)
                    
                    if field_analysis.get("status") == "success":
                        # Format field analysis in simple terms for LLM (no technical jargon)
                        ndvi_interp = field_analysis.get('ndvi', {}).get('interpretation', '')
                        soil_level = field_analysis.get('soil_moisture', {}).get('level', '')
                        soil_rec = field_analysis.get('soil_moisture', {}).get('recommendation', '')
                        weather_cond = field_analysis.get('weather', {}).get('condition', '')
                        temp = field_analysis.get('weather', {}).get('temperature', 'N/A')
                        rainfall_status = field_analysis.get('rainfall', {}).get('status', '')
                        rainfall_amount = field_analysis.get('rainfall', {}).get('last_7_days', 0)
                        region = field_analysis.get('location', {}).get('region', '')
                        
                        # Create simple, natural description without technical terms
                        # Convert technical data into farmer-friendly language
                        crop_status = ndvi_interp
                        soil_info = f"{soil_level}. {soil_rec}"
                        weather_info = f"{weather_cond}"
                        rainfall_info = f"{rainfall_status}"
                        
                        # Get today's date for context
                        today_date = date_context['date_readable']
                        
                        analysis_context = f"""

User asked about their crop condition. I checked their field in {region} TODAY ({today_date}). Here's what I found about their field RIGHT NOW:
Crop looks: {crop_status}
Soil condition: {soil_info}
Today's Weather: {weather_info}, temperature around {temp} degrees
Rain situation (recent): {rainfall_info}
Now respond to the user in simple, friendly language. Tell them:
How their crop is doing TODAY (in simple words)
What action they need to take NOW or SOON (clear instructions)
Important rules:

    Use newlines to separate paragraphs
    Say "today", "right now", "current conditions" - NOT specific dates like "April 5, 2025"
    DO NOT use words like: NDVI, satellite, remote sensing, vegetation index, technical data, metrics
    DO NOT mention dates like "April 5, 2025" or any past dates
    DO use simple words: "crop looks good", "field needs water", "soil is dry"
    Write like you're a helpful neighbor giving advice about TODAY
    Use the same language as the user (Urdu/English/Punjabi)
    Give practical, actionable advice in simple terms
    Refer to current/today's conditions
"""
                        last_message.content += analysis_context
                    else:
                        error_msg = field_analysis.get("message", "Unknown error occurred")
                        last_message.content += f"\n\n[Field Analysis Error: {error_msg}]"
                except Exception as e:
                    print(f"❌ Error analyzing field: {e}")
                    last_message.content += f"\n\n[Field Analysis Error: Could not analyze field. Please try again later.]"
                    field_analysis = {"status": "error", "message": str(e)}
        
        response = self.chatbot_chain.invoke({"messages": state['messages']})
        
        return {"messages": [AIMessage(content=response)], "field_analysis": field_analysis}
    
    def _build_graph(self):
        graph_builder = StateGraph(ChatbotState)
        graph_builder.add_node("chat_node", self._chat_node)
        graph_builder.add_edge(START, "chat_node")
        graph_builder.add_edge("chat_node", END)
        return graph_builder.compile(checkpointer=InMemorySaver())
    
    def invoke(self, message: str, thread_id: str) -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke({"messages": [HumanMessage(content=message)]}, config=config)
        return {"response": result["messages"][-1].content, "field_analysis": result.get("field_analysis")}
    
    async def stream(self, message: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        messages = {"messages": [HumanMessage(content=message)]}
        async for event in self.graph.astream_events(messages, config=config, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content

    def get_history(self, thread_id: str) -> list:
        config = {"configurable": {"thread_id": thread_id}}
        state = self.graph.get_state(config)
        messages = state.values.get("messages", [])
        return [{"type": type(msg).__name__, "content": msg.content} for msg in messages]


# Create singleton instances
chatbot = ChatbotWorkflow()
rs_analyzer = RemoteSensingAnalyzer()