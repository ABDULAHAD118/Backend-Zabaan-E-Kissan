# Testing Guide for Chat API with Field Analysis

## Prerequisites

1. Make sure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure your environment variables are set (especially for MongoDB and HuggingFace API if needed)

## Starting the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

## Testing Methods

### Method 1: Using the Test Script (Recommended)

Run the provided test script:

```bash
python test_chat_api.py
```

This will test:
- Health check
- Chat with location (Urdu)
- Chat with location (English)
- Chat without location (normal chat)
- Chat history

### Method 2: Using cURL

#### Test 1: Chat with Location (Urdu)
```bash
curl -X POST "http://localhost:8000/chat/test-thread-1" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "میرے کھیت کا تجزیہ کریں 31.5497 74.3436"
  }'
```

#### Test 2: Chat with Location (English)
```bash
curl -X POST "http://localhost:8000/chat/test-thread-2" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze my field at 24.8607 67.0011"
  }'
```

#### Test 3: Normal Chat (No Location)
```bash
curl -X POST "http://localhost:8000/chat/test-thread-3" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the best time to plant wheat in Pakistan?"
  }'
```

#### Test 4: Get Chat History
```bash
curl -X GET "http://localhost:8000/chat/test-thread-1/history"
```

#### Test 5: Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

### Method 3: Using Python Requests

```python
import requests

# Chat with location
response = requests.post(
    "http://localhost:8000/chat/test-thread-1",
    json={"query": "میرے کھیت کا تجزیہ کریں 31.5497 74.3436"}
)
print(response.json())
```

### Method 4: Using FastAPI Docs (Interactive)

1. Start the server
2. Open your browser and go to: `http://localhost:8000/docs`
3. Find the `/chat/{thread_id}` endpoint
4. Click "Try it out"
5. Enter:
   - `thread_id`: `test-123`
   - Request body:
     ```json
     {
       "query": "Analyze my field at 31.5497 74.3436"
     }
     ```
6. Click "Execute"

## Test Cases

### Test Case 1: Location Detection
**Input:** Message with coordinates
```json
{
  "query": "31.5497 74.3436"
}
```
**Expected:** Field analysis data should be included in the response

### Test Case 2: Mixed Content
**Input:** Message with text and coordinates
```json
{
  "query": "میرے کھیت کا تجزیہ کریں 31.5497 74.3436"
}
```
**Expected:** Friendly analysis of the field in Urdu

### Test Case 3: Invalid Coordinates
**Input:** Coordinates outside Pakistan range
```json
{
  "query": "40.7128 -74.0060"
}
```
**Expected:** Normal chat response (no field analysis, as coordinates are invalid)

### Test Case 4: No Location
**Input:** Message without coordinates
```json
{
  "query": "What crops grow best in Punjab?"
}
```
**Expected:** Normal chatbot response without field analysis

## Expected Response Format

When location is detected and field analysis is performed:

```json
{
  "response": "آپ کے کھیت کی تفصیلات...",
  "field_analysis": {
    "status": "success",
    "location": {
      "lat": 31.5497,
      "lon": 74.3436,
      "region": "Punjab"
    },
    "ndvi": {...},
    "soil_moisture": {...},
    "weather": {...},
    "rainfall": {...},
    "analysis": "...",
    "timestamp": "2025-01-XX XX:XX:XX"
  }
}
```

## Troubleshooting

1. **Server not starting:**
   - Check MongoDB connection
   - Verify environment variables
   - Check port 8000 is available

2. **Field analysis not working:**
   - Check internet connection (NASA API requires internet)
   - Verify coordinates are in Pakistan range (23-37 lat, 60-78 lon)
   - Check logs for errors

3. **Chatbot not responding:**
   - Verify HuggingFace API token (if required)
   - Check model availability
   - Review server logs

## Location Coordinates for Testing

Use these valid Pakistan coordinates for testing:

- **Lahore**: `31.5497 74.3436`
- **Karachi**: `24.8607 67.0011`
- **Islamabad**: `33.6844 73.0479`
- **Faisalabad**: `31.4504 73.1350`
- **Multan**: `30.1575 71.5249`
- **Peshawar**: `34.0151 71.5249`

## Notes

- Field analysis may take 10-30 seconds due to NASA API calls
- Responses are in the same language as the input query
- Each `thread_id` maintains its own conversation history

