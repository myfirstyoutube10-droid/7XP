import requests, json, hmac, hashlib, time, random, urllib3, ipaddress, os, sys, threading
from Crypto.Cipher import AES 
from Crypto.Util.Padding import pad, unpad 
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
from colorama import init, Fore, Back, Style

# Initialize Colorama
init(autoreset=True)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

aes_key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
aes_iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

HEX_KEY = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
API_KEY  = bytes.fromhex(HEX_KEY)

# ==================== GLOBAL VARIABLES ====================
accounts_list = []
accounts_lock = threading.Lock()
success_count = 0
success_lock = threading.Lock()
fail_count = 0
fail_lock = threading.Lock()
save_queue = queue.Queue()
save_thread_running = True

# Thread-safe print lock
print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    """Thread-safe print with color"""
    with print_lock:
        print(*args, **kwargs)

# ==================== IP ROTATOR ====================
class IPRotator:
    REGION_IP_CIDRS = {
        "BD": [
            "27.147.128.0/17", "37.111.192.0/19", "49.0.32.0/20", "59.152.96.0/20",
            "114.130.0.0/17", "115.127.0.0/17", "119.30.32.0/20", "123.49.0.0/18",
            "103.220.220.0/22", "103.108.140.0/22", "103.242.20.0/22"
        ],
        "IND": [
            "1.6.0.0/15", "1.38.0.0/15", "14.96.0.0/15", "27.4.0.0/14", "27.56.0.0/13"
        ],
        "ID": [
            "36.64.0.0/11", "101.255.0.0/16", "103.10.60.0/22", "114.120.0.0/13"
        ],
        "TH": [
            "1.46.0.0/15", "27.55.0.0/16", "49.228.0.0/15", "101.108.0.0/15"
        ],
        "VN": [
            "1.52.0.0/14", "14.160.0.0/11", "27.64.0.0/12", "113.160.0.0/12"
        ],
        "PK": [
            "39.32.0.0/11", "111.68.96.0/19", "182.176.0.0/12"
        ],
        "ME": [
            "2.88.0.0/13", "5.100.0.0/14", "31.166.0.0/15", "37.104.0.0/13"
        ],
        "BR": [
            "177.0.0.0/13", "186.192.0.0/12", "189.0.0.0/11", "200.96.0.0/12"
        ],
        "EU": [
            "2.16.0.0/12", "5.144.0.0/14", "31.40.0.0/14", "46.16.0.0/14"
        ],
        "CIS": [
            "2.92.0.0/14", "5.136.0.0/13", "31.128.0.0/12", "46.0.0.0/12"
        ],
        "NA": [
            "3.0.0.0/9", "8.0.0.0/12", "12.0.0.0/10", "24.0.0.0/10"
        ],
        "SAC": [
            "186.0.0.0/10", "190.0.0.0/11", "200.0.0.0/11"
        ],
        "TW": [
            "1.160.0.0/12", "36.224.0.0/12", "114.24.0.0/12", "118.160.0.0/12"
        ]
    }
    _cache = {}
    
    @classmethod
    def get_random_ip(cls, region="BD"):
        region = region.upper()
        if region not in cls._cache:
            cidrs = cls.REGION_IP_CIDRS.get(region, ["27.0.0.0/8"])
            hosts = []
            for cidr in cidrs:
                try:
                    net = ipaddress.ip_network(cidr, strict=False)
                    for _ in range(3):
                        ip_int = int(net.network_address) + random.randint(1, 2**(32-net.prefixlen)-2)
                        hosts.append(str(ipaddress.IPv4Address(ip_int)))
                except:
                    continue
            cls._cache[region] = hosts if hosts else [f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"]
        return random.choice(cls._cache[region])
    
    @classmethod
    def get_ip_headers(cls, region="BD"):
        """Get IP headers for requests"""
        ip = cls.get_random_ip(region)
        return {
            'X-Forwarded-For': ip,
            'X-Real-IP': ip,
            'Client-IP': ip
        }

# ==================== NAME GENERATOR ====================
def generate_random_name():
    SUPERSCRIPTS = ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹']
    SUBSCRIPTS = ['₀', '₁', '₂', '₃', '₄', '₅', '₆', '₇', '₈', '₉']
    use_super = random.choice([True, False])
    numbers = SUPERSCRIPTS if use_super else SUBSCRIPTS
    suffix = ''.join(random.choice(numbers) for _ in range(6))
    prefixes = ["MARUF", "M4RUF"]
    prefix = random.choice(prefixes)
    return f"{prefix}({suffix}"

# ==================== PROTOBUF FUNCTIONS ====================
def create_vr(N):
    if N < 0: return b''
    H = []
    while True:
        S = N & 0x7F
        N >>= 7
        if N: S |= 0x80
        H.append(S)
        if not N: break
    return bytes(H)

def create_variant(field_number, value):
    field_header = (field_number << 3) | 0
    return create_vr(field_header) + create_vr(value)

def create_length(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return create_vr(field_header) + create_vr(len(encoded_value)) + encoded_value

def create_proto(fields):
    packet = bytearray()    
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_packet = create_proto(value)
            packet.extend(create_length(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(create_variant(field, value))           
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(create_length(field, value))           
    return packet

def decode_varint(data, offset):
    result = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        result |= (byte & 0x7F) << shift
        offset += 1
        if not (byte & 0x80):
            return result, offset
        shift += 7
    return None, offset

def decode_protobuf(data):
    result = {}
    offset = 0
    data_len = len(data)
    while offset < data_len:
        header, offset = decode_varint(data, offset)
        if header is None:
            break
        field_number = header >> 3
        wire_type = header & 0x7
        if wire_type == 0:
            value, offset = decode_varint(data, offset)
            if value is not None:
                result[field_number] = value
        elif wire_type == 2:
            length, offset = decode_varint(data, offset)
            if length is None:
                break
            value = data[offset:offset + length]
            offset += length
            try:
                result[field_number] = value.decode('utf-8')
            except:
                result[field_number] = value.hex()
        elif wire_type == 1:
            offset += 8
        elif wire_type == 3:
            offset += 4
        else:
            break
    return result

def encrypt_aes(HeX):
    cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

# ==================== ACCOUNT FUNCTIONS ====================
def register_account(password, region="BD"):
    url = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
    ip_headers = IPRotator.get_ip_headers(region)
    
    payload_json = {"app_id": 100067, "client_type": 2, "password": password, "source": 2}
    payload = json.dumps(payload_json, separators=(',', ':'))
    signature = hmac.new(API_KEY, payload.encode(), hashlib.sha256).hexdigest()
    timestamp = str(int(time.time() * 1000) + random.randint(-999, 999))
    
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-G960F Build/PIE)",
        "Authorization": f"Signature {signature}",
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "Connection": "Keep-Alive",
        "Host": "100067.connect.garena.com",
        "X-Garena-Timestamp": timestamp,
        #**ip_headers
    }
    try:
        response = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get("code") == 0 and "data" in json_data:
                uid = json_data["data"]["uid"]
                return uid, password
        return None, None
    except:
        return None, None

def get_access_token(uid, password, region="BD"):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    ip_headers = IPRotator.get_ip_headers(region)
    
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-G960F Build/PIE)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        #**ip_headers
    }
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"
    }
    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        if response.status_code == 200:
            json_data = response.json()
            access_token = json_data.get("access_token")
            open_id = json_data.get("open_id")
            platform = json_data.get("platform")
            platform_type = int(platform) if platform else 4
            return access_token, open_id, platform_type
        return None, None, None
    except:
        return None, None, None

def major_register(access_token, open_id, name, LANG='en', region="BD"):
    url = "https://loginbp.ggpolarbear.com/MajorRegister"
    ip_headers = IPRotator.get_ip_headers(region)
    
    keystream = [0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37, 0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37,
                 0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37, 0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30]
    encoded_open_id = ""
    for i, ch in enumerate(open_id):
        encoded_open_id += chr(ord(ch) ^ keystream[i % len(keystream)])
    field14 = encoded_open_id.encode('latin1')
    
    payload_fields = {
        1: name,
        2: access_token,
        3: open_id,
        5: 102000007,
        6: 4,
        7: 1,
        13: 1,
        14: field14,
        15: LANG,
        16: 1,
        17: 1
    }
    proto_bytes = create_proto(payload_fields)
    proto_hex = proto_bytes.hex()
    payload = bytes.fromhex(encrypt_aes(proto_hex))
    
    headers = {
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "Host": "loginbp.ggpolarbear.com",
        "ReleaseVersion": "OB54",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
        "X-GA": "v1 1",
        "X-Unity-Version": "2018.4.",
        #**ip_headers
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        return decode_protobuf(response.content)
    except:
        return {}

def major_login_payload(access_token, open_id, platform_type):
    fields = {
        3: str(datetime.now())[:-7],
        4: "free fire",
        5: 1,
        7: "1.128.14",
        8: "Android OS 14 / API-34 (UKQ1.230917.001/V816.0.1.0.UMWJPSB)",
        9: "Handheld",
        11: "WIFI",
        12: 1708,
        13: 750,
        14: "440",
        15: "ARM64 FP ASIMD AES | 2208 | 8",
        16: 3479,
        17: "Adreno (TM) 613",
        18: "OpenGL ES 3.2 V@0615.74 (GIT@dad4038ba6, If56d4a5bb8, 1690544947) (Date:07/28/23)",
        19: "Google|27ed2fb9-7ace-4842-9ebf-0d42c7140201",
        20: "103.13.194.32",
        21: "en",
        22: open_id,
        23: platform_type,
        24: "Handheld",
        25: "google G011A",
        26: "BD",
        29: access_token,
        30: 1,
        42: "WIFI",
        57: "7428b253defc164018c604a1ebbfebdf",
        60: 110509,
        61: 29537,
        62: 697,
        64: 29665,
        65: 110509,
        66: 29665,
        67: 110509,
        73: 2,
        74: "/data/app/~~XPfhCrDak-UWHWhp3ymWJg==/com.dts.freefireth-am4qxn2SuG3LmR020vv1zQ==/lib/arm64",
        76: 1,
        77: "4c322aeb56444feaa151d1ea91a8f7f2|/data/app/~~XPfhCrDak-UWHWhp3ymWJg==/com.dts.freefireth-am4qxn2SuG3LmR020vv1zQ==/base.apk",
        78: 3,
        79: 2,
        81: "64",
        83: "2019120828",
        85: 3,
        86: "OpenGLES2",
        87: 4095,
        88: platform_type,
        90: "Pokhara",
        91: {10: 52},
        92: 21559,
        93: "android",
        94: "KqsHT8i1nPYybHwReglCq3THRFio2Q9U/EYoQzoAUmdpAf9+6ZixKBvdt1f8xFUBDN0+XKgZZfNC4rEtfHn3Vt/jEyg=",
        95: 111207,
        96: '{"cur_rate":[60,48,30,90],"support_etc2":false}',
        97: 1,
        99: f"{platform_type}",
        100: f"{platform_type}",
        102: "16544d12040f0f0263",
        103: 1
    }
    pyl = create_proto(fields).hex()
    payload = bytes.fromhex(encrypt_aes(pyl))
    return payload

def major_login(payload, region="BD"):
    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    ip_headers = IPRotator.get_ip_headers(region)
    
    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'OB54',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': 'loginbp.ggpolarbear.com',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        #**ip_headers
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        return decode_protobuf(response.content)
    except:
        return {}

def get_login_data(server_url, jwt_token, payload, region="BD"):
    url = f"{server_url}/GetLoginData"
    ip_headers = IPRotator.get_ip_headers(region)
    
    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'OB54',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': 'loginbp.ggpolarbear.com',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        'Authorization': f'Bearer {jwt_token}',
        #**ip_headers
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        return decode_protobuf(response.content)
    except:
        return {}

# ==================== SAVE THREAD ====================
def save_worker():
    """Background thread to handle saving"""
    global save_thread_running
    while save_thread_running:
        try:
            item = save_queue.get(timeout=1)
            if item is None:
                break
            
            with accounts_lock:
                try:
                    temp_filename = "accounts-bd.temp.json"
                    with open(temp_filename, 'w', encoding='utf-8') as f:
                        json.dump(accounts_list, f, indent=2, ensure_ascii=False)
                    
                    if os.path.exists("accounts-bd.json"):
                        os.replace(temp_filename, "accounts-bd.json")
                    else:
                        os.rename(temp_filename, "accounts-bd.json")
                    
                    # স্ট্যাটাস সেভ
                    with open("stats.json", 'w') as sf:
                        json.dump({"success": success_count, "fail": fail_count}, sf)
                    
                except Exception as e:
                    safe_print(f"{Fore.RED}⚠️ Save error: {e}{Style.RESET_ALL}")
            
            save_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            safe_print(f"{Fore.RED}⚠️ Save worker error: {e}{Style.RESET_ALL}")
            continue

def queue_save():
    save_queue.put(True)

def save_accounts(filename="accounts-bd.json"):
    global accounts_list
    try:
        with accounts_lock:
            if os.path.exists(filename):
                backup_filename = f"{filename}.backup"
                try:
                    os.replace(filename, backup_filename)
                except:
                    pass
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(accounts_list, f, indent=2, ensure_ascii=False)
            
            # স্ট্যাটাস সেভ
            with open("stats.json", 'w') as sf:
                json.dump({"success": success_count, "fail": fail_count}, sf)
        return True
    except Exception as e:
        safe_print(f"{Fore.RED}❌ Save error: {e}{Style.RESET_ALL}")
        return False

def load_accounts(filename="accounts-bd.json"):
    global accounts_list
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    accounts_list = data
                    return accounts_list
    except Exception as e:
        safe_print(f"{Fore.YELLOW}⚠️ Load error: {e}{Style.RESET_ALL}")
        backup_filename = f"{filename}.backup"
        if os.path.exists(backup_filename):
            try:
                with open(backup_filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        accounts_list = data
                        safe_print(f"{Fore.GREEN}✅ Recovered from backup: {len(accounts_list)} accounts{Style.RESET_ALL}")
                        return accounts_list
            except:
                pass
    return []

def account_exists(uid):
    global accounts_list
    with accounts_lock:
        for acc in accounts_list:
            if str(acc.get('uid')) == str(uid) or str(acc.get('account_id')) == str(uid):
                return True
    return False

def get_next_count():
    global success_count
    with success_lock:
        success_count += 1
        return success_count

def create_full_account(thread_id, region="BD", max_retries=2):
    global fail_count
    
    for attempt in range(max_retries):
        try:
            password = f"MARUF_{random.randint(1000, 9999)}"
            name = generate_random_name()
            
            register_uid, password = register_account(password, region)
            if not register_uid:
                continue
            
            access_token, open_id, platform_type = get_access_token(register_uid, password, region)
            if not access_token:
                continue
            
            reg_response = major_register(access_token, open_id, name, region=region)
            if 3 not in reg_response:
                continue
            
            account_id = reg_response[3]
            
            payload = major_login_payload(access_token, open_id, platform_type)
            
            login_response = major_login(payload, region)
            if 8 not in login_response:
                continue
            
            jwt_token = login_response[8]
            
            if 10 in login_response:
                server_url = login_response[10]
                login_data = get_login_data(server_url, jwt_token, payload, region)
                
                if not account_exists(register_uid) and not account_exists(account_id):
                    count = get_next_count()
                    
                    account = {
                        'uid': register_uid,
                        'password': password,
                        'name': name,
                        'account_id': account_id,
                        'region': region,
                        'jwt_token': jwt_token[:20] + '...',
                        'created_at': datetime.now().isoformat()
                    }
                    
                    with accounts_lock:
                        accounts_list.append(account)
                    
                    queue_save()
                    
                    safe_print(f"{Fore.GREEN}✅ [T{thread_id}] #{count} UID: {register_uid} | Account ID: {account_id} | {name}{Style.RESET_ALL}")
                    return account
                else:
                    safe_print(f"{Fore.YELLOW}⚠️ [T{thread_id}] Account already exists: {register_uid}{Style.RESET_ALL}")
                    return None
            
        except Exception as e:
            safe_print(f"{Fore.RED}❌ [T{thread_id}] Error: {e}{Style.RESET_ALL}")
            continue
    
    with fail_lock:
        fail_count += 1
    return None

def worker(thread_id, region="BD"):
    while True:
        try:
            create_full_account(thread_id, region)
        except Exception as e:
            safe_print(f"{Fore.RED}⚠️ [T{thread_id}] Worker error: {e}{Style.RESET_ALL}")
            continue

def display_banner():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}   🔥 MARUF ACCOUNT GENERATOR (MULTI-THREADED) 🔥{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}   • MajorLogin & GetLoginData Included{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}   • Thread-Safe Saving with Queue{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}   • Auto-Backup & Recovery{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}   • IP Rotation Enabled{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}   • No Data Loss{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}Press CTRL+C to stop{Style.RESET_ALL}\n")

def main():
    global success_count, fail_count, accounts_list, save_thread_running
    
    display_banner()
    
    load_accounts()
    safe_print(f"{Fore.CYAN}📂 Loaded {len(accounts_list)} existing accounts{Style.RESET_ALL}")
    
    success_count = len(accounts_list)
    safe_print(f"{Fore.CYAN}📊 Starting count: {success_count}{Style.RESET_ALL}")
    
    save_thread = threading.Thread(target=save_worker, daemon=True)
    save_thread.start()
    
    NUM_THREADS = 50
    safe_print(f"{Fore.GREEN}🚀 Starting {NUM_THREADS} threads...{Style.RESET_ALL}\n")
    
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        for i in range(NUM_THREADS):
            region = "BD"
            futures.append(executor.submit(worker, i, region))
        
        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            print(f"\n\n{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{Style.BRIGHT}   📊 GENERATION SUMMARY{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{Style.BRIGHT}   ✅ Success: {success_count}{Style.RESET_ALL}")
            print(f"{Fore.RED}{Style.BRIGHT}   ❌ Failed: {fail_count}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{Style.BRIGHT}   📁 Total accounts: {len(accounts_list)}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            
            print(f"\n{Fore.GREEN}💾 Saving final data...{Style.RESET_ALL}")
            save_accounts()
            print(f"{Fore.GREEN}✅ Done!{Style.RESET_ALL}")
            sys.exit(0)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Stopped by user{Style.RESET_ALL}")
        save_accounts()
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}❌ Fatal error: {e}{Style.RESET_ALL}")
        save_accounts()
        sys.exit(1)