from flask import Flask, render_template_string, request, url_for, redirect, send_file
from flask_socketio import SocketIO
import sqlite3
from datetime import datetime
import pandas as pd
import io
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tuku_emas_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

if not os.path.exists('databases'):
    os.makedirs('databases')

def get_db_path(branch_name):
    safe_branch = branch_name.strip().lower().replace(" ", "_")
    return os.path.join('databases', f'db_{safe_branch}.db')

def init_db(branch_name):
    db_path = get_db_path(branch_name)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            nama TEXT,
            hp TEXT,
            layanan TEXT,
            tanggal TEXT,
            status TEXT,
            call_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_next_queue_number(branch_name):
    db_path = get_db_path(branch_name)
    init_db(branch_name)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM visitors")
    count = cursor.fetchone()[0]
    conn.close()
    return f"A-{count + 1:03d}"

# Halaman Utama Pilihan Cabang Tuku Emas Indonesia
@app.route('/')
def home_branches():
    return render_template_string('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        body { font-family: 'Poppins', sans-serif; background-color: #f4f4f9; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; width: 90%; max-width: 520px; border-top: 6px solid #d4af37; }
        h2 { color: #333; margin-bottom: 5px; }
        p { color: #666; font-size: 13px; margin-bottom: 25px; }
        .branch-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; max-height: 420px; overflow-y: auto; text-align: left; padding-right: 5px; }
        .branch-btn { display: block; background: #fff9db; color: #b8860b; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 13px; border: 1px solid #ffe066; transition: 0.3s; text-align: center; }
        .branch-btn:hover { background: #d4af37; color: white; transform: translateY(-2px); }
        .trial-btn { background: #e8f5e9; color: #2e7d32; border-color: #c8e6c9; }
        .trial-btn:hover { background: #4caf50; color: white; }
    </style>
    <div class="container">
        <h2>Tuku Emas Indonesia</h2>
        <p>Silakan pilih outlet cabang Anda:</p>
        <div class="branch-grid">
            <a href="/cabang/pusat-trial" class="branch-btn trial-btn">🛠️ Pusat (Trial)</a>
            <a href="/cabang/otista" class="branch-btn">📍 Otista</a>
            <a href="/cabang/kopo" class="branch-btn">📍 Kopo</a>
            <a href="/cabang/kircon" class="branch-btn">📍 Kircon</a>
            <a href="/cabang/kudus" class="branch-btn">📍 Kudus</a>
            <a href="/cabang/semarang" class="branch-btn">📍 Semarang</a>
            <a href="/cabang/yogya" class="branch-btn">📍 Yogya</a>
            <a href="/cabang/surabaya-1" class="branch-btn">📍 Surabaya 1</a>
            <a href="/cabang/surabaya-2" class="branch-btn">📍 Surabaya 2</a>
            <a href="/cabang/sidoarjo" class="branch-btn">📍 Sidoarjo</a>
            <a href="/cabang/malang" class="branch-btn">📍 Malang</a>
            <a href="/cabang/solo" class="branch-btn">📍 Solo</a>
            <a href="/cabang/cirebon" class="branch-btn">📍 Cirebon</a>
            <a href="/cabang/cikarang" class="branch-btn">📍 Cikarang</a>
            <a href="/cabang/mojokerto" class="branch-btn">📍 Mojokerto</a>
        </div>
    </div>
    ''')

# 1. Halaman Layar TV per Cabang
@app.route('/cabang/<branch>/tv')
def tv_display(branch):
    branch_title = branch.replace('-', ' ').title()
    return render_template_string('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;900&display=swap');
        body { font-family: 'Poppins', sans-serif; background-color: #121212; color: white; margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .top-bar { background: #1a1a1a; border-bottom: 2px solid #d4af37; padding: 12px 30px; display: flex; align-items: center; justify-content: space-between; }
        .top-bar img { height: 70px; filter: drop-shadow(0 2px 8px rgba(212,175,55,0.3)); }
        .top-bar h1 { color: #d4af37; font-size: 18px; margin: 0; letter-spacing: 1px; text-transform: uppercase; font-weight: 700; }
        
        .main-container { display: flex; flex: 1; padding: 20px; gap: 20px; height: calc(100vh - 98px); box-sizing: border-box; }
        
        .left-column { flex: 3.5; display: flex; flex-direction: column; gap: 15px; }
        .video-box { flex: 1.5; background: #1e1e1e; border: 2px solid #333; border-radius: 20px; overflow: hidden; display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 30px rgba(0,0,0,0.3); position: relative; }
        .video-box video { width: 100%; height: 100%; object-fit: cover; }
        
        .primary-display { flex: 1.2; background: #1e1e1e; border: 3px solid #d4af37; border-radius: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; box-shadow: 0 10px 30px rgba(212, 175, 55, 0.15); padding: 5px; }
        .queue-number { font-size: 105px; color: #d4af37; margin: 0; font-weight: 900; line-height: 1; text-shadow: 2px 4px 15px rgba(0,0,0,0.6); }
        .counter-name { font-size: 28px; margin: 8px 0 2px 0; color: #ffffff; font-weight: 700; }
        .info-detail { font-size: 17px; color: #f1c40f; background: rgba(212, 175, 55, 0.15); padding: 6px 20px; border-radius: 8px; margin-top: 5px; border: 1px solid rgba(212,175,55,0.3); }
        
        .side-panel { flex: 1.2; background: #1e1e1e; border: 2px solid #333; border-radius: 20px; padding: 18px; display: flex; flex-direction: column; box-sizing: border-box; max-width: 340px; }
        .side-panel h3 { color: #d4af37; margin-top: 0; font-size: 15px; border-bottom: 2px solid #333; padding-bottom: 6px; }
        .queue-list-box { flex: 1; overflow-y: auto; margin-top: 6px; }
        .queue-item { background: #262626; padding: 6px 10px; border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid #d4af37; }
        .queue-item-num { font-size: 14px; font-weight: bold; color: #d4af37; }
        .queue-item-name { font-size: 11px; color: #ccc; }
        
        #audio-status {
            position: absolute; bottom: 15px; right: 20px; background: rgba(212, 175, 55, 0.9);
            color: #121212; padding: 10px 18px; border-radius: 6px; font-size: 14px; font-weight: bold;
            z-index: 100; box-shadow: 0 4px 10px rgba(0,0,0,0.4); transition: opacity 0.5s ease; cursor: pointer;
        }
    </style>
    
    <div id="audio-status">Tekan TOMBOL APA SAJA di Remot TV untuk Aktifkan Suara 🔊</div>

    <div class="top-bar">
        <img src="{{ url_for('static', filename='logo.png') }}" alt="Logo Tuku Emas">
        <h1>Tuku Emas Indonesia (''' + branch_title + ''') — Terima Harga Tinggi</h1>
    </div>

    <div class="main-container">
        <div class="left-column">
            <div class="video-box">
                <video id="promoVideo" autoplay loop muted playsinline>
                    <source src="{{ url_for('static', filename='promo.mp4') }}" type="video/mp4">
                </video>
            </div>
            <div class="primary-display">
                <h1 class="queue-number" id="q">A-000</h1>
                <h2 class="counter-name" id="c">Loket -</h2>
                <div class="info-detail" id="info">Nasabah: - | Layanan: -</div>
            </div>
        </div>
        <div class="side-panel">
            <h3>Antrean Berikutnya</h3>
            <div class="queue-list-box" id="next-queue-list">
                <div style="color: #777; text-align: center; margin-top: 30px; font-size: 12px;">Belum ada antrean menunggu</div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io();
        const branch = "''' + branch + '''";
        socket.emit('join_branch', { branch: branch });

        const videoElement = document.getElementById('promoVideo');
        const statusBadge = document.getElementById('audio-status');

        function aktifkanSuaraRemot() {
            videoElement.muted = false;
            videoElement.volume = 1.0;
            
            let initVoice = new SpeechSynthesisUtterance("Sistem siap");
            initVoice.lang = 'id-ID';
            initVoice.rate = 1.0;
            window.speechSynthesis.speak(initVoice);

            statusBadge.style.opacity = '0';
            setTimeout(() => { statusBadge.style.display = 'none'; }, 500);

            window.removeEventListener('keydown', handleRemoteKey);
            window.removeEventListener('click', aktifkanSuaraRemot);
            window.removeEventListener('touchstart', aktifkanSuaraRemot);
        }

        function handleRemoteKey(e) {
            aktifkanSuaraRemot();
        }

        window.addEventListener('keydown', handleRemoteKey);
        window.addEventListener('click', aktifkanSuaraRemot);
        window.addEventListener('touchstart', aktifkanSuaraRemot);

        window.addEventListener('DOMContentLoaded', () => {
            videoElement.play().catch(err => {
                console.log("Autoplay dicegah browser.");
            });
        });

        function panggilSuara(nomor, loket) {
            videoElement.volume = 0.1; 
            let nomorEjaan = nomor.replace('-', ' '); 
            let teks = "Nomor antrean, " + nomorEjaan.split('').join(' ') + ", silakan menuju, loket " + loket;
            let suara = new SpeechSynthesisUtterance(teks);
            suara.lang = 'id-ID'; suara.rate = 0.85;
            suara.onend = function() { videoElement.volume = 1.0; };
            window.speechSynthesis.speak(suara);
        }

        socket.on('update_queue_' + branch, data => {
            document.getElementById('q').innerText = data.current.number;
            document.getElementById('c').innerText = "Loket " + data.current.counter;
            document.getElementById('info').innerText = "Nasabah: " + data.current.nama + " | " + data.current.layanan;
            panggilSuara(data.current.number, data.current.counter);

            updateList(data.waiting);
        });

        socket.on('new_customer_registered_' + branch, data => {
            updateList(data.waiting);
        });

        function updateList(waitingData) {
            let listHtml = '';
            if (waitingData.length === 0) {
                listHtml = '<div style="color: #777; text-align: center; margin-top: 30px; font-size: 12px;">Belum ada antrean menunggu</div>';
            } else {
                waitingData.forEach(item => {
                    let badgeCall = item.call_count > 0 ? ` <span style="background:#ffc107; color:#000; padding:2px 5px; border-radius:3px; font-size:9px;">Dipanggil ke-${item.call_count}</span>` : '';
                    listHtml += `
                        <div class="queue-item">
                            <div>
                                <div class="queue-item-num">${item.number} ${badgeCall}</div>
                                <div class="queue-item-name">${item.nama}</div>
                            </div>
                            <div style="font-size: 10px; color: #aaa; text-align: right;">${item.layanan}</div>
                        </div>
                    `;
                });
            }
            document.getElementById('next-queue-list').innerHTML = listHtml;
        }
    </script>
    ''')

# 2. Halaman HP Nasabah per Cabang
@app.route('/cabang/<branch>')
def customer_form(branch):
    branch_title = branch.replace('-', ' ').title()
    logo_url = url_for('static', filename='logo.png')
    return render_template_string('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        body { font-family: 'Poppins', sans-serif; background-color: #f4f4f9; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .container { background: white; padding: 35px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; width: 90%; max-width: 420px; border-top: 6px solid #d4af37; margin: 20px 0; }
        .logo img { height: 100px; margin-bottom: 10px; }
        .welcome-text { color: #d4af37; font-size: 15px; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 1px; }
        .branch-badge { background: #fff9db; color: #b8860b; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; display: inline-block; margin-bottom: 15px; border: 1px solid #ffe066; }
        p { color: #666; margin-bottom: 20px; font-size: 13px; }
        .form-group { text-align: left; margin-bottom: 15px; }
        label { font-size: 13px; font-weight: bold; color: #444; display: block; margin-bottom: 5px; }
        input, select { width: 100%; padding: 12px; border: 2px solid #eee; border-radius: 10px; font-size: 15px; box-sizing: border-box; font-family: inherit; background: #fff; }
        input:focus, select:focus { outline: none; border-color: #d4af37; }
        button { background: #d4af37; color: white; border: none; padding: 15px; font-size: 16px; border-radius: 10px; cursor: pointer; font-weight: bold; width: 100%; transition: 0.3s; box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3); margin-top: 10px; }
        button:hover { background: #b8962c; }
    </style>
    <div class="container">
        <div class="logo"><img src="''' + logo_url + '''" alt="Logo"></div>
        <div class="welcome-text">Tuku Emas Indonesia</div>
        <div class="branch-badge">Outlet: ''' + branch_title + '''</div>
        <p>Silakan isi data diri & pilih jenis transaksi Anda.</p>
        <form action="/cabang/''' + branch + '''/ambil" method="POST">
            <div class="form-group">
                <label>Nama Lengkap</label>
                <input type="text" name="nama" placeholder="Contoh: Budi Santoso" required>
            </div>
            <div class="form-group">
                <label>Nomor WhatsApp</label>
                <input type="tel" name="hp" placeholder="Contoh: 081234567890" required>
            </div>
            <div class="form-group">
                <label>Aktivitas / Jenis Transaksi</label>
                <select name="layanan" required>
                    <option value="" disabled selected>-- Pilih Jenis Transaksi --</option>
                    <option value="Jual Perhiasan / Logam Mulia">Jual Perhiasan / Logam Mulia</option>
                    <option value="Beli Logam Mulia">Beli Logam Mulia</option>
                    <option value="Trade-In (Tukar Tambah)">Trade-In (Tukar Tambah)</option>
                </select>
            </div>
            <button type="submit">Ambil Nomor Antrean</button>
        </form>
    </div>
    ''')

@app.route('/cabang/<branch>/ambil', methods=['POST'])
def ambil_antrean(branch):
    nama = request.form.get('nama')
    hp = request.form.get('hp')
    layanan = request.form.get('layanan')
    nomor_baru = get_next_queue_number(branch)
    tanggal_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db_path = get_db_path(branch)
    init_db(branch)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO visitors (number, nama, hp, layanan, tanggal, status, call_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (nomor_baru, nama, hp, layanan, tanggal_sekarang, 'waiting', 0))
    conn.commit()

    cursor.execute("SELECT number, nama, hp, layanan, call_count FROM visitors WHERE status='waiting'")
    waiting_list = [{"number": r[0], "nama": r[1], "hp": r[2], "layanan": r[3], "call_count": r[4]} for r in cursor.fetchall()]
    conn.close()

    socketio.emit('new_customer_registered_' + branch, {
        "waiting": waiting_list
    })
    
    logo_url = url_for('static', filename='logo.png')
    return '''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
        body { font-family: 'Poppins', sans-serif; background-color: #f4f4f9; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; border-top: 6px solid #d4af37; max-width: 400px; width: 90%; }
        .logo img { height: 90px; margin-bottom: 10px; }
        h2 { color: #666; font-size: 16px; font-weight: 400; margin: 0; }
        h1 { color: #d4af37; font-size: 56px; margin: 10px 0; }
        .badge { background: #fff9db; color: #b8860b; padding: 8px 15px; border-radius: 8px; font-size: 14px; font-weight: bold; display: inline-block; margin: 10px 0; border: 1px solid #ffe066; }
        p { color: #888; font-size: 14px; }
        .btn-back { display: inline-block; margin-top: 20px; padding: 10px 20px; text-decoration: none; color: #d4af37; border: 2px solid #d4af37; border-radius: 8px; font-weight: bold; }
    </style>
    <div class="container">
        <div class="logo"><img src="''' + logo_url + '''" alt="Logo"></div>
        <h2>Nomor Antrean Anda:</h2>
        <h1>''' + nomor_baru + '''</h1>
        <div class="badge">''' + layanan + '''</div>
        <p>Halo <b>''' + nama + '''</b>, silakan duduk dan tunggu panggilan di layar TV.</p>
        <a href="/cabang/''' + branch + '''" class="btn-back">Ambil Antrean Lagi</a>
    </div>
    '''

# 3. Halaman Panel Admin / CS per Cabang
@app.route('/cabang/<branch>/cs')
def cs_dashboard(branch):
    branch_title = branch.replace('-', ' ').title()
    db_path = get_db_path(branch)
    init_db(branch)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, number, nama, hp, layanan, call_count FROM visitors WHERE status='waiting'")
    waiting_data = cursor.fetchall()
    conn.close()

    waiting_rows = ""
    if not waiting_data:
        waiting_rows = "<tr><td colspan='5' style='padding:20px; text-align:center; color:#888;'>Tidak ada antrean yang menunggu.</td></tr>"
    else:
        for q in waiting_data:
            call_badge = f" <span style='background:#ffc107; color:#000; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:normal;'>Dipanggil ke-{q[5]}</span>" if q[5] > 0 else ""
            waiting_rows += f"""
            <tr>
                <td style="padding:12px; border-bottom:1px solid #eee; font-weight:bold; color:#d4af37; text-align:center;">{q[1]}{call_badge}</td>
                <td style="padding:12px; border-bottom:1px solid #eee;">{q[2]}</td>
                <td style="padding:12px; border-bottom:1px solid #eee;"><a href="https://wa.me/{q[3]}" target="_blank" style="color:#25d366; text-decoration:none; font-weight:bold;">💬 {q[3]}</a></td>
                <td style="padding:12px; border-bottom:1px solid #eee;">{q[4]}</td>
                <td style="padding:12px; border-bottom:1px solid #eee; text-align:center;">
                    <button onclick="panggilID({q[0]})" style="background:#28a745; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold;">Panggil (Panggilan ke-{q[5]+1})</button>
                </td>
            </tr>
            """

    return render_template_string('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        body { font-family: 'Poppins', sans-serif; background-color: #f4f4f9; margin: 0; padding: 30px; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border-top: 6px solid #d4af37; }
        .header-flex { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px; }
        h2 { color: #333; margin: 0; }
        .loket-box { background: #fff9db; padding: 12px 20px; border-radius: 10px; border: 1px solid #ffe066; display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
        .loket-box label { font-weight: bold; color: #b8860b; font-size: 14px; }
        .loket-box select { padding: 8px 12px; border-radius: 6px; border: 1px solid #d4af37; font-family: inherit; font-weight: bold; font-size: 14px; background: white; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { background: #121212; color: #d4af37; padding: 12px; text-align: left; font-size: 13px; }
        .link-rekap { display: inline-block; margin-top: 20px; color: #d4af37; text-decoration: none; font-weight: bold; font-size: 14px; }
        .link-rekap:hover { text-decoration: underline; }
    </style>
    <div class="container">
        <div class="header-flex">
            <div>
                <h2>Panel Admin - Outlet ''' + branch_title + '''</h2>
                <p style="color:#666; margin:5px 0 0 0; font-size:13px;">Nasabah dapat dipanggil maksimal 3 kali sebelum otomatis selesai.</p>
            </div>
        </div>

        <div class="loket-box">
            <label for="pilih-loket">Pilih Loket Anda Saat Ini:</label>
            <select id="pilih-loket">
                <option value="1">Loket 1</option>
                <option value="2">Loket 2</option>
                <option value="3">Loket 3</option>
                <option value="4">Loket 4</option>
                <option value="5">Loket 5</option>
                <option value="6">Loket 6</option>
            </select>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="text-align:center;">No. Antrean</th>
                    <th>Nama Nasabah</th>
                    <th>No. WhatsApp</th>
                    <th>Jenis Layanan</th>
                    <th style="text-align:center;">Aksi Panggil</th>
                </tr>
            </thead>
            <tbody>
                ''' + waiting_rows + '''
            </tbody>
        </table>

        <br>
        <a href="/cabang/''' + branch + '''/rekap" target="_blank" class="link-rekap">📊 Lihat Riwayat & Export Excel Cabang Ini</a>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io();
        const branch = "''' + branch + '''";

        function panggilID(id) {
            let selectedLoket = document.getElementById('pilih-loket').value;
            socket.emit('call_by_id', { id: id, counter: selectedLoket, branch: branch });
        }

        socket.on('update_queue_' + branch, () => {
            location.reload();
        });
    </script>
    ''')

# 4. Halaman Riwayat & Download Excel per Cabang
@app.route('/cabang/<branch>/rekap')
def rekap_visitor(branch):
    branch_title = branch.replace('-', ' ').title()
    db_path = get_db_path(branch)
    init_db(branch)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, number, nama, hp, layanan, tanggal, status FROM visitors ORDER BY id DESC")
    history_data = cursor.fetchall()
    conn.close()

    action_buttons = ""
    if history_data:
        action_buttons = '''
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <a href="/cabang/''' + branch + '''/export_excel" style="background:#28a745; color:white; padding:10px 18px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:13px; box-shadow: 0 4px 10px rgba(40,167,69,0.3);">📥 Download Laporan Excel (''' + branch_title + ''')</a>
            <a href="/cabang/''' + branch + '''/hapus_semua" onclick="return confirm('PERINGATAN! Hapus seluruh riwayat cabang ini?');" style="background:#dc3545; color:white; padding:10px 15px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:13px;">🗑️ Reset Antrean Cabang Ini</a>
        </div>
        '''

    rows = ""
    for v in history_data:
        status_badge = "<span style='color:green; font-weight:bold;'>Selesai</span>" if v[6] == 'done' else "<span style='color:orange; font-weight:bold;'>Menunggu</span>"
        rows += f"""
        <tr>
            <td style="padding:12px; border-bottom:1px solid #ddd; text-align:center; font-weight:bold; color:#d4af37;">{v[1]}</td>
            <td style="padding:12px; border-bottom:1px solid #ddd;">{v[2]}</td>
            <td style="padding:12px; border-bottom:1px solid #ddd;"><a href="https://wa.me/{v[3]}" target="_blank" style="color: #25d366; text-decoration: none; font-weight: bold;">💬 {v[3]}</a></td>
            <td style="padding:12px; border-bottom:1px solid #ddd;">{v[4]}</td>
            <td style="padding:12px; border-bottom:1px solid #ddd; font-size:13px; color:#555;">{v[5]}</td>
            <td style="padding:12px; border-bottom:1px solid #ddd; text-align:center;">{status_badge}</td>
            <td style="padding:12px; border-bottom:1px solid #ddd; text-align:center;">
                <a href="/cabang/''' + branch + f'''/hapus/{v[0]}" onclick="return confirm('Hapus data ini?');" style="background:#dc3545; color:white; padding:6px 12px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:bold;">Hapus</a>
            </td>
        </tr>
        """
    if not rows:
        rows = "<tr><td colspan='7' style='padding:20px; text-align:center; color:#888;'>Belum ada riwayat pengunjung di cabang ini.</td></tr>"

    return render_template_string('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        body { font-family: 'Poppins', sans-serif; background-color: #f4f4f9; margin: 0; padding: 40px; }
        .container { max-width: 1100px; margin: auto; background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border-top: 6px solid #d4af37; }
        h2 { color: #333; margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 5px; }
        th { background: #121212; color: #d4af37; padding: 12px; text-align: left; font-size: 13px; }
        .btn-back { display: inline-block; margin-bottom: 20px; padding: 8px 15px; background: #eee; color: #333; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; }
        .btn-back:hover { background: #ddd; }
    </style>
    <div class="container">
        <a href="/cabang/''' + branch + '''/cs" class="btn-back">← Kembali ke Panel Admin</a>
        <h2>Laporan Cabang: ''' + branch_title + '''</h2>
        <p style="color: #666; font-size: 13px; margin-bottom: 20px;">Data riwayat dan laporan Excel khusus untuk outlet ''' + branch_title + '''.</p>
        
        ''' + action_buttons + '''
        
        <table>
            <thead>
                <tr>
                    <th style="text-align:center;">No. Antrean</th>
                    <th>Nama Nasabah</th>
                    <th>No. WhatsApp</th>
                    <th>Jenis Layanan</th>
                    <th>Tanggal & Waktu</th>
                    <th style="text-align:center;">Status</th>
                    <th style="text-align:center;">Aksi</th>
                </tr>
            </thead>
            <tbody>''' + rows + '''</tbody>
        </table>
    </div>
    ''')

@app.route('/cabang/<branch>/export_excel')
def export_excel(branch):
    db_path = get_db_path(branch)
    conn = sqlite3.connect(db_path)
    query = "SELECT number AS 'Nomor Antrean', nama AS 'Nama Nasabah', hp AS 'No. WhatsApp', layanan AS 'Jenis Layanan', tanggal AS 'Tanggal & Waktu', status AS 'Status' FROM visitors ORDER BY id DESC"
    df = pd.read_sql(query, conn)
    conn.close()

    df['Status'] = df['Status'].replace({'waiting': 'Menunggu', 'done': 'Selesai'})

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Laporan Cabang')
    output.seek(0)

    filename = f"Laporan_TukuEmas_{branch}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=filename)

@app.route('/cabang/<branch>/hapus/<int:id>')
def hapus_data(branch, id):
    db_path = get_db_path(branch)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM visitors WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('rekap_visitor', branch=branch))

@app.route('/cabang/<branch>/hapus_semua')
def hapus_semua(branch):
    db_path = get_db_path(branch)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM visitors")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='visitors'")
    conn.commit()
    conn.close()
    return redirect(url_for('rekap_visitor', branch=branch))

@socketio.on('join_branch')
def handle_join_branch_socket(data):
    pass

@socketio.on('call_by_id')
def handle_call_by_id_socket(data):
    visitor_id = data['id']
    counter = data['counter']
    branch = data['branch']

    db_path = get_db_path(branch)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT number, nama, hp, layanan, call_count FROM visitors WHERE id=?", (visitor_id,))
    visitor = cursor.fetchone()

    if visitor:
        new_call_count = visitor[4] + 1
        
        if new_call_count >= 3:
            cursor.execute("UPDATE visitors SET status='done', call_count=? WHERE id=?", (new_call_count, visitor_id))
        else:
            cursor.execute("UPDATE visitors SET call_count=? WHERE id=?", (new_call_count, visitor_id))
        
        conn.commit()

        current_queue = {
            "number": visitor[0],
            "counter": counter,
            "nama": visitor[1],
            "hp": visitor[2],
            "layanan": visitor[3]
        }
    else:
        current_queue = {"number": "A-000", "counter": "-", "nama": "-", "hp": "-", "layanan": "-"}

    cursor.execute("SELECT number, nama, hp, layanan, call_count FROM visitors WHERE status='waiting'")
    waiting_list = [{"number": r[0], "nama": r[1], "hp": r[2], "layanan": r[3], "call_count": r[4]} for r in cursor.fetchall()]
    conn.close()

    socketio.emit('update_queue_' + branch, {"current": current_queue, "waiting": waiting_list})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)