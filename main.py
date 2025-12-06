from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import google.generativeai as genai
import edge_tts
import asyncio
import os
import uuid

app = FastAPI()

# ⚠️ 為了安全，建議把 API Key 放在環境變數，但在這裡為了測試方便先填入
# 在 Render 上架時，請在 Environment Variables 設定 GEMINI_API_KEY
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "你的_GEMINI_API_KEY_填在這裡")

genai.configure(api_key="AIzaSyCrv_ONdVXXasLupFA4Dv0K7NaFc_xups0")

@app.get("/")
def read_root():
    return {"status": "My AI Radio is Online!"}

@app.post("/generate_podcast")
async def generate_podcast(topic: str):
    """
    接收一個 topic (主題)，回傳一個 mp3 檔案
    """
    print(f"收到主題請求: {topic}")
    
    # 1. 生成劇本
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    Write a fun, energetic podcast dialogue between Alex (Male) and Sarah (Female).
    Topic: {topic}
    Length: Very short, about 100 words.
    Format exactly like:
    Alex: [text]
    Sarah: [text]
    """
    
    try:
        response = model.generate_content(prompt)
        script = response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini Error: {str(e)}")

    # 2. 生成語音
    final_audio = b""
    lines = script.split('\n')
    
    for line in lines:
        if ':' not in line: continue
        parts = line.split(':', 1)
        if len(parts) < 2: continue
        
        speaker = parts[0].strip()
        text = parts[1].strip()
        
        # 簡單清理文字
        text = text.replace("*", "")
        
        voice = "en-US-ChristopherNeural" if "Alex" in speaker else "en-US-AvaNeural"
        
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                final_audio += chunk["data"]

    # 3. 存成暫存檔
    filename = f"{uuid.uuid4()}.mp3"
    with open(filename, "wb") as f:
        f.write(final_audio)

    # 4. 回傳檔案

    return FileResponse(filename, media_type="audio/mpeg", filename="podcast.mp3")
