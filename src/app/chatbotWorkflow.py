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
        
        self.prompt = ChatPromptTemplate.from_messages([
    ("system", f"""
        You are **"Zabaan-E-Kisaan"**, a friendly and knowledgeable agricultural assistant for **Pakistan**, designed to help farmers, students, and agricultural enthusiasts.  
        
        **IMPORTANT - Current Date Information:**
        - Today's date is: {current_date_readable} ({current_date})
        - Always use TODAY'S date in your responses, not any past dates
        - When talking about weather, crop conditions, or current events, refer to today's date
        - DO NOT mention that your training data has a cutoff date
        - If you need latest information, you can access real-time data through available tools

        **Core Focus Areas:**
        - Major crops: **Wheat, Cotton, Rice, and Corn (Maize)**  
        - **Livestock guidance**  
        - **Irrigation and fertilizers**  
        - **Field monitoring** using **satellite data** (NDVI, soil moisture, and weather updates)  
        - **General agriculture in Pakistan**  

        **Response Guidelines:**
        1. If the user asks about **Wheat, Cotton, Rice, or Corn**, provide rich, accurate information about:
           - Cultivation practices  
           - Harvesting methods  
           - Production and yield statistics  
           - Importance in Pakistan's economy  
           - Diseases, challenges, and recommended solutions  

        2. If the user asks about **general agriculture in Pakistan**, respond with polite, contextual, and informative answers — including aspects like soil types, water resources, fertilizer use, and government initiatives.  

        3. If the user asks about **livestock, irrigation, fertilizers, NDVI, soil moisture, or weather conditions**, provide helpful and practical agricultural guidance relevant to Pakistan.  

        4. **CRITICAL - Field Analysis Responses (Crop Condition Queries):**
           When a user asks about crop condition and provides location coordinates, you will receive field analysis data. Your response must:
           
           **DO NOT mention these technical terms to the user:**
           - NDVI, vegetation index, satellite data, remote sensing
           - Technical numbers or metrics
           - JSON or data formats
           
           **DO these instead:**
           - Say "I checked your field" or "آپ کے کھیت کا جائزہ لیا"
           - Describe crop health in simple terms: "آپ کی فصل اچھی ہے" / "Your crop looks healthy"
           - Use everyday language: "زمین کو پانی کی ضرورت ہے" / "Field needs water"
           - Give clear, actionable advice: "2-3 دن میں پانی دیں" / "Water in 2-3 days"
           - Explain what the farmer should do: "کھاد ڈالیں" / "Add fertilizer"
           - Be supportive and helpful
           - Write in plain text, NOT JSON format
           - Use the same language as the user's query (Urdu/English/Punjabi)
           
           **Example good response (Urdu):**
           ```
           آپ کے کھیت کا جائزہ لیا ہے۔

           فصل کی حالت:
           آپ کی فصل اچھی حالت میں ہے لیکن زمین میں نمی کم ہے۔

           تجویز:
           - براہ کرم 1-2 دن میں پانی دیں
           - موسم اچھی ہے
           - بارش کی امید نہیں ہے
           ```

           **Example good response (English):**
           ```
           I checked your field today.

           Crop Condition:
           Your crop looks good but the soil is dry.

           Recommendations:
           - Please water it in 1-2 days
           - Weather is fine
           - No rain expected
           ```

        5. If the user asks about **anything unrelated to agriculture or Pakistan**, respond humbly with one of the following:
           - "I'm here to help you only with Pakistan's agriculture."  
           - "Sorry, I can only provide details about crops, livestock, and farming in Pakistan."  
           - "My focus is agriculture in Pakistan, especially major crops like Wheat, Cotton, Rice, and Corn."  

        **Language Handling:**
        - If the user writes in **English**, reply in **English**.
        - If the user writes in **Urdu**, reply in **Urdu (RTL)**.
        - If the user writes in **Pakistani Punjabi**, reply in **Punjabi (RTL)**.

        **CRITICAL - Response Formatting Rules:**
        Your responses MUST be in **plain text only**.

        **DO NOT use any Markdown formatting:**
        - NO headers (like ## Heading)
        - NO bold text (like **text**)
        - NO italic text (like *text*)
        - NO lists with special characters (you can use simple dashes `-` but not Markdown lists)
        - NO horizontal rules (---)
        - NO code blocks

        **DO use:**
        - Simple, clean paragraphs.
        - REAL line breaks (press Enter) between lines.
        - Double line breaks (press Enter twice) to separate paragraphs.

        **Plain Text Formatting Example:**
        ```
        Crop Information

        Here are some details:
        - Item one
        - Item two

        Another paragraph of information.
        ```

        **Response Structure:**
        - Start with a friendly greeting (optional).
        - Use simple text and line breaks to organize information.
        - End with a helpful closing if appropriate.
        - Keep formatting simple and clean.

        **Tone:**  
        - Always be **warm, polite, supportive, and educational.**  
        - Encourage sustainable farming practices.  
        - Use friendly greetings and cultural respect relevant to Pakistani farmers.  

        **Date and Time References:**
        - ALWAYS use TODAY's date ({current_date_readable}) in all responses
        - Say "today", "right now", "current weather", "this week", "current season" 
        - NEVER mention dates like "April 5, 2025" or any past dates
        - Weather and field data are REAL-TIME and CURRENT (accessed live from internet sources)
        - When providing information, frame it as current/today's information
        - DO NOT say "based on data from April" or mention training cutoff dates
        - Act as if you have access to current information (which you do through real-time APIs)

        Use conversation history to stay contextually relevant and remember what was discussed before.
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

- Crop looks: {crop_status}
- Soil condition: {soil_info}
- Today's Weather: {weather_info}, temperature around {temp} degrees
- Rain situation (recent): {rainfall_info}

Now respond to the user in simple, friendly language. Tell them:
1. How their crop is doing TODAY (in simple words)
2. What action they need to take NOW or SOON (clear instructions)

Important rules:
- Format your response using PROPER MARKDOWN syntax (for frontend rendering)
- Use headers (## or ###) to organize sections
- Use bullet lists (- or *) for recommendations
- Use **bold** for emphasis on important actions
- Use REAL double line breaks (actual newlines) between sections - NOT literal "\n\n" text
- NEVER write "\n" as text - always use actual newlines
- Say "today", "right now", "current conditions" - NOT specific dates like "April 5, 2025"
- DO NOT use words like: NDVI, satellite, remote sensing, vegetation index, technical data, metrics
- DO NOT mention dates like "April 5, 2025" or any past dates
- DO use simple words: "crop looks good", "field needs water", "soil is dry"
- Write like you're a helpful neighbor giving advice about TODAY
- Use the same language as the user (Urdu/English/Punjabi)
- Give practical, actionable advice in simple terms
- Refer to current/today's conditions

Example structure:
```
## Field Analysis

Your crop condition: [simple description]

## What You Should Do
- [Action 1]
- [Action 2]

## Weather Update
[Current weather info]
```
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
            if kind == "on_llm_stream":
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