from flask import Flask, render_template, jsonify, request, send_file
import subprocess
import os
import json
import time
import threading

app = Flask(__name__)

# গ্লোবাল ভেরিয়েবল
processes = {}

def read_stats():
    try:
        with open("stats.json", "r") as f:
            return json.load(f)
    except:
        return {"success": 0, "fail": 0}

def get_account_count():
    try:
        with open("accounts-bd.json", "r") as f:
            return len(json.load(f))
    except:
        return 0

def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return {"bio_text": "", "room_name": ""}

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=2)

def start_bot_process():
    if 'bot' in processes and processes['bot'].poll() is None:
        return False
    proc = subprocess.Popen(['python3', 'bot.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    processes['bot'] = proc
    return True

def stop_bot_process():
    if 'bot' in processes and processes['bot'].poll() is None:
        processes['bot'].terminate()
        time.sleep(1)
        if processes['bot'].poll() is None:
            processes['bot'].kill()
        del processes['bot']
        return True
    return False

def start_gen_process():
    if 'generator' in processes and processes['generator'].poll() is None:
        return False
    proc = subprocess.Popen(['python3', 'generator.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    processes['generator'] = proc
    return True

def stop_gen_process():
    if 'generator' in processes and processes['generator'].poll() is None:
        processes['generator'].terminate()
        time.sleep(1)
        if processes['generator'].poll() is None:
            processes['generator'].kill()
        del processes['generator']
        return True
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    gen_running = 'generator' in processes and processes['generator'].poll() is None
    bot_running = 'bot' in processes and processes['bot'].poll() is None
    stats_data = read_stats()
    config = load_config()
    return jsonify({
        'generator': gen_running,
        'bot': bot_running,
        'total': get_account_count(),
        'success': stats_data.get('success', 0),
        'fail': stats_data.get('fail', 0),
        'bio': config.get('bio_text', ''),
        'room': config.get('room_name', '')
    })

@app.route('/api/start_gen', methods=['POST'])
def start_gen():
    if start_gen_process():
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/api/stop_gen', methods=['POST'])
def stop_gen():
    stopped = stop_gen_process()
    if stopped:
        # জেনারেটর বন্ধ করলেই বট অটো স্টার্ট হবে
        time.sleep(0.5)
        if 'bot' in processes and processes['bot'].poll() is None:
            stop_bot_process()
            time.sleep(0.5)
        start_bot_process()
    return jsonify({'status': 'stopped' if stopped else 'not_running'})

@app.route('/api/start_bot', methods=['POST'])
def start_bot():
    if start_bot_process():
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/api/stop_bot', methods=['POST'])
def stop_bot():
    if stop_bot_process():
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'not_running'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    file.save('accounts-bd.json')
    return jsonify({'status': 'uploaded'})

@app.route('/api/download')
def download_file():
    return send_file('accounts-bd.json', as_attachment=True)

@app.route('/api/update_bio', methods=['POST'])
def update_bio():
    data = request.json
    new_bio = data.get('bio')
    apply_to = data.get('apply_to')  # 'new' or 'all'
    
    if not new_bio:
        return jsonify({'error': 'Bio required'}), 400
    
    config = load_config()
    config['bio_text'] = new_bio
    save_config(config)
    
    if apply_to == 'all':
        # বট রিস্টার্ট করলে সবাই নতুন বায়ো নেবে
        stop_bot_process()
        time.sleep(1)
        start_bot_process()
        return jsonify({'status': 'applied_to_all'})
    else:
        return jsonify({'status': 'saved_for_new'})

@app.route('/api/update_room', methods=['POST'])
def update_room():
    data = request.json
    new_room = data.get('room_name')
    apply_to = data.get('apply_to')  # 'new' or 'all'
    
    if not new_room:
        return jsonify({'error': 'Room name required'}), 400
    
    config = load_config()
    config['room_name'] = new_room
    save_config(config)
    
    if apply_to == 'all':
        # বট রিস্টার্ট করলে নতুন রুম নাম কাজ করবে
        stop_bot_process()
        time.sleep(1)
        start_bot_process()
        return jsonify({'status': 'applied_to_all'})
    else:
        return jsonify({'status': 'saved_for_new'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)