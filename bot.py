import requests, json, asyncio, urllib3, traceback
from Crypto.Cipher import AES 
from Crypto.Util.Padding import pad, unpad 
from datetime import datetime 
from protobuf_decoder.protobuf_decoder import Parser
import aiohttp
import ssl
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============ কনফিগ লোড ============
def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return {
            "bio_text": "[B][C][00FFFF]খুব কম টাকায় [FFD700]GUILD GLORY BOT [00FFFF]ও [00FF00]220+ Like ৮ টাকা [FFFFFF]বিক্রি করা হয়, কেউ কিনতে চাইলে [FFFF00]MESSAGE দাও.[FF69B4] TELEGRAM: [FFFFFF]@FFH_PIYASH [00FF00]WP: [FFFFFF]01858370922 [FF0000](LIMITED)",
            "room_name": "[B][C][00FF00]PIYASH"
        }

CONFIG = load_config()
ROOM_NAME = CONFIG.get("room_name", "[B][C][00FF00]PIYASH")
BIO_TEXT = CONFIG.get("bio_text", "[B][C][00FFFF]Default Bio")

# ============ CONSTANTS ============
ACCOUNTS_FILE = "accounts-bd.json"

WELCOME_MSG = """[C][B][FFD700]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]        ⚡ PIYASH TCP BOT ⚡
[C][FFD700]━━━━━━━━━━━━━━━━━
[C][FFFFFF]Welcome!
[C][00FF7F]Thanks for joining my room.
[C][FFFFFF]
[C][00BFFF]Telegram
[C][00FFFF]TG: @FF_PIYASH 
[C][FFFFFF]
[C][FFD700]FREE TCP BOT Available
[C][FF8C00]Fast • Secure • Easy to Use
[C][FFFFFF]
[C][FFD700]Macth Will Start When Room Will Full
[C][FFFFFF]
[C][FF69B4]Type /help for more.
[C][FFD700]━━━━━━━━━━━━━━━━━"""

MAP_RECOMMENDATION = """[C][B][FFD700]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]     ⚡ BEST CRAFTLAND MAP ⚡
[C][FFD700]━━━━━━━━━━━━━━━━━
[C][FFFFFF]PLAY THIS CRAFTLAND MAP AND ENJOY 
[C][FFD700]━━━━━━━━━━━━━━━━━"""

MAP_CODE = "#C91E64"

# ============ AES KEYS ============
aes_key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
aes_iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ============ BOT CLASS ============
class MarufBot:
    def __init__(self, uid, password):
        self.uid = uid
        self.password = password
        self.key = None
        self.iv = None
        self.server_url = None
        self.account_id = None
        self.account_name = None
        self.jwt_token = None
        self.clan_id = None
        self.team_owner_uid = None
        self.team_chat_code = None
        self.room_id = None
        self.room_chat_id = None
        self.online_writer = None
        self.whisper_writer = None
        self.auth_token = None
        self.chat_ip = None
        self.chat_port = None
        self.online_ip = None
        self.online_port = None
        self.region = None
        self.bio_updated = False

    # ============ PACKET CREATION FUNCTIONS ============
    
    def bio_payload(self, text):
        fields = {
            2: 17,
            5: "",
            6: "",
            8: f"{text}",
            9: 1,
            11: "",
            12: ""
        }
        pyl = self.create_proto(fields).hex()
        encrypted_hex = self.encrypt_aes(pyl)
        payload = bytes.fromhex(encrypted_hex)
        return payload

    async def change_bio(self, payload, jwt_token):
        url = "https://clientbp.ggpolarbear.com/UpdateSocialBasicInfo"
    
        headers = {
            'X-Unity-Version': '2018.4.11f1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
            'Host': 'loginbp.ggpolarbear.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'Authorization': f'Bearer {jwt_token}'
        }
    
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(url, headers=headers, data=payload, verify=False, timeout=10)
            )
            if response.status_code == 200:
                print(f"[{self.uid}] Bio updated successfully!")
                return True
            else:
                print(f"[{self.uid}] Bio update failed with status: {response.status_code}")
                return False
        except Exception as e:
            print(f"[{self.uid}] Bio update error: {e}")
            return False
    
    def create_room(self, room_name, key, iv):
        fields = {
            1: 2,
            2: {
                1: 1,
                2: 15,
                3: 1,
                4: room_name,
                6: 4,
                7: 1,
                8: 1,
                9: 1,
                11: 1,
                12: 2,
                14: 36981056,
                15: [{1: "IDC3", 2: 126, 3: "ME"}, {1: "IDC4", 2: 126, 3: "BD"}]
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '0E15'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def team_join_request(self, target_uid, bot_uid, badge_value, key, iv):
        fields = {
            1: 33,
            2: {
                1: int(target_uid),
                2: "BD",
                3: 1,
                4: 1,
                5: bytes([1, 7, 9, 10, 11, 18, 25, 26, 32]),
                6: "7X MARUF",
                7: 330,
                8: 1000,
                10: "BD",
                11: bytes([
                    49, 97, 99, 52, 98, 56, 48, 101, 99, 102, 48, 52, 55, 56,
                    97, 52, 52, 50, 48, 51, 98, 102, 56, 102, 97, 99, 54, 49,
                    50, 48, 102, 53
                ]),
                12: 1,
                13: int(target_uid),
                14: {
                    1: 2203434355,
                    2: 8,
                    3: b"\x10\x15\x08\x0A\x0B\x13\x0C\x0F\x11\x04\x07\x02\x03\x0D\x0E\x12\x01\x05\x06"
                },
                16: 1,
                17: 1,
                18: 312,
                19: 46,
                23: bytes([16, 1, 24, 1]),
                24: 902037031,
                26: {},
                27: {
                    1: 11,
                    2: int(bot_uid),
                    3: 9999
                },
                28: {},
                31: {
                    1: 1,
                    2: int(badge_value)
                },
                32: int(badge_value),
                34: {
                    1: int(target_uid),
                    2: 8,
                    3: b"\x0F\x06\x15\x08\x0A\x0B\x13\x0C\x11\x04\x0E\x14\x07\x02\x01\x05\x10\x03\x0D\x12"
                }
            },
            10: "en",
            13: {
                2: 1,
                3: 1
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '0515'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def send_message(self, uid, chat_id, chat_type, message, key, iv):
        fields = {
            1: int(uid),
            2: int(chat_id),
            3: chat_type,
            4: message,
            5: int(datetime.now().timestamp()),
            9: {
                1: "7X MARUF",
                2: 902037031,
                3: 901037021,
                4: 330,
                5: 827001005,
                8: "7X MARUF",
                10: 1,
                11: 1,
                13: {1: 2},
                14: {
                    1: 12484827014,
                    2: 8,
                    3: b"\x10\x15\x08\x0A\x0B\x13\x0C\x0F\x11\x04\x07\x02\x03\x0D\x0E\x12\x01\x05\x06"
                },
                12: 0
            },
            10: "en",
            13: {3: 1}
        }
        proto = self.create_proto(fields).hex()
        proto = "080112" + self.encrypt_chat_packet(len(proto) // 2, Tp='Uid') + proto
        packet_type = '1201'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def send_json(self, uid, chat_id, chat_type, json_msg, key, iv):
        if "StickerStr" and "TitleID" in json_msg:
            show_type = 0
        else:
            show_type = 1

        fields = {
            1: int(uid),
            2: int(chat_id),
            3: chat_type,
            5: int(datetime.now().timestamp()),
            7: show_type,
            8: json_msg,
            9: {
                1: "7X MARUF",
                2: 902037031,
                3: 901037021,
                4: 330,
                5: 827001005,
                8: "7X MARUF",
                10: 1,
                11: 1,
                13: {1: 2},
                14: {
                    1: 12484827014,
                    2: 8,
                    3: b"\x10\x15\x08\x0A\x0B\x13\x0C\x0F\x11\x04\x07\x02\x03\x0D\x0E\x12\x01\x05\x06"
                },
                12: 0
            },
            10: "en",
            13: {3: 1}
        }
        proto = self.create_proto(fields).hex()
        proto = "080112" + self.encrypt_chat_packet(len(proto) // 2, Tp='Uid') + proto
        packet_type = '1201'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def exit_packet(self, uid, key, iv, exit_type=7):
        fields = {
            1: exit_type,
            2: {
                1: uid
            }
        }
        proto = self.create_proto(fields).hex()
        if exit_type == 7:
            packet_type = '0515'
        elif exit_type == 6:
            packet_type = '0E15'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def start_match(self, uid, key, iv):
        fields = {
            1: 9,
            2: {
                1: uid
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '0515'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def encrypt_chat_packet(self, H, Tp):
        e, H = [], int(H)
        while H:
            e.append((H & 0x7F) | (0x80 if H > 0x7F else 0))
            H >>= 7
        return bytes(e).hex() if Tp == 'Uid' else None

    def encrypt_aes(self, HeX):
        cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

    def create_vr(self, N):
        if N < 0:
            return ''
        H = []
        while True:
            S = N & 0x7F
            N >>= 7
            if N:
                S |= 0x80
            H.append(S)
            if not N:
                break
        return bytes(H)

    def create_variant(self, field_number, value):
        field_header = (field_number << 3) | 0
        return self.create_vr(field_header) + self.create_vr(value)

    def create_length(self, field_number, value):
        field_header = (field_number << 3) | 2
        encoded_value = value.encode() if isinstance(value, str) else value
        return self.create_vr(field_header) + self.create_vr(len(encoded_value)) + encoded_value

    def create_proto(self, fields):
        packet = bytearray()
        for field, value in fields.items():
            if isinstance(value, dict):
                nested_packet = self.create_proto(value)
                packet.extend(self.create_length(field, nested_packet))
            elif isinstance(value, int):
                packet.extend(self.create_variant(field, value))
            elif isinstance(value, str) or isinstance(value, bytes):
                packet.extend(self.create_length(field, value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        nested_packet = self.create_proto(item)
                        packet.extend(self.create_length(field, nested_packet))
        return packet

    def decode_varint(self, data, offset):
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

    def decode_protobuf(self, data):
        result = {}
        offset = 0
        data_len = len(data)
        while offset < data_len:
            header, offset = self.decode_varint(data, offset)
            if header is None:
                break
            field_number = header >> 3
            wire_type = header & 0x7
            if wire_type == 0:
                value, offset = self.decode_varint(data, offset)
                if value is not None:
                    result[field_number] = value
            elif wire_type == 2:
                length, offset = self.decode_varint(data, offset)
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

    def decode_hex(self, H):
        R = hex(H)
        F = str(R)[2:]
        if len(F) == 1:
            F = "0" + F
        return F

    def fix_packet(self, parsed_results):
        result_dict = {}
        for result in parsed_results:
            field_data = {}
            field_data['wire_type'] = result.wire_type
            if result.wire_type == "varint":
                field_data['data'] = result.data
            if result.wire_type == "string":
                field_data['data'] = result.data
            if result.wire_type == "bytes":
                field_data['data'] = result.data
            elif result.wire_type == 'length_delimited':
                field_data["data"] = self.fix_packet(result.data.results)
            result_dict[result.field] = field_data
        return result_dict

    def decode_packet(self, input_text):
        try:
            parsed_results = Parser().parse(input_text)
            parsed_results_objects = parsed_results
            parsed_results_dict = self.fix_packet(parsed_results_objects)
            json_data = json.dumps(parsed_results_dict)
            return json_data
        except Exception as e:
            print(f"[{self.uid}] Decode error: {e}")
            return None

    def create_packet(self, Pk, N, K, V):
        PkEnc = AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(Pk), 16)).hex()
        _ = self.decode_hex(int(len(PkEnc) // 2))
        if len(_) == 2:
            HeadEr = N + "000000"
        elif len(_) == 3:
            HeadEr = N + "00000"
        elif len(_) == 4:
            HeadEr = N + "0000"
        elif len(_) == 5:
            HeadEr = N + "000"
        else:
            print(f'[{self.uid}] Error Generating Packet!!')
            return b''
        return bytes.fromhex(HeadEr + _ + PkEnc)

    def auth_clan_chat(self, clan_id, clan_key, key, iv):
        fields = {
            1: 3,
            2: {
                1: int(clan_id),
                2: 1,
                4: str(clan_key)
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '1201'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def play_emote(self, uid, emote_id, key, iv):
        fields = {
            1: 21,
            2: {
                1: 804266360,
                2: 909000001,
                5: {
                    1: uid,
                    3: emote_id,
                }
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '0515'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def join_team(self, team_code, key, iv):
        fields = {
            1: 4,
            2: {
                4: bytes.fromhex("01090a0b121920"),
                5: str(team_code),
                6: 6,
                8: 1,
                9: {
                    2: 800,
                    6: 11,
                    8: "1.111.1",
                    9: 5,
                    10: 1
                }
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '0515'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def join_squad(self, bot_uid, uid, key, iv):
        fields = {
            1: 2,
            2: {
                1: int(uid),
                2: "BD",
                3: 1,
                4: 1,
                6: "7X_MARUF!!",
                7: 330,
                8: 1000,
                9: 100,
                10: "DZ",
                12: 1,
                13: int(uid),
                16: 1,
                17: {
                    2: 159,
                    4: "y[WW",
                    6: 11,
                    8: "1.111.1",
                    9: 3,
                    10: 1
                },
                18: 306,
                19: 18,
                24: 902000306,
                26: {},
                27: {
                    1: 11,
                    2: int(bot_uid),
                    3: 99999999999
                },
                28: {},
                31: {
                    1: 1,
                    2: 32768
                },
                32: 32768,
                34: {
                    1: int(bot_uid),
                    2: 8,
                    3: b"\x10\x15\x08\x0A\x0B\x13\x0C\x0F\x11\x04\x07\x02\x03\x0D\x0E\x12\x01\x05\x06"
                }
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '0515'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def accept_invite(self, uid, squad_code, key, iv):
        fields = {
            1: 4,
            2: {
                1: int(uid),
                3: int(uid),
                4: bytes.fromhex("01090a0b121920"),
                8: 1,
                9: {
                    2: 161,
                    4: "y[WW",
                    6: 11,
                    8: "1.114.18",
                    9: 3,
                    10: 1
                },
                10: str(squad_code),
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '0515'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def reject_message(self, uid, key, iv):
        banner = f"""
.






[00FF00][B]WELCOME TO 7X MARUF TCP


 """
        fields = {
            1: 5,
            2: {
                1: int(uid),
                2: 1,
                3: int(uid),
                4: banner
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '0515'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def auth_team_chat(self, owner_uid, chat_code, key, iv):
        fields = {
            1: 3,
            2: {
                1: owner_uid,
                3: "en",
                4: str(chat_code)
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '1215'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    def auth_room_chat(self, owner_uid, chat_code, key, iv):
        fields = {
            1: 3,
            2: {
                1: owner_uid,
                2: 3,
                3: "en",
                4: str(chat_code)
            }
        }
        proto = self.create_proto(fields).hex()
        packet_type = '1215'
        packet = self.create_packet(proto, packet_type, key, iv)
        return packet

    # ============ FAST LOGIN FUNCTIONS ============
    
    async def get_access_token(self, uid, password):
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-G960F Build/PIE)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close"
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
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(url, headers=headers, data=data, timeout=10)
            )
            if response.status_code != 200:
                print(f"❌ [{self.uid}] Token error: {response.status_code}")
                return None, None, None
            json_data = response.json()
            return json_data["access_token"], json_data["open_id"], int(json_data["platform"])
        except Exception as e:
            print(f"❌ [{self.uid}] Token request error: {e}")
            return None, None, None

    def major_login_payload(self, access_token, open_id, platform_type):
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
            91: {
                10: 52
            },
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
        pyl = self.create_proto(fields).hex()
        payload = bytes.fromhex(self.encrypt_aes(pyl))
        return payload

    async def major_login(self, payload):
        url = "https://loginbp.ggpolarbear.com/MajorLogin"
        headers = {
            'X-Unity-Version': '2018.4.11f1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
            'Host': 'loginbp.ggpolarbear.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(url, headers=headers, data=payload, timeout=10)
            )
            if response.status_code != 200:
                print(f"❌ [{self.uid}] MajorLogin failed: {response.status_code}")
                return None
            response_content = response.content
            json_response = self.decode_protobuf(response_content)
            return json_response
        except Exception as e:
            print(f"❌ [{self.uid}] MajorLogin error: {e}")
            return None

    async def get_login_data(self, jwt_token, payload):
        url = f"{self.server_url}/GetLoginData"
        headers = {
            'X-Unity-Version': '2018.4.11f1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
            'Host': 'loginbp.ggpolarbear.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'Authorization': f'Bearer {jwt_token}'
        }
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(url, headers=headers, data=payload, timeout=10)
            )
            if response.status_code != 200:
                print(f"❌ [{self.uid}] GetLoginData failed: {response.status_code}")
                return None
            response_content = response.content
            json_response = self.decode_protobuf(response_content)
            return json_response
        except Exception as e:
            print(f"❌ [{self.uid}] GetLoginData error: {e}")
            return None

    def create_auth_token(self, account_id, jwt_token, timestamp, key, iv):
        uid_hex = hex(account_id)[2:]
        uid_length = len(uid_hex)
        K = bytes.fromhex(key)
        V = bytes.fromhex(iv)
        encrypted_timestamp = self.decode_hex(timestamp)
        encrypted_account_token = jwt_token.encode().hex()
        encrypted_packet = AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(encrypted_account_token), 16)).hex()
        encrypted_packet_length = hex(len(encrypted_packet) // 2)[2:]
        if uid_length == 9:
            headers = '0000000'
        elif uid_length == 8:
            headers = '00000000'
        elif uid_length == 10:
            headers = '000000'
        elif uid_length == 7:
            headers = '000000000'
        else:
            print(f'[{self.uid}] Unexpected length')
            headers = '0000000'
        return f"0115{headers}{uid_hex}{encrypted_timestamp}00000{encrypted_packet_length}{encrypted_packet}"

    # ============ SEND PACKET FUNCTIONS ============
    
    async def send_packet(self, packet, packet_type):
        if packet_type == 'chat':
            if self.whisper_writer:
                self.whisper_writer.write(packet)
                await self.whisper_writer.drain()
                return True
            else:
                return False
        if packet_type == 'online':
            if self.online_writer:
                self.online_writer.write(packet)
                await self.online_writer.drain()
                return True
            else:
                return False
        return True

    # ============ FAST TCP CONNECTIONS ============
    
    async def tcp_online(self, reconnect_delay=0.5):
        key = bytes.fromhex(self.key)
        iv = bytes.fromhex(self.iv)
    
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.online_ip, int(self.online_port))
                self.online_writer = writer
                bytes_payload = bytes.fromhex(self.auth_token)
                self.online_writer.write(bytes_payload)
                await self.online_writer.drain()
                            
                await asyncio.sleep(0.3)
                room_packet = self.create_room(ROOM_NAME, key, iv)
                await self.send_packet(room_packet, 'online')
            
                # Bio update - only once
                if not self.bio_updated:
                    bio_payload_data = self.bio_payload(BIO_TEXT)
                    bio_status = await self.change_bio(bio_payload_data, self.jwt_token)
                    if bio_status:
                        print(f"[{self.uid}] BIO UPDATE SUCCESS")
                        self.bio_updated = True
                    else:
                        print(f"[{self.uid}] BIO UPDATE FAILED")
                
                while True:
                    data2 = await reader.read(9999)
                    if not data2:
                        break
                    
                    # Fast decode for room creation response
                    if data2.hex().startswith('0e00'):
                        data2_hex = data2.hex()[10:]
                        json_response = self.decode_packet(data2_hex)
                        if json_response:
                            json_data = json.loads(json_response)
                            
                            room_id = None
                            room_chat_id = None
                            try:
                                if "5" in json_data:
                                    outer = json_data["5"]["data"]
                                    if "1" in outer:
                                        room_id = outer["1"]["data"] if isinstance(outer["1"], dict) else outer["1"]
                                    if "36" in outer:
                                        room_chat_id = outer["36"]["data"] if isinstance(outer["36"], dict) else outer["36"]
                                    elif "40" in outer:
                                        room_chat_id = outer["40"]["data"] if isinstance(outer["40"], dict) else outer["40"]
                                    if not room_id or not room_chat_id:
                                        if "2" in outer and isinstance(outer["2"], dict):
                                            inner = outer["2"]["data"] if "data" in outer["2"] else outer["2"]
                                            if "1" in inner:
                                                room_id = inner["1"]["data"] if isinstance(inner["1"], dict) else inner["1"]
                                            if "36" in inner:
                                                room_chat_id = inner["36"]["data"] if isinstance(inner["36"], dict) else inner["36"]
                                            elif "40" in inner:
                                                room_chat_id = inner["40"]["data"] if isinstance(inner["40"], dict) else inner["40"]
                            except Exception as e:
                                print(f'[{self.uid}] extract error: {e}')
                            
                            if room_id and room_chat_id:
                                room_chat_packet = self.auth_room_chat(room_id, room_chat_id, key, iv)
                                await self.send_packet(room_chat_packet, 'chat')
                                print(f'[{self.uid}] Room Chat Sent')
                                
                                await asyncio.sleep(0.2)
                                                                
                                # Send welcome messages with minimal delays
                                await asyncio.sleep(0.2)
                                message_packet = self.send_message(self.account_id, room_id, 3, WELCOME_MSG, key, iv)
                                await self.send_packet(message_packet, 'chat')
                                
                                await asyncio.sleep(0.2)
                                message_packet = self.send_message(self.account_id, room_id, 3, MAP_RECOMMENDATION, key, iv)
                                await self.send_packet(message_packet, 'chat')
                                
                                await asyncio.sleep(0.2)
                                json_message = f'{{"WorkshopCode":"{MAP_CODE}","type":"UGCMapShare"}}'
                                json_packet = self.send_json(self.account_id, room_id, 3, json_message, key, iv)
                                await self.send_packet(json_packet, 'chat')
                                print(f'[{self.uid}] Welcome messages sent fast!')
                            else:
                                print(f"[{self.uid}] room_id or room_chat_id not found")

                    # Fast squad invite handling
                    if data2.hex().startswith('0500'):
                        data2_hex = data2.hex()[10:]
                        json_response = self.decode_packet(data2_hex)
                        if json_response:
                            json_data = json.loads(json_response)
                            
                            # Check for team join request
                            try:
                                if '5' in json_data:
                                    data = json_data['5']['data']
                                    uid = None
                                    code = None
                                    if '1' in data:
                                        uid = data['1']['data'] if isinstance(data['1'], dict) else data['1']
                                    if '8' in data:
                                        code = data['8']['data'] if isinstance(data['8'], dict) else data['8']
                                    
                                    if uid and code:
                                        join_request_packet = self.team_join_request(uid, self.account_id, 32768, key, iv)
                                        await self.send_packet(join_request_packet, 'online')
                                    
                                    join_uid = None
                                    join_code = None
                                    if '2' in data and '1' in data['2']['data']:
                                        join_uid = data['2']['data']['1']['data'] if isinstance(data['2']['data']['1'], dict) else data['2']['data']['1']
                                    if '7' in data:
                                        join_code = data['7']['data'] if isinstance(data['7'], dict) else data['7']
                                    
                                    if join_uid and join_code and len(str(join_code)) > 20:
                                        join_squad_packet = self.join_squad(self.account_id, join_uid, key, iv)
                                        await self.send_packet(join_squad_packet, 'online')
                                        await asyncio.sleep(0.05)
                                        reject_message_packet = self.reject_message(join_uid, key, iv)
                                        await self.send_packet(reject_message_packet, 'online')
                                        await asyncio.sleep(0.05)
                                        accept_invite_packet = self.accept_invite(join_uid, join_code, key, iv)
                                        await self.send_packet(accept_invite_packet, 'online')
                                        print(f'[{self.uid}] INVITE ACCEPTED')
                            except Exception as e:
                                print(f'[{self.uid}] extract error: {e}')
                            
                            # Team chat
                            try:
                                if '5' in json_data:
                                    data = json_data['5']['data']
                                    team_owner_uid = None
                                    team_chat_code = None
                                    if '1' in data:
                                        team_owner_uid = data['1']['data'] if isinstance(data['1'], dict) else data['1']
                                    if '17' in data:
                                        team_chat_code = data['17']['data'] if isinstance(data['17'], dict) else data['17']
                                    
                                    if team_owner_uid and team_chat_code:
                                        await asyncio.sleep(0.05)
                                        team_chat_packet = self.auth_team_chat(team_owner_uid, team_chat_code, key, iv)
                                        await self.send_packet(team_chat_packet, 'chat')
                                        print(f'[{self.uid}] Team Chat Sent')
                            except Exception as e:
                                print(f'[{self.uid}] extract error: {e}')
                            
                self.online_writer.close()
                await self.online_writer.wait_closed()
                self.online_writer = None
            except Exception as e:
                print(f"[{self.uid}] Online error with {self.online_ip}:{self.online_port} - {e}")
                self.online_writer = None
            await asyncio.sleep(reconnect_delay)

    async def tcp_chat(self, ready_event, reconnect_delay=0.5):
        key = bytes.fromhex(self.key)
        iv = bytes.fromhex(self.iv)
        
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.chat_ip, int(self.chat_port))
                self.whisper_writer = writer
                bytes_payload = bytes.fromhex(self.auth_token)
                await self.send_packet(bytes_payload, 'chat')
                ready_event.set()
                
                print(f"[{self.uid}] TCP CHAT connected")
                
                if self.clan_id:
                    print(f"[{self.uid}] CLAN_ID: {self.clan_id}")
                    clan_chat_packet = self.auth_clan_chat(self.clan_id, 0, key, iv)
                    await self.send_packet(clan_chat_packet, 'chat')
                    print(f"[{self.uid}] BOT CONNECTED WITH CLAN CHAT")

                while True:
                    data = await reader.read(9999)
                    if not data:
                        break
                    
                    if data.hex().startswith("120000"):
                        data_hex = data.hex()[10:]
                        json_response = self.decode_packet(data_hex)
                        if not json_response:
                            continue
                        json_data = json.loads(json_response)
                        
                        if "5" in json_data:
                            message = json_data["5"]["data"].get("4", {}).get("data", "")
                            nickname = json_data["5"]["data"]["9"]["data"]["1"]["data"]
                            uid = json_data["5"]["data"]["1"]["data"]
                            chat_type = json_data["5"]["data"].get("3", {}).get("data", 0)
                            
                            if chat_type == 2:
                                chat_id = uid
                            else:
                                chat_id = json_data["5"]["data"]["2"]["data"]
                            
                            input_message = json_data["5"]["data"].get("4", {}).get("data", "").lower()
                            input_json = json_data["5"]["data"].get("8", {}).get("data", "")
                            
                            # Auto-reply to JSON messages
                            if "type" in input_json and uid != self.account_id:
                                json_packet = self.send_json(self.account_id, chat_id, chat_type, input_json, key, iv)
                                await self.send_packet(json_packet, 'chat')
                            
                            # Fast command handling
                            if input_message.startswith("/start"):
                                start_packet = self.start_match(uid, key, iv)
                                await self.send_packet(start_packet, 'online')
                                message = "[00FF00]Starting Match"
                                message_packet = self.send_message(self.account_id, chat_id, chat_type, message, key, iv)
                                await self.send_packet(message_packet, 'chat')
                                message = "[FF0000]ROOM STARTING ERROR!, [00FF00]TEAM MATCH STARTED!"
                                message_packet = self.send_message(self.account_id, chat_id, chat_type, message, key, iv)
                                await self.send_packet(message_packet, 'chat')
                            
                            if input_message.startswith("/help") or input_message.startswith("help"):
                                help_msg = """[C][B][00FFFF]📋 MARUF BOT COMMANDS
[C][B][FFD700]━━━━━━━━━━━━━━━━━
[C][00FFFF]/help [32CD32]→ [FFFFFF]Show this help menu
[C][00FFFF]/admin [32CD32]→ [FFFFFF]Developer info
[C][00FFFF]/social [32CD32]→ [FFFFFF]Social media links
[C][00FFFF]/store [32CD32]→ [FFFFFF]Store menu
[C][00FFFF]/tcp [32CD32]→ [FFFFFF]TCP Bot prices
[C][00FFFF]/glory [32CD32]→ [FFFFFF]Glory Bot prices
[C][00FFFF]/map [32CD32]→ [FFFFFF]Best Craftland Map
[C][00FFFF]/start [32CD32]→ [FFFFFF]Start the match
[C][B][FFD700]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]🤖 Bot by: [FFD700]@FF7X_MARUF"""
                                message_packet = self.send_message(self.account_id, chat_id, chat_type, help_msg, key, iv)
                                await self.send_packet(message_packet, 'chat')
                            
                            if input_message.startswith("/admin") or input_message.startswith("admin"):
                                admin_msg = """[C][B][00FFFF]DEVELOPER INFORMATION
[C][B][FFFF00]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]Developer : [FFFF00]KING 7X MARUF 
[C][B][00FFFF]TELEGRAM  : [FFFF00]@FF_MARUF
[C][B][00FFFF]TIKTOK  : [FFFF00]@FF7X_MARUF
[C][B][00FFFF]YOUTUBE  : [FFFF00]7X MARUF 
[C][B][FFFF00]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]Thanks for [FFFF00]Using This Bot!"""
                                message_packet = self.send_message(self.account_id, chat_id, chat_type, admin_msg, key, iv)
                                await self.send_packet(message_packet, 'chat')
                            
                            if input_message.startswith("/social") or input_message.startswith("social"):
                                social_msg = """[C][FFD700]━━━━━━━━━━━━━━━━━
[C][B][00BFFF]⚡ MARUF SOCIAL LINKS ⚡
[C][FFD700]━━━━━━━━━━━━━━━━━
[C][00BFFF]Telegram: @FF_MARUF
[C][00FFFF]TG Channel: @FF7X_MARUF 
[C][00FFFF]TG Group: @FF7X_MARUF_HELP
[C][FF69B4]TikTok: @FF7X_MARUF 
[C][FF69B4]YouTube: 7X MARUF 
[C][FFD700]━━━━━━━━━━━━━━━━━"""
                                message_packet = self.send_message(self.account_id, chat_id, chat_type, social_msg, key, iv)
                                await self.send_packet(message_packet, 'chat')
                            
                            if input_message.startswith("/store") or input_message.startswith("store"):
                                store_msg = """[C][B][FFD700]   MARUF BOT STORE
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[FFFFFF]/tcp     [32CD32]→ [FFFFFF]TCP Bot Prices
[FFFFFF]/glory   [32CD32]→ [FFFFFF]Glory Bot Prices
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]Contact TELEGRAM: [FFFF00]@FF_MARUF 
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]Contact TIKTOK: [FFFF00]@FF7X_MARUF"""
                                message_packet = self.send_message(self.account_id, chat_id, chat_type, store_msg, key, iv)
                                await self.send_packet(message_packet, 'chat')
                            
                            if input_message.startswith("/tcp") or input_message.startswith("tcp"):
                                tcp_msg = """[C][B][39FF14]⚡  TCP BOT PRICE LIST
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[C][00FFFF]MARUF TCP BOT
[C][FFFFFF]➥ 1 MONTH [32CD32]→ [FFFF00]200 BDT ($2) [FF0000]10%Off
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]Contact TELEGRAM: [FFFF00]@FF_MARUF 
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]Contact TIKTOK: [FFFF00]@FF7X_MARUF"""
                                message_packet = self.send_message(self.account_id, chat_id, chat_type, tcp_msg, key, iv)
                                await self.send_packet(message_packet, 'chat')
                            
                            if input_message.startswith("/glory") or input_message.startswith("glory"):
                                glory_msg = """[C][B][FFD700]GL🤞ORY BOT PRICE LIST
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[C][FFFFFF]1 Ba🤞sic [32CD32]→ [FFFF00]200 T🤞K
[C][FFFFFF]2 Ba🤞sic [32CD32]→ [FFFF00]400 T🤞K
[C][FFFFFF]5 Ba🤞sic [32CD32]→ [FFFF00]1,000 T🤞K
[C][FFFFFF]10 Ba🤞sic [32CD32]→ [FFFF00]2,000 T🤞K
[C][FFFFFF]20 Ba🤞sic [32CD32]→ [FFFF00]4,000 T🤞K
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]Contact TELEGRAM: [FFFF00]@FF_MARUF 
[C][B][00FF7F]━━━━━━━━━━━━━━━━━
[C][B][00FFFF]Contact TIKTOK: [FFFF00]@FF7X_MARUF"""
                                message_packet = self.send_message(self.account_id, chat_id, chat_type, glory_msg, key, iv)
                                await self.send_packet(message_packet, 'chat')
                            
                            if input_message.startswith("/map") or input_message.startswith("map"):
                                json_message = f'{{"WorkshopCode":"{MAP_CODE}","type":"UGCMapShare"}}'
                                json_packet = self.send_json(self.account_id, chat_id, chat_type, json_message, key, iv)
                                await self.send_packet(json_packet, 'chat')
                            
                self.whisper_writer.close()
                await self.whisper_writer.wait_closed()
                self.whisper_writer = None
            except Exception as e:
                print(f"[{self.uid}] Chat error with {self.chat_ip}:{self.chat_port} - {e}")
                self.whisper_writer = None
            await asyncio.sleep(reconnect_delay)

    # ============ FAST LOGIN ============
    
    async def login(self):
        """Login and get all required data"""
        access_token, open_id, platform_type = await self.get_access_token(self.uid, self.password)
        if not access_token:
            return False
        
        print(f"✅ [{self.uid}] Access token received")
        
        payload = self.major_login_payload(access_token, open_id, platform_type)
        major_login_response = await self.major_login(payload)
        
        if not major_login_response:
            print(f"❌ [{self.uid}] MajorLogin failed!")
            return False
            
        self.jwt_token = major_login_response.get(8)
        self.server_url = major_login_response.get(10)
        self.region = major_login_response.get(2)
        self.account_id = major_login_response.get(1)
        self.key = major_login_response.get(22)
        self.iv = major_login_response.get(23)
        timestamp = major_login_response.get(21)
        
        if not self.jwt_token or not self.server_url:
            print(f"❌ [{self.uid}] Invalid MajorLogin response!")
            return False
        
        login_data_response = await self.get_login_data(self.jwt_token, payload)
        if not login_data_response:
            print(f"❌ [{self.uid}] GetLoginData failed!")
            return False
            
        self.account_name = login_data_response.get(4)
        chat_server = login_data_response.get(32)
        online_server = login_data_response.get(14)
        
        if not chat_server or not online_server:
            print(f"❌ [{self.uid}] Invalid server data!")
            return False
        
        self.chat_ip, self.chat_port = chat_server.split(":")
        self.online_ip, self.online_port = online_server.split(":")
        
        self.clan_id = login_data_response.get(20)
        self.auth_token = self.create_auth_token(self.account_id, self.jwt_token, timestamp, self.key, self.iv)
        
        print(f"✅ [{self.uid}] Login successful! Bot: {self.account_name}")
        print(f"📡 [{self.uid}] Online: {self.online_ip}:{self.online_port}")
        print(f"💬 [{self.uid}] Chat: {self.chat_ip}:{self.chat_port}")
        print(f"🌍 [{self.uid}] Region: {self.region}")
        return True

    async def run(self):
        """Main loop for this bot"""
        while True:
            try:
                print(f"🔄 [{self.uid}] Starting bot...")
                if await self.login():
                    ready_event = asyncio.Event()
                    chat_task = asyncio.create_task(self.tcp_chat(ready_event))
                    await ready_event.wait()
                    await asyncio.sleep(0.3)
                    online_task = asyncio.create_task(self.tcp_online())
                    await asyncio.gather(chat_task, online_task)
                else:
                    print(f"❌ [{self.uid}] Login failed, retrying in 5 seconds...")
                    await asyncio.sleep(5)
            except asyncio.TimeoutError:
                print(f"⚠️ [{self.uid}] Token expired, restarting...")
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"❌ [{self.uid}] Bot error: {e}")
                traceback.print_exc()
                await asyncio.sleep(3)

# ============ MAIN ============
async def main():
    """Load accounts and start all bots"""
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
    except FileNotFoundError:
        print(f"❌ {ACCOUNTS_FILE} not found!")
        print("📝 Create accounts-bd.json with format:")
        print('[{"uid": 123456789, "password": "password"}]')
        return
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {ACCOUNTS_FILE}: {e}")
        return
    
    if not accounts:
        print("❌ No accounts found in JSON file!")
        return
    
    print(f"✅ Loaded {len(accounts)} accounts from {ACCOUNTS_FILE}")
    
    tasks = []
    for i, acc in enumerate(accounts):
        uid = acc.get('uid')
        password = acc.get('password')
        if not uid or not password:
            print(f"⚠️ Skipping invalid account: {acc}")
            continue
        
        bot = MarufBot(uid, password)
        tasks.append(asyncio.create_task(bot.run()))
        # Stagger start to avoid rate limiting
        if i < len(accounts) - 1:
            await asyncio.sleep(0.5)
    
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 All bots stopped by user")
    except Exception as e:
        print(f"❌ Fatal Error: {e}")