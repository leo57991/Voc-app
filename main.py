from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import google.generativeai as genai
import edge_tts
import asyncio
import os
import uuid

app = FastAPI()

# ⚠️ 請確認 Render 環境變數有設定 GEMINI_API_KEY
# 或是為了測試，暫時將 Key 填入下方的引號中 (注意安全)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "你的_AIza_開頭的Key")
genai.configure(api_key=GEMINI_API_KEY)

@app.get("/")
def read_root():
    return {"status": "Radio Server Online"}

# 🛠️ 診斷工具：用瀏覽器打開 /list_models 可以看到所有可用的模型
@app.get("/list_models")
def list_models():
    try:
        model_list = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_list.append(m.name)
        return {"available_models": model_list}
    except Exception as e:
        return {"error": str(e)}

@app.post("/generate_podcast")
async def generate_podcast(topic: str):
    """
    接收 topic，生成劇本，轉成語音，回傳 MP3
    """
    print(f"收到主題: {topic}")
    
    # 1. 生成劇本 (使用 gemini-2.0-flash)
    try:
        # 🌟 修正點：根據你的 list_models 結果，我們改用 gemini-2.0-flash
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        Write a fun, energetic podcast dialogue between Alex (Male) and Sarah (Female).
        Topic: {topic}
        Length: Very short, about 100 words.
        Format exactly like:
        Alex: [text]
        Sarah: [text]
        Do not include any actions like [laughs] or (intro music).
        """
        
        response = model.generate_content(prompt)
        script = response.text
        print("劇本生成成功")
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini Error: {str(e)}")

    # 2. 生成語音 (Edge TTS)
    final_audio = b""
    lines = script.split('\n')
    
    for line in lines:
        if ':' not in line: continue
        parts = line.split(':', 1)
        if len(parts) < 2: continue
        
        speaker = parts[0].strip()
        text = parts[1].strip()
        
        # 移除可能殘留的星號或標記
        text = text.replace("*", "").strip()
        
        if not text: continue
        
        # 分配聲音
        voice = "en-US-ChristopherNeural" if "Alex" in speaker else "en-US-AvaNeural"
        
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                final_audio += chunk["data"]

    # 3. 存成暫存檔 (使用 /tmp/ 避免權限問題)
    filename = f"/tmp/{uuid.uuid4()}.mp3"
    with open(filename, "wb") as f:
        f.write(final_audio)

    # 4. 回傳檔案給 App
    return FileResponse(filename, media_type="audio/mpeg", filename="podcast.mp3")
