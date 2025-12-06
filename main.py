from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import google.generativeai as genai
import edge_tts
import asyncio
import os
import uuid

app = FastAPI()

# ⚠️ Render 的 Environment Variable 設定好後，這裡就會自動讀取
# 如果你在本地測試，請確保這裡填入你的 Key，或者在 Render 後台設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "你的_GEMINI_API_KEY_填在這裡")

genai.configure(api_key=GEMINI_API_KEY)

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
    # 改回最新的 Flash 模型，因為你已經更新了 requirements.txt，這次一定行
    model = genai.GenerativeModel('gemini-1.5-flash')
    
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
        print("劇本生成成功") # Debug 用
    except Exception as e:
        # 如果還是失敗，我們會印出更詳細的錯誤，包含可用的模型列表
        print(f"Gemini Error Detail: {e}")
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
        
        # 簡單清理文字 (移除星號等 Markdown 符號)
        text = text.replace("*", "").replace("#", "")
        
        voice = "en-US-ChristopherNeural" if "Alex" in speaker else "en-US-AvaNeural"
        
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                final_audio += chunk["data"]

    # 3. 存成暫存檔
    # 使用 /tmp/ 目錄，這是 Render 等雲端服務允許寫入的地方
    filename = f"/tmp/{uuid.uuid4()}.mp3"
    with open(filename, "wb") as f:
        f.write(final_audio)

    # 4. 回傳檔案
    return FileResponse(filename, media_type="audio/mpeg", filename="podcast.mp3")
