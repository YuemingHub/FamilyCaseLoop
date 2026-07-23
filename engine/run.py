"""启动器：仅监听 127.0.0.1:8000（本地个人工具，不对外暴露）。

用法：
    pip install -r requirements.txt
    python run.py
或：
    uvicorn app.api:app --host 127.0.0.1 --port 8000
"""
import uvicorn
from app.api import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
