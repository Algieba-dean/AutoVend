"""
Run script for AutoVend application.
"""
import uvicorn
from app.config import HOST, PORT, DEBUG

if __name__ == "__main__":
    print("Starting AutoVend API server...")
    print(f"Debug mode: {'enabled' if DEBUG else 'disabled'}")
    print(f"Server running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info"
    ) 