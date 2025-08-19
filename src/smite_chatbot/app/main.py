import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the SMITE 2 Streamlit chatbot app"""
    
    # Get the project root and ensure it's in PYTHONPATH
    project_root = Path(__file__).parent.parent.parent.parent
    src_path = project_root / "src"
    
    # Set up environment
    env = os.environ.copy()
    current_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{current_path}" if current_path else str(src_path)
    
    # Get the path to the streamlit app
    app_path = Path(__file__).parent / "streamlit_app.py"
    
    # Launch streamlit with proper environment
    cmd = [
        sys.executable, 
        "-m", "streamlit", "run", 
        str(app_path),
        "--server.port", "8501",
        "--server.address", "localhost"
    ]
    
    print("🚀 Starting SMITE 2 Chatbot...")
    print(f"📱 App will be available at: http://localhost:8501")
    print("💡 Make sure you have OPENAI_API_KEY environment variable set")
    
    try:
        subprocess.run(cmd, env=env, cwd=project_root)
    except KeyboardInterrupt:
        print("\n👋 Shutting down SMITE 2 Chatbot...")
    except Exception as e:
        print(f"❌ Error launching app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()