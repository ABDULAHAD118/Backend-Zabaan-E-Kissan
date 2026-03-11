"""
Chatbot router.
WS  /chat/{thread_id}          – Streaming chatbot conversation.
POST /chat/{thread_id}/message  – Non-streaming chatbot conversation.
GET  /chat/analyze-field        – Remote sensing field analysis.
"""
import json
import logging
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from ..chatbotWorkflow import chatbot, rs_analyzer, check_agricultural_land
from ..schemas.chatbot import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chatbot"])


@router.websocket("/{thread_id}")
async def chat_socket(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for streaming chatbot responses.

    Clients should send JSON:
        ``{"query": "<user message>", "language": "urdu"}``   (language defaults to "urdu")
        ``{"query": "<user message>", "language": "english"}``

    The server streams response chunks and sends ``{"done": true}`` when finished.
    """
    await websocket.accept()
    if not chatbot:
        await websocket.close(code=1011, reason="Chatbot service is not configured.")
        return
    try:
        while True:
            raw = await websocket.receive_text()
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON payload."}))
                continue

            user_message = data.get("query", "").strip()
            language = data.get("language", "urdu").strip().lower()
            if language not in ("urdu", "english"):
                language = "urdu"

            if not user_message:
                await websocket.send_text(json.dumps({"error": "Empty query."}))
                continue

            try:
                async for chunk in chatbot.stream(
                    message=user_message,
                    thread_id=thread_id,
                    language=language
                ):
                    if chunk:
                        await websocket.send_text(json.dumps({"response": chunk}))
            except Exception as exc:
                logger.error("Chatbot stream error (thread=%s): %s", thread_id, exc)
                await websocket.send_text(
                    json.dumps({"error": "An error occurred while generating a response."})
                )
            await websocket.send_text(json.dumps({"done": True}))
    except WebSocketDisconnect:
        logger.info("Client disconnected from thread %s", thread_id)
    except Exception as exc:
        logger.error("Unexpected WebSocket error (thread=%s): %s", thread_id, exc)
        try:
            await websocket.close(code=1011, reason="Unexpected server error.")
        except Exception:
            pass


@router.post("/{thread_id}/message", summary="Non-streaming chatbot message")
async def chat_message(thread_id: str, request: ChatRequest):
    """
    REST endpoint for non-streaming chatbot responses.

    Send JSON body:
        ``{"query": "گندم کی کاشت؟", "language": "urdu"}``
        ``{"query": "When to plant wheat?", "language": "english"}``

    Returns Markdown-formatted response.
    """
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot service is not configured.")

    language = (request.language or "urdu").strip().lower()
    if language not in ("urdu", "english"):
        language = "urdu"

    try:
        result = chatbot.invoke(
            message=request.query,
            thread_id=thread_id,
            language=language
        )
        return {
            "response": result["response"],
            "language": language,
            "field_analysis": result.get("field_analysis")
        }
    except Exception as exc:
        logger.error("Chatbot invoke error (thread=%s): %s", thread_id, exc)
        raise HTTPException(status_code=500, detail="An error occurred while generating a response.")


@router.get("/analyze-field", summary="Remote sensing field analysis")
async def analyze_field(lat: float, lon: float):
    """
    Analyse a field at the given latitude/longitude using remote sensing.
    Coordinates must fall within Pakistan (23–37 °N, 60–78 °E) AND on agricultural land.
    """
    if not (23 <= lat <= 37 and 60 <= lon <= 78):
        raise HTTPException(
            status_code=400,
            detail="Coordinates are outside the supported Pakistan boundary (lat 23-37, lon 60-78).",
        )

    # Validate land use before running analysis
    land_check = check_agricultural_land(lat, lon)
    if not land_check["is_agricultural"]:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "non_agricultural_land",
                "land_type": land_check["land_type"],
                "message_urdu": land_check["message_urdu"],
                "message_english": land_check["message_english"],
            },
        )

    try:
        return rs_analyzer.analyze_field(lat, lon)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
