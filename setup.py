import subprocess
import sys
import os

def install_requirements():
    try:
        print("[*] Installing required Python packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("[*] All required packages installed successfully.")
    except subprocess.CalledProcessError:
        print("[!] Failed to install some packages. Please check your internet connection or requirements.txt.")
        sys.exit(1)

def run_app():
    print("[*] Launching VChanger.py...")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "VChanger.py")])

if __name__ == "__main__":
    install_requirements()
    run_app()
