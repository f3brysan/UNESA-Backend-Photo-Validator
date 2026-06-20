import os
import base64
import cv2
import numpy as np
import torch
from flask import Flask, request, jsonify
from ultralytics import YOLO

# Perbaikan untuk PyTorch 2.6+ yang mengubah default weights_only=True
_original_torch_load = torch.load
def _custom_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _custom_torch_load

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

_model = None

def get_model():
    global _model
    if _model is None:
        try:
            # Pastikan model di-load hanya saat benar-benar dibutuhkan
            model_path = os.path.join(os.getcwd(), 'model', 'best.pt')
            if not os.path.exists(model_path):
                model_path = '/app/model/best.pt'
            _model = YOLO(model_path)
            print("Model YOLO berhasil dimuat secara lazy.")
        except Exception as e:
            print(f"Warning: model gagal diload. Error: {e}")
            _model = None
    return _model

def check_background_blue(img_bgr):
    # Konversi gambar ke ruang warna HSV
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # Rentang warna yang dianggap biru (H: 90 - 130)
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    
    # Ambil bagian atas gambar sebagai representasi background (misal top 20%)
    h, w = img_bgr.shape[:2]
    top_bg = hsv[0:int(h*0.2), :]
    
    # Buat mask di mana bernilai > 0 jika pixel berada pada rentang warna biru
    mask = cv2.inRange(top_bg, lower_blue, upper_blue)
    blue_ratio = np.sum(mask > 0) / mask.size
    
    return blue_ratio > 0.3

@app.route('/api/v1/validasi_foto', methods=['POST'])
def validasi_foto():
    req_data = request.get_json(silent=True) or request.form
    
    foto_b64 = req_data.get('foto')
    gender = req_data.get('gender')
    
    if not foto_b64:
        return jsonify({"status": "error", "message": "Field 'foto' (base64) tidak ditemukan"}), 400
        
    if not gender or gender.upper() not in ['L', 'P']:
        return jsonify({"status": "error", "message": "Field 'gender' (L/P) tidak valid"}), 400
        
    try:
        if ',' in foto_b64:
            foto_b64 = foto_b64.split(',')[1]
            
        img_bytes = base64.b64decode(foto_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Gambar tidak valid")
    except Exception as e:
        return jsonify({"status": "error", "message": "Gagal membaca foto format base64"}), 400

    # Tahap 1: Pengecekan background
    if not check_background_blue(img):
        return jsonify({"status": "error", "message": "Background tidak sesuai"}), 400
        
    # Pemuatan model (lazy)
    model_instance = get_model()
    if model_instance is None:
        return jsonify({"status": "error", "message": "Server error: Model YOLO belum tersedia"}), 500

    # Tahap Inferensi
    results = model_instance(img)
    boxes = results[0].boxes
    class_names = results[0].names
    
    CONFIDENCE_THRESHOLD = 0.7

    da_si_found = False
    logo_found = False
    tie_meragukan = False
    logo_meragukan = False
    tie_score = None
    logo_score = None
    logo_x_center = -1
    
    detected_objects = []
    
    for box in boxes:
        cls_id = int(box.cls[0])
        name = class_names[cls_id].lower()
        confidence = float(box.conf[0])
        detected_objects.append(name)
        
        if 'tie' in name:
            if tie_score is None or confidence > tie_score:
                tie_score = round(confidence, 4)
            da_si_found = True
        if 'logo' in name:
            if logo_score is None or confidence > logo_score:
                logo_score = round(confidence, 4)
                x1, _, x2, _ = box.xyxy[0].tolist()
                logo_x_center = (x1 + x2) / 2
            logo_found = True

    if da_si_found and tie_score is not None and tie_score < CONFIDENCE_THRESHOLD:
        tie_meragukan = True
    if logo_found and logo_score is not None and logo_score < CONFIDENCE_THRESHOLD:
        logo_meragukan = True
            
    total_objects = len(detected_objects)
    response_data = {
        "status": "success",
        "message": "Foto sesuai ketentuan",
        "data": {
            "total_objects": total_objects,
            "detected_objects": detected_objects,
            "tie_score": tie_score,
            "logo_score": logo_score,           
        }
    }
            
    if gender.upper() == 'L' and not da_si_found:
        response_data["status"] = "error"
        response_data["message"] = "Harap, mengenakan dasi yang sesuai."
        return jsonify(response_data), 400

    if gender.upper() == 'L' and tie_meragukan:
        response_data["status"] = "error"
        response_data["message"] = f"Dasi Anda tampak meragukan. Bisa dicoba dengan mengunggah foto yang lebih jelas."
        return jsonify(response_data), 400

    if gender.upper() == 'P' and da_si_found:
        response_data["status"] = "error"
        response_data["message"] = "Wanita tidak mengenakan dasi."
        return jsonify(response_data), 400
        
    if not logo_found:
        response_data["status"] = "error"
        response_data["message"] = "Tidak mengenakan almamater yang sesuai."
        return jsonify(response_data), 400

    if logo_meragukan:
        response_data["status"] = "error"
        response_data["message"] = f"Logo Anda tampak meragukan. Bisa dicoba dengan mengunggah foto yang lebih jelas."
        return jsonify(response_data), 400
        
    img_h, img_w = img.shape[:2]
    if logo_x_center < img_w / 2:
        response_data["status"] = "error"
        response_data["message"] = "Foto anda mirror."
        return jsonify(response_data), 400

    return jsonify(response_data), 200

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"status": "error", "message": "Payload terlalu besar (Max 10MB)"}), 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
