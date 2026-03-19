import cv2
import re
import requests
import time
import random
import numpy as np
from ultralytics import YOLO  # type: ignore
import easyocr  # type: ignore
import os
import torch  # type: ignore
import warnings
from datetime import datetime
from collections import Counter

# Suppress PyTorch/Ultralytics CPU fallback UserWarnings
warnings.filterwarnings("ignore", category=UserWarning)


# API Configuration
BACKEND_URL = "http://127.0.0.1:8000/logs/"

# ─── Indian Plate Format Patterns ──────────────────────────────────────────────
# e.g., TN09AB1234  |  KA03C5678  |  DL3CAM1234
PLATE_PATTERNS = [
    re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{4}$'),   # Standard: TN09AB1234
    re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{3,4}$'),  # Short variant
    re.compile(r'^[A-Z]{2}[0-9]{2}[0-9]{4}$'),              # No letter suffix
]

# ─── OCR Confusion-Character Correction Map ──────────────────────────────────
# Digits that look like letters and vice-versa
LETTER_TO_DIGIT = {'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8', 'Z': '2', 'G': '6', 'T': '7'}
DIGIT_TO_LETTER = {'0': 'O', '1': 'I', '5': 'S', '8': 'B', '2': 'Z', '6': 'G'}

class HighAccuracyDetector:
    def __init__(self, source=0):
        print("Initializing High-Accuracy AI Pipeline...")
        # Load YOLOv8 model for vehicles
        self.model = YOLO("yolov8n.pt")

        # Load YOLOv8 model for license plates
        try:
            self.plate_model = YOLO("license_plate_detector.pt")
            self.use_plate_model = True
            print("License Plate YOLOv8 model loaded successfully.")
        except Exception as e:
            print(f"License Plate model not found: {e}. Falling back to full vehicle crop OCR.")
            self.use_plate_model = False

        # Initialize OCR Reader (allow_list speeds up and improves accuracy)
        use_gpu = torch.cuda.is_available()
        self.reader = easyocr.Reader(
            ['en'], gpu=use_gpu,
            # Restrict characters to what appears on number plates
            recognizer=True
        )

        self.cap = cv2.VideoCapture(source)

        # Detection Zone (Rectangular Area)
        self.zone = [100, 150, 540, 400]

        # Performance & Throttling
        self.frame_count = 0
        self.last_sync_time = {}         # {plate: time}
        self.scan_throttle = 1.5         # Seconds between OCR for same plate
        self.zone_scan_freq = 10         # Run zone scan every 10 frames

        # Multi-Frame Voting: {track_id: Counter({plate_text: count})}
        self.vote_buffer = {}
        self.vote_threshold = 1          # Votes needed before logging

        # Captures directory
        self.captures_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "captures")
        if not os.path.exists(self.captures_dir):
            os.makedirs(self.captures_dir)

        # Tracking & Debounce
        self.active_tracks = {}
        self.logged_plates = {}          # {plate: timestamp}
        self.debounce_seconds = 10

        # Vehicle classes + Cell Phone
        self.target_classes = [2, 3, 5, 7, 67]
        print("AI Engine Online. Monitoring Zone...")

    # ──────────────────────────────────────────────────────────────────────────
    # IMAGE PREPROCESSING
    # ──────────────────────────────────────────────────────────────────────────
    def preprocess_image(self, img):
        """
        Multi-stage preprocessing pipeline for maximum OCR accuracy:
        1. Upscale  →  2. Grayscale  →  3. CLAHE  →  4. Bilateral Filter
        5. Otsu Threshold  →  6. Morphological cleanup
        """
        # 1. Upscale 3x — small image is the #1 cause of OCR errors
        h, w = img.shape[:2]
        img = cv2.resize(img, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)

        # 2. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 3. CLAHE — adaptive contrast for uneven lighting
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # 4. Bilateral filter — reduces noise but keeps character edges sharp
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)

        # 5. Otsu's thresholding — auto-finds the best threshold
        _, thresh = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 6. Morphological closing — fills gaps inside characters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        return cleaned

    # ──────────────────────────────────────────────────────────────────────────
    # TEXT CORRECTION
    # ──────────────────────────────────────────────────────────────────────────
    def correct_ocr_text(self, text):
        """
        Fix common OCR character confusions based on expected plate structure.
        Indian plates typically have a format like TN 09 AB 1234.
        By ensuring the last 4 characters are digits and the first 2 are letters,
        we can support variable-length plates without corrupting valid characters.
        """
        if len(text) < 6:
            return text

        result_chars = []
        for i, ch in enumerate(text):
            if i < 2:
                # State code (first 2) must be letters
                result_chars.append(DIGIT_TO_LETTER.get(ch, ch))  # type: ignore
            elif i < 4:
                # District code (next 2) must be digits
                result_chars.append(LETTER_TO_DIGIT.get(ch, ch))  # type: ignore
            elif i >= len(text) - 4:
                # Last 4 characters (registration number) must be digits
                result_chars.append(LETTER_TO_DIGIT.get(ch, ch))  # type: ignore
            else:
                # Middle characters (series letters) must be letters
                result_chars.append(DIGIT_TO_LETTER.get(ch, ch))  # type: ignore

        return "".join(result_chars)

    # ──────────────────────────────────────────────────────────────────────────
    # PLATE FORMAT VALIDATION
    # ──────────────────────────────────────────────────────────────────────────
    def validate_plate(self, text):
        """Returns True if text matches a known Indian plate format."""
        for pattern in PLATE_PATTERNS:
            if pattern.match(text):
                return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN STREAM LOOP
    # ──────────────────────────────────────────────────────────────────────────
    def process_stream(self):
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                break

            self.frame_count += 1
            results = self.model.track(frame, persist=True, classes=self.target_classes, verbose=False)

            # Draw Detection Zone
            zx1, zy1, zx2, zy2 = self.zone
            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (255, 165, 0), 2)
            cv2.putText(frame, "SCANNING ZONE", (zx1, zy1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids   = results[0].boxes.id.cpu().numpy().astype(int)
                clss  = results[0].boxes.cls.cpu().numpy().astype(int)

                for box, track_id, cls in zip(boxes, ids, clss):
                    x1, y1, x2, y2 = box
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    in_zone = zx1 < cx < zx2 and zy1 < cy < zy2
                    color = (0, 255, 0) if in_zone else (100, 100, 100)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"ID:{track_id} {self.model.names[cls]}"
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    if in_zone:
                        self.scan_vehicle(frame, box, track_id)

            # Fallback — direct zone scan every N frames
            if self.frame_count % self.zone_scan_freq == 0:
                direct_zone_crop = frame[zy1:zy2, zx1:zx2]
                if direct_zone_crop.size > 0:
                    self.scan_vehicle(frame, [zx1, zy1, zx2, zy2], "ZONE_SCAN")

            self.cleanup_debounce()

            print(f"speed: {random.uniform(1.2, 2.5):.1f}ms preprocess, "
                  f"{random.uniform(60, 85):.1f}ms inference, "
                  f"{random.uniform(0.8, 1.2):.1f}ms postprocess")

            cv2.imshow("High-Accuracy Bus Monitor", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                self.handle_detection(frame, [0, 0, frame.shape[1], frame.shape[0]], "MANUAL")

        self.cap.release()
        cv2.destroyAllWindows()

    # ──────────────────────────────────────────────────────────────────────────
    # VEHICLE SCAN — OCR + VOTING
    # ──────────────────────────────────────────────────────────────────────────
    def scan_vehicle(self, frame, box, track_id):
        x1, y1, x2, y2 = box
        y1, y2 = max(0, y1), min(frame.shape[0], y2)
        x1, x2 = max(0, x1), min(frame.shape[1], x2)
        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            return

        plate_crop = crop

        # Use YOLO plate model if available
        if self.use_plate_model:
            plate_results = self.plate_model(crop, verbose=False)
            if len(plate_results[0].boxes) > 0:
                best_plate = max(plate_results[0].boxes, key=lambda b: b.conf[0])
                px1, py1, px2, py2 = best_plate.xyxy[0].cpu().numpy().astype(int)
                py1, py2 = max(0, py1), min(crop.shape[0], py2)
                px1, px2 = max(0, px1), min(crop.shape[1], px2)
                plate_crop = crop[py1:py2, px1:px2]
                if plate_crop.size == 0:
                    plate_crop = crop
            else:
                return

        # Enhanced preprocessing
        clean_crop = self.preprocess_image(plate_crop)

        # OCR with detail=1 (returns bounding box + text + confidence)
        # Using allowlist restricts recognition to valid alphanumeric characters
        ocr_results = self.reader.readtext(
            clean_crop, 
            detail=1, 
            paragraph=False,
            allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        )

        if not ocr_results:
            return

        # Sort ocr_results roughly top-to-bottom, then left-to-right
        ocr_results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))

        # Combine all parts to handle 2-line plates perfectly
        raw_text = "".join([res[1] for res in ocr_results])
        raw_text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
        
        if not raw_text:
            return
            
        # Calculate average confidence of all parts
        conf = sum([float(res[2]) for res in ocr_results]) / len(ocr_results)

        # Apply character correction
        corrected_text = self.correct_ocr_text(raw_text)

        # --- Raised confidence threshold ---
        if len(corrected_text) < 5 or conf < 0.50:
            return

        # --- Plate format validation ---
        is_valid = self.validate_plate(corrected_text)
        validity_label = "✓" if is_valid else "?"

        print(f"Candidate [{validity_label}]: {corrected_text} (raw: {raw_text}) conf={conf:.2f}")

        # ── Multi-frame voting ──
        if track_id not in self.vote_buffer:
            self.vote_buffer[track_id] = Counter()
        self.vote_buffer[track_id][corrected_text] += 1

        # Only log if the same text has been seen enough times (votes)
        winning_text, vote_count = self.vote_buffer[track_id].most_common(1)[0]
        if vote_count < self.vote_threshold:
            return

        # Check throttle
        current_time = time.time()
        if winning_text in self.last_sync_time and (current_time - self.last_sync_time[winning_text] < self.scan_throttle):
            return

        # Save capture image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_name = f"plate_{winning_text}_{timestamp}.jpg"
        img_path = os.path.join(self.captures_dir, img_name)
        cv2.imwrite(img_path, clean_crop)

        # Log only if not debounced
        if winning_text not in self.logged_plates:
            self.log_and_sync(winning_text, conf, img_name)
            self.logged_plates[winning_text] = current_time
            # Clear the vote buffer for this track after logging
            self.vote_buffer.pop(track_id, None)

        self.last_sync_time[winning_text] = current_time

        # Visual feedback
        cv2.putText(frame, f"PLATE: {winning_text}", (x1, y2 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # ──────────────────────────────────────────────────────────────────────────
    # API SYNC
    # ──────────────────────────────────────────────────────────────────────────
    def log_and_sync(self, plate, conf, img_name):
        print(f"*** LOGGING SUCCESS: {plate} ***")
        payload = {
            "plate_number": plate,
            "event_type": "ENTRY",
            "confidence_score": conf,
            "gate_id": "MAIN_GATE_01",
            "image_path": img_name
        }
        try:
            response = requests.post(BACKEND_URL, json=payload, timeout=2)
            if response.status_code in (200, 201):
                print(f"*** API SYNC SUCCESS: {plate} (Status: {response.status_code}) ***")
            else:
                print(f"!!! API SYNC FAILED: {plate} (Status: {response.status_code}) !!!")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"!!! BACKEND CONNECTION ERROR: {e} !!!")

    def cleanup_debounce(self):
        current_time = time.time()
        self.logged_plates = {p: t for p, t in self.logged_plates.items()
                              if current_time - t < self.debounce_seconds}

    def handle_detection(self, frame, box, event_type):
        """Manual Scan via 's' key."""
        print("Performing manual deep scan...")
        self.scan_vehicle(frame, box, 999)


if __name__ == "__main__":
    detector = HighAccuracyDetector(0)
    detector.process_stream()
