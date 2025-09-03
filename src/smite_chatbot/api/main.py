import uvicorn
import sys
import os
from pathlib import Path

def main():
    """Launch the SMITE 2 FastAPI chatbot API"""
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("   Please set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Check storage directory
    storage_dir = Path("storage")
    if not storage_dir.exists():
        print("❌ Storage directory not found!")
        print("   Please run data population first: uv run smite-populate")
        sys.exit(1)
    
    print("🚀 Starting SMITE 2 Chatbot API...")
    print("📱 API will be available at:")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - ReDoc: http://localhost:8000/redoc")
    print("   - Health Check: http://localhost:8000/health")
    print("   - Chat Endpoint: POST http://localhost:8000/chat")
    print()
    print("💡 Example curl command:")
    print('   curl -X POST "http://localhost:8000/chat" \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"message": "What is Achilles ultimate ability?"}\'')
    print()
    
    try:
        # Run the FastAPI app with uvicorn
        uvicorn.run(
            "smite_chatbot.api.app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Set to True for development
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down SMITE 2 Chatbot API...")
    except Exception as e:
        print(f"❌ Error launching API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()