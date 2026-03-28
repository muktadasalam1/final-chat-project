import subprocess
import time
import socket
import os
import sys
import re
import webbrowser
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_color(text, color=Colors.GREEN):
    print(f"{color}{text}{Colors.END}")

def get_local_ip_from_ipconfig():
    try:
        result = subprocess.run(["ipconfig"], capture_output=True, text=True, shell=True)
        output = result.stdout
        
        patterns = [
            r'IPv4 Address[.\s]+:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',
            r'IPv4 Address[.\s]+\.\s*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',
            r'Dirección IPv4[.\s]+\.\s*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)'
        ]
        
        ips = []
        for pattern in patterns:
            matches = re.findall(pattern, output)
            ips.extend(matches)
        
        valid_ips = []
        for ip in ips:
            if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                valid_ips.append(ip)
        
        if valid_ips:
            return valid_ips[0]
        
        for ip in ips:
            if ip != '127.0.0.1':
                return ip
        
        return '127.0.0.1'
    except Exception as e:
        print_color(f"Error getting IP: {e}", Colors.RED)
        return '127.0.0.1'

def get_local_ip_socket():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def get_local_ip():
    ip = get_local_ip_from_ipconfig()
    if ip == '127.0.0.1':
        socket_ip = get_local_ip_socket()
        if socket_ip:
            ip = socket_ip
    return ip

def create_qr_code(url, filename="qr_code.png"):
    try:
        import qrcode
        from PIL import Image
        
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filename)
        
        print_color(f"QR Code saved: {filename}", Colors.GREEN)
        
        try:
            os.startfile(filename)
        except:
            pass
        
        return True
    except ImportError:
        print_color("Installing qrcode...", Colors.YELLOW)
        subprocess.run([sys.executable, "-m", "pip", "install", "qrcode", "pillow", "--quiet"])
        import qrcode
        from PIL import Image
        return create_qr_code(url, filename)
    except Exception as e:
        print_color(f"QR Code error: {e}", Colors.RED)
        return False

def get_cloudflare_url(cloudflared_path):
    try:
        process = subprocess.Popen(
            [str(cloudflared_path / "cloudflared.exe"), "tunnel", "--url", "http://localhost:8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        public_url = None
        for _ in range(30):
            try:
                line = process.stderr.readline()
                if line:
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        public_url = match.group()
                        break
            except:
                pass
            time.sleep(1)
        
        return public_url, process
    except Exception as e:
        return None, None

def main():
    print_color("\n" + "="*60, Colors.BLUE)
    print_color("Starting Chat Application", Colors.BOLD)
    print_color("="*60, Colors.BLUE)
    
    #backend_path = Path(r"/home/mln/Projects/web/test/chat-app-v2/final-chat-project/file/chat_project/backend")
    #cloudflared_path ="cloudflared"
    backend_path = Path(r"C:\Users\pc\Desktop\file\chat_project\backend")
    cloudflared_path = Path(r"C:\Users\pc\Desktop\file\cloudflared")
    
    
    if not backend_path.exists():
        print_color(f"Path not found: {backend_path}", Colors.RED)
        return
    
    if cloudflared_path is None:
        print_color("cloudflared not found in PATH", Colors.RED)
        return
    
    # you don't need this in linux, but in windows we need to check if the executable exists
    if not cloudflared_path.exists():
        print_color(f"Path not found: {cloudflared_path}", Colors.RED)
        return
    
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:8000"
    
    print_color(f"\nLocal IP detected: {local_ip}", Colors.GREEN)
    print_color(f"Local URL: {local_url}", Colors.GREEN)
    
    print_color("\n[1/3] Starting FastAPI server...", Colors.YELLOW)
    os.chdir(backend_path)


    #this won't work in linux, but in windows we need to open a new terminal to run the server
    fastapi_process = subprocess.Popen(
        ["cmd", "/k", "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"],
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )


    #we can just run the server in the same terminal in linux
    #fastapi_process = subprocess.Popen(
    #    ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    #)

    time.sleep(3)
    print_color("FastAPI server running on port 8000", Colors.GREEN)
    
    print_color("\n[2/3] Starting Cloudflare Tunnel...", Colors.YELLOW)
    #use 
    #os.chdir(cloudflared_path)
    #when you have the cloudflared executable in a specific folder, 
    # but if you have it as a cli tool then you don't need to call os.chdir 
    
    public_url, tunnel_process = get_cloudflare_url(cloudflared_path)
    
    print_color("\n" + "="*60, Colors.GREEN)
    print_color("Services Running Successfully", Colors.BOLD)
    print_color("="*60, Colors.GREEN)
    
    print_color(f"\nLocal URL (same network):", Colors.BLUE)
    print_color(f"   {local_url}", Colors.GREEN)
    
    if public_url:
        print_color(f"\nPublic URL (anywhere):", Colors.BLUE)
        print_color(f"   {public_url}", Colors.GREEN)
        
        try:
            import pyperclip
            pyperclip.copy(public_url)
            print_color(f"Public URL copied to clipboard", Colors.GREEN)
        except:
            pass
    else:
        print_color("\nStarting Cloudflare Tunnel in separate window...", Colors.YELLOW)
        subprocess.Popen(
            'start "Cloudflare Tunnel" cmd /k .\\cloudflared.exe tunnel --url http://localhost:8000',
            shell=True
        )
        public_url = input("\nEnter the Cloudflare URL (or press Enter to skip): ").strip()
    
    print_color("\n[3/3] Creating QR Codes...", Colors.YELLOW)
    
    if public_url:
        print_color(f"\nQR Code for Public URL:", Colors.BLUE)
        create_qr_code(public_url, "public_qr.png")
    
    print_color(f"\nQR Code for Local URL:", Colors.BLUE)
    create_qr_code(local_url, "local_qr.png")
    
    print_color("\nOpening browser...", Colors.YELLOW)
    webbrowser.open(local_url)
    
    print_color("\n" + "="*60, Colors.GREEN)
    print_color("Application Ready!", Colors.BOLD)
    print_color("="*60, Colors.GREEN)
    
    print_color("\nInstructions:", Colors.BLUE)
    print_color("   1. Scan QR code with your phone", Colors.GREEN)
    print_color("   2. Login or create an account", Colors.GREEN)
    print_color("   3. Start chatting", Colors.GREEN)
    
    print_color("\nPress Enter to stop all services...", Colors.RED)
    input()
    
    print_color("\nStopping services...", Colors.RED)
    fastapi_process.terminate()
    try:
        tunnel_process.terminate()
    except:
        pass
    print_color("All services stopped", Colors.GREEN)

if __name__ == "__main__":
    main()