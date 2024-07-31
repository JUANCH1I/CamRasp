from flask import Flask, render_template, Response, jsonify
import RPi.GPIO as GPIO
import cv2
import threading
import time
from flask_socketio import SocketIO, emit
import pyaudio


app = Flask(__name__)
socketio = SocketIO(app)

# Configuracion de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pines GPIO
pins = {
    17: {'name': 'Puerta', 'state': GPIO.LOW},
    27: {'name': 'Bocina', 'state': GPIO.LOW},
    22: {'name': 'Luces', 'state': GPIO.LOW}
}

for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

class Camera:
    def __init__(self):
        self.camera = cv2.VideoCapture(0)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Reducir resolucion
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 24)  # Aumentar FPS si es posible
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update_frame, args=())
        self.thread.daemon = True
        self.thread.start()
        self.frame = None

    def update_frame(self):
        while True:
            with self.lock:
                success, frame = self.camera.read()
                if success:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    self.frame = buffer.tobytes()
            time.sleep(0.03)  # Reducir retraso para aumentar FPS

    def get_frame(self):
        with self.lock:
            return self.frame

    def release(self):
        with self.lock:
            if self.camera.isOpened():
                self.camera.release()

    def __del__(self):
        self.release()

class Audio:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024)
        self.thread = threading.Thread(target=self.update_audio, args=())
        self.thread.daemon = True
        self.thread.start()

    def update_audio(self):
        while True:
            data = self.stream.read(1024)
            socketio.emit('audio_frame', data)

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

camera = None
audio = None
camera_lock = threading.Lock()
audio_lock = threading.Lock()

def get_camera():
    global camera
    with camera_lock:
        if camera is None:
            camera = Camera()
        return camera
    

def get_audio():
    global audio
    with audio_lock:
        if audio is None:
            audio = Audio()
        return audio

@app.route('/')
def index():
    for pin in pins:
        pins[pin]['state'] = GPIO.input(pin)
    templateData = {'pins': pins}
    return render_template('client.html', **templateData)
    
@app.route('/client_video_feed')
def client_video_feed():
    return render_template('raspi.html')
    
@app.route('/control')
def control_page():
    for pin in pins:
        pins[pin]['state'] = GPIO.input(pin)
    templateData = {'pins': pins}
    return render_template('control.html', **templateData)

@app.route('/<changePin>/<action>', methods=['POST'])
def action(changePin, action):
    changePin = int(changePin)
    deviceName = pins[changePin]['name']
    if action == "on":
        GPIO.output(changePin, GPIO.LOW)
    if action == "off":
        GPIO.output(changePin, GPIO.HIGH)
    for pin in pins:
        pins[pin]['state'] = GPIO.input(pin)
    return jsonify({'status': 'success', 'pin': changePin, 'state': GPIO.input(changePin)})

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)  # Reducir retraso para el generador

@app.route('/video_feed')
def video_feed():
    return Response(gen(get_camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('offer')
def handle_offer(sdp):
    emit('offer', sdp, broadcast=True)

@socketio.on('answer')
def handle_answer(sdp):
    emit('answer', sdp, broadcast=True)

@socketio.on('candidate')
def handle_candidate(candidate):
    emit('candidate', candidate, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

