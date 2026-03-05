"""
Chatbot router.
WS  /chat/{thread_id}   – Streaming chatbot conversation.
GET /chat/analyze-field – Remote sensing field analysis.
"""
import json
import logging
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from ..chatbotWorkflow import chatbot, rs_analyzer
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chatbot"])
@router.websocket("/{thread_id}")
async def chat_socket(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for streaming chatbot responses.
    Clients should send JSON: ``{"query": "<user message>"}``
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
            if not user_message:
                await websocket.send_text(json.dumps({"error": "Empty query."}))
                continue
            try:
                async for chunk in chatbot.stream(message=user_message, thread_id=thread_id):
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
@router.get("/analyze-field", summary="Remote sensing field analysis")
async def analyze_field(lat: float, lon: float):
    """
    Analyse a field at the given latitude/longitude using remote sensing.
    Coordinates must fall within Pakistan (23–37 °N, 60–78 °E).
    """
    if not (23 <= lat <= 37 and 60 <= lon <= 78):
        raise HTTPException(
            status_code=400,
            detail="Coordinates are outside the supported Pakistan boundary (lat 23-37, lon 60-78).",
        )
    try:
        return rs_analyzer.analyze_field(lat, lon)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
