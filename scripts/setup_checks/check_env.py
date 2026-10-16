import sys
import shutil
import subprocess

def check_command(command_name: str, min_version_desc: str = "") -> bool:
    path = shutil.which(command_name)
    if path:
        print(f"  [OK] {command_name} found at: {path}")
        return True
    else:
        print(f"  [FAIL] {command_name} NOT found in PATH. {min_version_desc}")
        return False

def check_system():
    print("=" * 60)
    print("REEL STUDIO Environment Diagnostic Check")
    print("=" * 60)

    # 1. Python Version
    print("\n[1/4] Checking Python version:")
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro}")
    if v.major == 3 and v.minor >= 10:
        print("  [OK] Python version is >= 3.10")
    else:
        print("  [WARN] Python 3.10+ is recommended.")

    # 2. FFmpeg & FFprobe (Crucial for video processing)
    print("\n[2/4] Checking Media Tools:")
    ffmpeg_ok = check_command("ffmpeg", "Required for video rendering and audio extraction.")
    ffprobe_ok = check_command("ffprobe", "Required for video metadata validation.")

    # 3. Flutter SDK
    print("\n[3/4] Checking Flutter Web SDK:")
    flutter_ok = check_command("flutter", "Required for the Flutter Web frontend.")

    # 4. Git
    print("\n[4/4] Checking Version Control:")
    git_ok = check_command("git")

    print("\n" + "=" * 60)
    if ffmpeg_ok and ffprobe_ok and flutter_ok and git_ok:
        print("ALL SYSTEM REQUIREMENTS SATISFIED. Ready for development.")
    else:
        print("SOME DEPENDENCIES ARE MISSING. Please review above failures.")
    print("=" * 60)

if __name__ == "__main__":
    check_system()