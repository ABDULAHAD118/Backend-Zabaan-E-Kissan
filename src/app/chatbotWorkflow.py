# app/chatbotWorkflow.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from typing import TypedDict, Annotated, Optional, Literal
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
            return {"status": "error", "message": f"Error: {str(e)}"}

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
        m = datetime.now().month
        if m in [11, 12, 1, 2]:
            ndvi_value = 0.6
        elif m in [3, 4]:
            ndvi_value = 0.7
        elif m in [5, 6, 7]:
            ndvi_value = 0.4
        else:
            ndvi_value = 0.65
        return {
            "value": ndvi_value,
            "interpretation": self._interpret_ndvi(ndvi_value),
            "interpretation_en": self._interpret_ndvi_en(ndvi_value),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Seasonal estimate"
        }

    def _interpret_ndvi(self, ndvi: float) -> str:
        if ndvi < 0.2:   return "خالی زمین"
        elif ndvi < 0.4: return "ابتدائی نشوونما"
        elif ndvi < 0.6: return "اچھی فصل"
        elif ndvi < 0.8: return "بہترین صحت"
        return "بہت گھنی"

    def _interpret_ndvi_en(self, ndvi: float) -> str:
        if ndvi < 0.2:   return "Bare land"
        elif ndvi < 0.4: return "Early growth"
        elif ndvi < 0.6: return "Good crop"
        elif ndvi < 0.8: return "Excellent health"
        return "Very dense"

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
                        "level_en": self._interpret_soil_moisture_en(gwetroot),
                        "recommendation": self._soil_moisture_advice(gwetroot),
                        "recommendation_en": self._soil_moisture_advice_en(gwetroot)
                    },
                    "weather": {
                        "temperature": round(temp, 1),
                        "humidity": round(humidity, 1),
                        "condition": self._weather_condition(temp),
                        "condition_en": self._weather_condition_en(temp)
                    },
                    "rainfall": {
                        "last_7_days": round(rainfall_week, 1),
                        "status": self._rainfall_status(rainfall_week),
                        "status_en": self._rainfall_status_en(rainfall_week)
                    }
                }
            return self._get_default_data()
        except Exception as e:
            print(f"NASA API error: {e}")
            return self._get_default_data()

    def _get_default_data(self):
        return {
            "soil_moisture": {
                "value": 0.3, "level": "اعتدال", "level_en": "Moderate",
                "recommendation": "نگرانی کریں", "recommendation_en": "Monitor closely"
            },
            "weather": {"temperature": 25, "humidity": 60, "condition": "معتدل", "condition_en": "Moderate"},
            "rainfall": {"last_7_days": 0, "status": "خشک", "status_en": "Dry"}
        }

    def _interpret_soil_moisture(self, v: float) -> str:
        if v < 0.15: return "بہت خشک ❗"
        elif v < 0.25: return "خشک ⚠️"
        elif v < 0.35: return "اعتدال ✅"
        elif v < 0.45: return "نمی 💧"
        return "زیادہ نمی 🌊"

    def _interpret_soil_moisture_en(self, v: float) -> str:
        if v < 0.15: return "Very Dry ❗"
        elif v < 0.25: return "Dry ⚠️"
        elif v < 0.35: return "Moderate ✅"
        elif v < 0.45: return "Moist 💧"
        return "Waterlogged 🌊"

    def _soil_moisture_advice(self, v: float) -> str:
        if v < 0.15: return "فوری پانی دیں"
        elif v < 0.25: return "24 گھنٹے میں پانی دیں"
        elif v < 0.45: return "پانی کی ضرورت نہیں"
        return "پانی بالکل نہ دیں"

    def _soil_moisture_advice_en(self, v: float) -> str:
        if v < 0.15: return "Irrigate immediately"
        elif v < 0.25: return "Irrigate within 24 hours"
        elif v < 0.45: return "No irrigation needed"
        return "Do NOT irrigate — risk of waterlogging"

    def _weather_condition(self, temp: float) -> str:
        if temp > 35: return "بہت گرم 🌡️"
        elif temp > 30: return "گرم 🌤️"
        elif temp > 20: return "معتدل ☀️"
        return "ٹھنڈا 🌥️"

    def _weather_condition_en(self, temp: float) -> str:
        if temp > 35: return "Very Hot 🌡️"
        elif temp > 30: return "Hot 🌤️"
        elif temp > 20: return "Moderate ☀️"
        return "Cold 🌥️"

    def _rainfall_status(self, mm: float) -> str:
        if mm > 50: return "زیادہ بارش 🌧️"
        elif mm > 20: return "اچھی بارش 🌦️"
        elif mm > 5: return "ہلکی بارش 💧"
        return "خشک ☀️"

    def _rainfall_status_en(self, mm: float) -> str:
        if mm > 50: return "Heavy Rain 🌧️"
        elif mm > 20: return "Good Rain 🌦️"
        elif mm > 5: return "Light Rain 💧"
        return "Dry ☀️"

    def _interpret_results(self, ndvi: dict, nasa_data: dict) -> str:
        return (
            f"🌾 Crop: {ndvi['interpretation']} (NDVI: {ndvi['value']})\n"
            f"💧 Soil: {nasa_data['soil_moisture']['level']} → {nasa_data['soil_moisture']['recommendation']}\n"
            f"🌡️ Weather: {nasa_data['weather']['condition']} ({nasa_data['weather']['temperature']}°C)\n"
            f"🌧️ Rainfall: {nasa_data['rainfall']['last_7_days']} mm"
        )


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


# Agricultural land-use tags recognized by OpenStreetMap
_AGRI_LANDUSE = {
    "farmland", "farm", "farmyard", "orchard", "vineyard",
    "plant_nursery", "greenhouse_horticulture", "allotments",
    "meadow", "paddy", "rice_field", "floodplain",
    "pasture", "grass",
}

_AGRI_NATURAL = {"grassland", "scrub", "heath", "wetland", "wood", "bare_rock"}

_URBAN_LANDUSE = {
    "residential", "commercial", "industrial", "retail",
    "construction", "cemetery", "education", "institutional",
    "military", "port", "railway",
}


def _overpass_landuse_check(lat: float, lon: float, radius_m: int) -> Optional[dict]:
    """
    Query Overpass API with a bounding box of `radius_m` metres around (lat, lon).
    Returns parsed result dict, or None if API is unavailable / times out.
    Result keys: found_urban (list), found_agri (list)
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    delta = radius_m / 111_000          # 1 degree ≈ 111 km
    south, north = lat - delta, lat + delta
    west,  east  = lon - delta, lon + delta

    query = f"""
[out:json][timeout:12];
(
  way["landuse"]({south},{west},{north},{east});
  way["natural"]({south},{west},{north},{east});
  relation["landuse"]({south},{west},{north},{east});
  node["landuse"]({south},{west},{north},{east});
  node["natural"]({south},{west},{north},{east});
);
out tags 20;
"""
    try:
        resp = requests.post(overpass_url, data={"data": query}, timeout=14)
        if resp.status_code != 200:
            return None

        elements = resp.json().get("elements", [])
        found_urban: list[str] = []
        found_agri:  list[str] = []

        for el in elements:
            tags = el.get("tags", {})
            lu   = tags.get("landuse", "").strip().lower()
            nat  = tags.get("natural",  "").strip().lower()
            if lu in _URBAN_LANDUSE:
                found_urban.append(lu)
            if lu in _AGRI_LANDUSE or nat in _AGRI_NATURAL:
                found_agri.append(lu or nat)

        return {"found_urban": found_urban, "found_agri": found_agri, "total": len(elements)}

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return None
    except Exception as e:
        print(f"⚠️ Overpass error (radius={radius_m}m): {e}")
        return None


def _nominatim_urban_check(lat: float, lon: float) -> dict:
    """
    Use Nominatim reverse geocoding to detect if coordinates are inside a
    city / town / suburb / residential area by examining the address hierarchy.

    Returns:
        {"is_urban": bool, "place_type": str, "display_name": str}
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat, "lon": lon,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 16,          # street-level detail
    }
    headers = {"User-Agent": "ZabaanEKissan-AgriBot/1.0 (agricultural assistant)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {"is_urban": False, "place_type": "unknown", "display_name": ""}

        data        = resp.json()
        place_type  = data.get("type", "").lower()          # e.g. residential, farmland
        category    = data.get("category", "").lower()      # e.g. landuse, natural
        address     = data.get("address", {})
        display     = data.get("display_name", "")

        # Urban signals from place type / category
        _URBAN_TYPES = {
            "residential", "commercial", "industrial", "retail",
            "construction", "apartments", "house", "building",
            "office", "school", "hospital", "police", "fire_station",
            "mall", "supermarket", "hotel",
        }
        # Agricultural signals from place type / category
        _AGRI_TYPES = {
            "farmland", "farm", "orchard", "vineyard", "meadow",
            "paddy", "allotments", "greenhouse_horticulture",
            "grass", "scrub", "heath", "forest",
        }

        # Strong urban signals from the address hierarchy
        _URBAN_ADDR_KEYS = {"suburb", "neighbourhood", "quarter", "city_block"}

        if place_type in _URBAN_TYPES or category in ("building", "amenity", "shop"):
            return {"is_urban": True, "place_type": place_type or category, "display_name": display}

        if place_type in _AGRI_TYPES:
            return {"is_urban": False, "place_type": place_type, "display_name": display}

        # Check address hierarchy — if suburb/neighbourhood exists, it's urban
        for key in _URBAN_ADDR_KEYS:
            if key in address:
                return {"is_urban": True, "place_type": key, "display_name": display}

        # Has a house number? Almost certainly not a field
        if address.get("house_number") or address.get("building"):
            return {"is_urban": True, "place_type": "building", "display_name": display}

        return {"is_urban": False, "place_type": place_type or "rural/unknown", "display_name": display}

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        print("⚠️ Nominatim timed out")
        return {"is_urban": False, "place_type": "unknown (timeout)", "display_name": ""}
    except Exception as e:
        print(f"⚠️ Nominatim error: {e}")
        return {"is_urban": False, "place_type": "unknown (error)", "display_name": ""}


def _make_non_agri_response(land_label: str) -> dict:
    return {
        "is_agricultural": False,
        "land_type": land_label,
        "confidence": "high",
        "message_urdu": (
            f"⚠️ **یہ زرعی زمین نہیں لگتی**\n\n"
            f"آپ نے جو مقام دیا ہے وہ **{land_label}** علاقہ معلوم ہوتا ہے، نہ کہ کھیت یا زرعی زمین۔\n\n"
            f"براہ کرم اپنے **اصل کھیت یا فارم** کے GPS نقاط فراہم کریں تاکہ میں "
            f"درست زرعی تجزیہ کر سکوں۔ 🌾"
        ),
        "message_english": (
            f"⚠️ **These coordinates do not appear to be agricultural land**\n\n"
            f"The location you provided seems to be a **{land_label}** area, not a crop field or farm.\n\n"
            f"Please share the GPS coordinates of your **actual farmland or crop field** "
            f"so I can give you an accurate analysis. 🌾"
        ),
    }


def check_agricultural_land(lat: float, lon: float) -> dict:
    """
    Multi-strategy land-use validation using:
      1. Overpass API (OSM) with progressive radius: 300 m → 800 m → 2 km
      2. Nominatim reverse geocoding as final fallback

    Fail-open: if all checks are inconclusive or APIs unavailable, allow through.

    Returns:
        {
          "is_agricultural": bool,
          "land_type": str,
          "confidence": "high" | "medium" | "low",
          "message_urdu": str,
          "message_english": str,
        }
    """
    _PASS = {
        "is_agricultural": True,
        "land_type": "unknown/unmapped",
        "confidence": "low",
        "message_urdu": "",
        "message_english": "",
    }

    # ── Strategy 1: Overpass with progressively larger radius ─────────────────
    for radius in (300, 800, 2000):
        result = _overpass_landuse_check(lat, lon, radius)

        if result is None:
            # API down or timeout — skip to next strategy
            break

        found_urban = result["found_urban"]
        found_agri  = result["found_agri"]
        total       = result["total"]

        print(f"🗺️  Overpass radius={radius}m → urban={found_urban}, agri={found_agri}, total={total}")

        if found_urban and not found_agri:
            # Clear urban signal
            return _make_non_agri_response(found_urban[0])

        if found_agri:
            # Clear agricultural signal
            return {
                "is_agricultural": True,
                "land_type": found_agri[0],
                "confidence": "high",
                "message_urdu": "",
                "message_english": "",
            }

        if found_urban and found_agri:
            # Mixed zone — agricultural wins (field on village edge)
            return {
                "is_agricultural": True,
                "land_type": f"mixed ({found_agri[0]})",
                "confidence": "medium",
                "message_urdu": "",
                "message_english": "",
            }

        # total > 0 but no landuse/natural we recognise → keep widening
        # total == 0 → no OSM data at all → widen and try again

    # ── Strategy 2: Nominatim reverse geocoding ───────────────────────────────
    print(f"🔍 Falling back to Nominatim for ({lat}, {lon})...")
    nom = _nominatim_urban_check(lat, lon)
    print(f"🔍 Nominatim → is_urban={nom['is_urban']}, type={nom['place_type']}")

    if nom["is_urban"]:
        return _make_non_agri_response(nom["place_type"])

    # ── Strategy 3: Fail-open ─────────────────────────────────────────────────
    # Could not confirm it's urban → assume rural/agricultural (Pakistan has
    # vast unmapped farmland). Let the field analysis proceed.
    return _PASS


def _build_system_prompt(language: str, current_date: str, current_date_readable: str) -> str:
    """Build the system prompt based on the requested language."""

    if language == "english":
        return f"""You are **"Zabaan-e-Kissan"** (Voice of the Farmer), a professional and friendly agricultural assistant dedicated to helping farmers, students, and agriculture enthusiasts across Pakistan.

**Internal Date Context (DO NOT show to user):**
- Today's date is: {current_date_readable} ({current_date})
- Use this date to reason about current season, weather, and crop stages.
- Never mention this date explicitly in your response unless the user specifically asks for today's date.
- Do not say "as of my training cutoff" or reference old dates like "April 2025".
- Present all information as current and up-to-date.

**Scope — AGRICULTURE ONLY:**
You MUST only answer questions related to:
- Agriculture in Pakistan (crops, soil, irrigation, fertilizers, pesticides)
- Major crops: wheat, cotton, rice, maize, sugarcane, vegetables, fruits
- Livestock and poultry farming
- Weather and its impact on crops
- Field analysis and crop monitoring
- Government agriculture schemes in Pakistan
- Post-harvest handling and storage

If the user asks about ANYTHING outside agriculture (politics, entertainment, technology, finance, health unrelated to farming, etc.), respond ONLY with:
> "I'm here to assist with agriculture topics only. Please ask me about crops, farming, or livestock in Pakistan."

**Language:**
- Respond ONLY in English.
- If the user writes in Urdu or any other language, reply in English and politely note that you respond in English.

**Response Format — STRICT MARKDOWN:**
Always structure your responses using Markdown so they render beautifully in a mobile app:
- Use `##` and `###` for headings
- Use `-` or `*` for bullet lists
- Use `**bold**` for important terms
- Use `> blockquote` for key recommendations
- Use `---` for section dividers where appropriate
- Use emojis sparingly but meaningfully (🌾 💧 🌡️ 🐄)
- Keep responses concise, practical, and farmer-friendly

**Field Analysis (when coordinates are provided):**
- NEVER use technical jargon: no "NDVI", "remote sensing", "vegetation index", "satellite data"
- Say "I checked your field" — give plain-language crop health summaries
- Give clear, actionable advice: "Irrigate within 24 hours", "Crop looks healthy"

**Tone:**
- Professional yet friendly
- Encouraging sustainable and modern farming practices
- Respectful of Pakistani farming culture
"""
    else:
        # Default: Urdu
        return f"""آپ **"زبانِ کسان"** ہیں — پاکستانی کسانوں، طلباء اور زراعت سے محبت کرنے والوں کے لیے ایک پیشہ ور اور دوستانہ زرعی معاون۔

**اندرونی تاریخ کا سیاق (صارف کو نہ دکھائیں):**
- آج کی تاریخ: {current_date_readable} ({current_date})
- اس تاریخ کو موسم، فصل کے مرحلے، اور موجودہ زرعی حالات سمجھنے کے لیے استعمال کریں۔
- اپنے جواب میں یہ تاریخ براہِ راست نہ لکھیں جب تک صارف خود نہ پوچھے۔
- "اپریل 2025" جیسی پرانی تاریخوں کا ذکر نہ کریں اور نہ ہی "میری ٹریننگ کا اختتام" کہیں۔
- تمام معلومات موجودہ اور تازہ ترین کے طور پر پیش کریں۔

**دائرۂ کار — صرف زراعت:**
آپ صرف درج ذیل موضوعات پر جواب دیں گے:
- پاکستان میں زراعت (فصلیں، مٹی، آبپاشی، کھادیں، کیڑے مار ادویات)
- بڑی فصلیں: گندم، کپاس، چاول، مکئی، گنا، سبزیاں، پھل
- مویشی پالنا اور پولٹری
- موسم اور فصلوں پر اس کا اثر
- کھیت کی نگرانی اور صحت
- پاکستان میں حکومتی زرعی اسکیمیں
- کٹائی کے بعد کی سنبھال اور ذخیرہ

اگر صارف زراعت سے باہر کسی بھی موضوع (سیاست، تفریح، ٹیکنالوجی، مالیات، غیر زرعی صحت وغیرہ) کے بارے میں پوچھے، تو **صرف یہ جواب دیں:**
> "میں صرف پاکستان کی زراعت، فصلوں اور مویشیوں کے بارے میں مدد کر سکتا ہوں۔"

**زبان:**
- **صرف اردو** میں جواب دیں۔
- اگر صارف انگریزی یا کسی اور زبان میں لکھے، تو اردو میں جواب دیں اور شائستگی سے بتائیں کہ آپ اردو میں جواب دیتے ہیں۔

**جوابی فارمیٹ — مارک ڈاؤن لازمی:**
ہمیشہ مارک ڈاؤن استعمال کریں تاکہ موبائل ایپ میں خوبصورت دکھے:
- `##` اور `###` عنوانات کے لیے
- `-` یا `*` نکات کے لیے
- `**بولڈ**` اہم اصطلاحات کے لیے
- `> بلاک کوٹ` اہم سفارشات کے لیے
- `---` سیکشن کی تقسیم کے لیے
- ایموجی مناسب جگہ پر استعمال کریں (🌾 💧 🌡️ 🐄)
- جواب مختصر، عملی اور کسان دوست ہو

**فیلڈ تجزیہ (جب کوآرڈینیٹس دیے جائیں):**
- تکنیکی اصطلاحات استعمال نہ کریں: NDVI، ریموٹ سینسنگ، ویجیٹیشن انڈیکس، سیٹلائٹ ڈیٹا
- کہیں "میں نے آپ کا کھیت دیکھا" — آسان زبان میں فصل کی صحت بیان کریں
- واضح عملی مشورہ دیں: "24 گھنٹے میں پانی دیں"، "فصل اچھی ہے"

**لہجہ:**
- پیشہ ور مگر دوستانہ
- پائیدار اور جدید کاشتکاری کی حوصلہ افزائی
- پاکستانی کسانوں کی ثقافت کا احترام
"""


# ==============================================
# CHATBOT STATE
# ==============================================

class ChatbotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    field_analysis: Optional[dict]
    language: str


# ==============================================
# CHATBOT WORKFLOW
# ==============================================

class ChatbotWorkflow:
    def __init__(self):
        self.rs_analyzer = RemoteSensingAnalyzer()

        self.llm = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen3-235B-A22B-Instruct-2507",
            task="text-generation",
            max_new_tokens=1024,
            temperature=0.5,
        )
        self.model = ChatHuggingFace(llm=self.llm)
        self.graph = self._build_graph()

    def _get_current_date_context(self) -> dict:
        now = datetime.now()
        return {
            "date": now.strftime("%Y-%m-%d"),
            "date_readable": now.strftime("%B %d, %Y"),
            "day": now.strftime("%A"),
            "time": now.strftime("%H:%M")
        }

    def _build_prompt_for_language(self, language: str) -> ChatPromptTemplate:
        date_ctx = self._get_current_date_context()
        system_content = _build_system_prompt(
            language=language,
            current_date=date_ctx["date"],
            current_date_readable=date_ctx["date_readable"]
        )
        return ChatPromptTemplate.from_messages([
            ("system", system_content),
            ("placeholder", "{messages}")
        ])

    def _chat_node(self, state: ChatbotState) -> ChatbotState:
        last_message = state["messages"][-1]
        field_analysis = None
        language = state.get("language", "urdu")

        date_ctx = self._get_current_date_context()

        # Hidden date context injected into user message (NOT shown to user)
        hidden_date_ctx = (
            f"\n\n[SYSTEM_INTERNAL — DO NOT SHOW TO USER: "
            f"Today is {date_ctx['date_readable']} ({date_ctx['day']}), "
            f"time {date_ctx['time']}. Use this for seasonal reasoning only.]"
        )

        if isinstance(last_message, HumanMessage):
            last_message.content += hidden_date_ctx

            location = extract_location_from_message(last_message.content)
            if location:
                lat, lon = location
                print(f"🛰️ Checking land use at {lat}, {lon}...")

                # ── Step 1: Validate that coordinates are on agricultural land ──
                land_check = check_agricultural_land(lat, lon)

                if not land_check["is_agricultural"]:
                    # Inject a refusal so the LLM returns the right message
                    refusal = (
                        land_check["message_english"]
                        if language == "english"
                        else land_check["message_urdu"]
                    )
                    last_message.content += (
                        f"\n\n[SYSTEM_INTERNAL — DO NOT SHOW TO USER: "
                        f"Land-use check FAILED. Land type: {land_check['land_type']}. "
                        f"This is NOT agricultural land. "
                        f"You MUST tell the user EXACTLY this (translate to {language} if needed, "
                        f"keep it warm and helpful): {refusal}. "
                        f"Do NOT proceed with any field analysis. "
                        f"Do NOT mention NDVI, satellite, or any technical terms.]"
                    )
                    print(f"🚫 Non-agricultural land detected: {land_check['land_type']}")
                else:
                    # ── Step 2: Land is agricultural → run full analysis ──
                    print(f"✅ Agricultural land confirmed ({land_check['land_type']}). Analyzing...")
                    try:
                        field_analysis = self.rs_analyzer.analyze_field(lat, lon)
                        if field_analysis.get("status") == "success":
                            if language == "english":
                                crop_status = field_analysis.get("ndvi", {}).get("interpretation_en", "")
                                soil_level = field_analysis.get("soil_moisture", {}).get("level_en", "")
                                soil_rec = field_analysis.get("soil_moisture", {}).get("recommendation_en", "")
                                weather_cond = field_analysis.get("weather", {}).get("condition_en", "")
                                temp = field_analysis.get("weather", {}).get("temperature", "N/A")
                                rainfall_status = field_analysis.get("rainfall", {}).get("status_en", "")
                                rainfall_amount = field_analysis.get("rainfall", {}).get("last_7_days", 0)
                                region = field_analysis.get("location", {}).get("region", "")

                                analysis_context = f"""

[SYSTEM_INTERNAL — DO NOT SHOW TO USER: Field check complete for {region}.
Crop status: {crop_status}. Soil: {soil_level} — {soil_rec}.
Weather: {weather_cond}, {temp}°C. Rainfall last 7 days: {rainfall_status} ({rainfall_amount} mm).
Respond in ENGLISH using Markdown. Give a plain-language crop health summary with clear, actionable advice.
Do NOT mention NDVI, satellite, remote sensing, or vegetation index. Say "I checked your field".]
"""
                            else:
                                crop_status = field_analysis.get("ndvi", {}).get("interpretation", "")
                                soil_level = field_analysis.get("soil_moisture", {}).get("level", "")
                                soil_rec = field_analysis.get("soil_moisture", {}).get("recommendation", "")
                                weather_cond = field_analysis.get("weather", {}).get("condition", "")
                                temp = field_analysis.get("weather", {}).get("temperature", "N/A")
                                rainfall_status = field_analysis.get("rainfall", {}).get("status", "")
                                rainfall_amount = field_analysis.get("rainfall", {}).get("last_7_days", 0)
                                region = field_analysis.get("location", {}).get("region", "")

                                analysis_context = f"""

[SYSTEM_INTERNAL — صارف کو نہ دکھائیں: {region} کے کھیت کا تجزیہ مکمل۔
فصل: {crop_status}۔ مٹی: {soil_level} — {soil_rec}۔
موسم: {weather_cond}، {temp}°C۔ گزشتہ 7 دن بارش: {rainfall_status} ({rainfall_amount} mm)۔
اردو میں Markdown استعمال کرتے ہوئے آسان زبان میں فصل کی صحت بتائیں اور عملی مشورہ دیں۔
NDVI، سیٹلائٹ، ریموٹ سینسنگ الفاظ استعمال نہ کریں۔ کہیں "میں نے آپ کا کھیت دیکھا"۔]
"""

                            last_message.content += analysis_context
                        else:
                            err = field_analysis.get("message", "Unknown error")
                            last_message.content += f"\n\n[SYSTEM_INTERNAL: Field analysis failed: {err}]"
                    except Exception as e:
                        print(f"❌ Error analyzing field: {e}")
                        last_message.content += f"\n\n[SYSTEM_INTERNAL: Field analysis unavailable: {e}]"
                        field_analysis = {"status": "error", "message": str(e)}

        # Build a fresh prompt with the correct language each invocation
        prompt = self._build_prompt_for_language(language)
        chain = prompt | self.model | StrOutputParser()
        response = chain.invoke({"messages": state["messages"]})

        return {
            "messages": [AIMessage(content=response)],
            "field_analysis": field_analysis,
            "language": language
        }

    def _build_graph(self):
        graph_builder = StateGraph(ChatbotState)
        graph_builder.add_node("chat_node", self._chat_node)
        graph_builder.add_edge(START, "chat_node")
        graph_builder.add_edge("chat_node", END)
        return graph_builder.compile(checkpointer=InMemorySaver())

    def invoke(self, message: str, thread_id: str, language: str = "urdu") -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)], "language": language},
            config=config
        )
        return {
            "response": result["messages"][-1].content,
            "field_analysis": result.get("field_analysis"),
            "language": language
        }

    async def stream(self, message: str, thread_id: str, language: str = "urdu"):
        config = {"configurable": {"thread_id": thread_id}}
        messages = {
            "messages": [HumanMessage(content=message)],
            "language": language
        }
        async for event in self.graph.astream_events(messages, config=config, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content

    def get_history(self, thread_id: str) -> list:
        config = {"configurable": {"thread_id": thread_id}}
        state = self.graph.get_state(config)
        messages = state.values.get("messages", [])
        return [{"type": type(msg).__name__, "content": msg.content} for msg in messages]


# Create singleton instances
chatbot = ChatbotWorkflow()
rs_analyzer = RemoteSensingAnalyzer()

