#!/usr/bin/env python3
# ============================================================
#  build.py - בנה EXE עם PyInstaller
# ============================================================

import subprocess
import sys
import os

def build_launcher():
    """בנה launcher.exe"""
    print("🔨 Building launcher.exe...")
    cmd = [
        sys.executable, "-m", "pyinstaller",
        "--onefile",
        "--windowed",
        "--icon=launcher.py",  # or add real icon file
        "--name=ControlIt",
        "launcher.py"
    ]
    result = subprocess.run(cmd)
    return result.returncode == 0

def build_login():
    """בנה login.exe"""
    print("🔨 Building login.exe...")
    cmd = [
        sys.executable, "-m", "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=ControlIt-Login",
        "login_page.py"
    ]
    result = subprocess.run(cmd)
    return result.returncode == 0

def cleanup():
    """נקה build artifacts"""
    print("🧹 Cleaning up build artifacts...")
    import shutil
    for folder in ["build", "__pycache__"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"  Removed {folder}/")

if __name__ == "__main__":
    print("=" * 50)
    print("  ControlIt Build System")
    print("=" * 50)

    # בנה launcher
    if not build_launcher():
        print("❌ Launcher build failed")
        sys.exit(1)
    print("✅ Launcher built: dist/ControlIt.exe")

    # בנה login
    if not build_login():
        print("❌ Login build failed")
        sys.exit(1)
    print("✅ Login built: dist/ControlIt-Login.exe")

    # נקה
    cleanup()

    print("\n" + "=" * 50)
    print("✅ Build complete!")
    print("📦 Executables in: dist/")
    print("=" * 50)
