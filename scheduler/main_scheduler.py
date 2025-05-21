from flask import Flask, request, jsonify
from queue import Queue
from threading import Thread
import time
import logging
import sys
import requests

from task_processor import process_task

app = Flask(__name__)
data_queue = Queue()

# -----------------------
# 🔧 Logging 설정
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 콘솔/로그 수집 시스템으로 출력
    ]
)

# 큐에서 뽑아 데이터 처리
def process_queue():
    while True:
        try:
            task = data_queue.get()
            task_name = task.get('task_name')
            estimated_time = task.get('estimated_time', 0)
            process_task(task_name, estimated_time)
            url = 'http://localhost:5000/users'  # Flask 서버 주소 및 라우트
            data = {
                'cluster': 'k3s-2',
                'task': 'mltask-dd390921e2eb47e28ceeeae405e6bae5'
            }

            try:
                response = requests.post(url, json=data)
                print('Status Code:', response.status_code)
                print('Response:', response.json())
            except requests.exceptions.RequestException as e:
                print('Request failed:', e)
            # Dispatcher 에 값 전달


            data_queue.task_done()
        except Exception as e:
            logging.error(f"[Thread Error] 큐 처리 중 오류 발생: {e}")

# 작업 처리 스레드 시작
worker = Thread(target=process_queue, daemon=True)
worker.start()

# Enqueue End Point
@app.route('/schedule/enqueue', methods=['POST'])
def enqueue():
    if not request.is_json:
        logging.warning("enqueue 요청이 JSON이 아님")
        return jsonify({"error": "JSON 형식이어야 합니다."}), 400

    data = request.get_json()

    if 'task_name' not in data or 'estimated_time' not in data:
        logging.warning("enqueue 요청에 필요한 키가 없음")
        return jsonify({"error": "task_name과 estimated_time이 필요합니다."}), 400

    try:
        task = {
            "task_name": data['task_name'],
            "estimated_time": int(data['estimated_time']) # 초 단위 정수값 사용 
        }
        data_queue.put(task)
        logging.info(f"작업 등록됨: {task}")
        return jsonify({"status": "작업이 큐에 등록되었습니다.", "task": task}), 200
    except Exception as e:
        logging.error(f"enqueue 처리 중 오류: {e}")
        return jsonify({"error": "요청 처리 중 오류 발생"}), 500

# Queue 크기 확인
@app.route('/queue_size', methods=['GET'])
def queue_size():
    size = data_queue.qsize()
    logging.info(f"큐 크기 확인 요청 - 현재 큐 크기: {size}")
    return jsonify({"queue_size": size}), 200

if __name__ == '__main__':
    logging.info("Flask 앱 시작됨 (0.0.0.0:28000)")
    app.run(debug=False, host='0.0.0.0', port=28000)