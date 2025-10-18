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
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are "Zuban-e-Kisan", a friendly agricultural assistant for Pakistan with satellite monitoring.
            
Core Features: Crop advice, livestock guidance, irrigation, fertilizers, field monitoring (NDVI, soil moisture, weather)
Language: Default Urdu, auto-switch based on input
Scope: Pakistan agriculture only
Tone: Warm, supportive, educational"""),
            ("placeholder", "{messages}")
        ])
        
        self.llm = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen3-235B-A22B-Instruct-2507",
            task="text-generation",
            max_new_tokens=512,
            temperature=0.5,
        )
        
        self.model = ChatHuggingFace(llm=self.llm)
        self.chatbot_chain = self.prompt | self.model | StrOutputParser()
        self.graph = self._build_graph()
    
    def _chat_node(self, state: ChatbotState) -> ChatbotState:
        last_message = state['messages'][-1]
        field_analysis = None
        
        if isinstance(last_message, HumanMessage):
            location = extract_location_from_message(last_message.content)
            if location:
                lat, lon = location
                print(f"🛰️ Analyzing field at {lat}, {lon}...")
                field_analysis = self.rs_analyzer.analyze_field(lat, lon)
                
                if field_analysis["status"] == "success":
                    analysis_msg = f"\n\n[کھیت کا تجزیہ]\n📍 {field_analysis['location']['region']}\n{field_analysis['analysis']}"
                    last_message.content += analysis_msg
        
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
    
    def get_history(self, thread_id: str) -> list:
        config = {"configurable": {"thread_id": thread_id}}
        state = self.graph.get_state(config)
        messages = state.values.get("messages", [])
        return [{"type": type(msg).__name__, "content": msg.content} for msg in messages]


# Create singleton instances
chatbot = ChatbotWorkflow()
rs_analyzer = RemoteSensingAnalyzer()