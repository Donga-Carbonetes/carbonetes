from flask import Flask, request, jsonify
from queue import Queue
from threading import Thread
import time

app = Flask(__name__)
data_queue = Queue()

# 사용자 정의 처리 함수 (로직 구현 예정)
def process_task(task_name, estimated_time):
    print(f"[처리 시작] 작업 이름: {task_name}, 예상 시간: {estimated_time}초")
    

    time.sleep(estimated_time)
    print(f"[처리 완료] 작업 이름: {task_name}")

# 큐에서 뽑아 데이터 처리
def process_queue():
    while True:
        if not data_queue.empty():
            task = data_queue.get()
            task_name = task['task_name']
            estimated_time = task['estimated_time']
            process_task(task_name, estimated_time)
            data_queue.task_done()
        else:
            time.sleep(0.5)  # 큐가 비었을 때 과도한 루프 방지용

# 작업 처리 스레드 시작
worker = Thread(target=process_queue, daemon=True)
worker.start()

# Enqueue End Point
@app.route('/enqueue', methods=['POST'])
def enqueue():
    if not request.is_json:
        return jsonify({"error": "JSON 형식이어야 합니다."}), 400

    data = request.get_json()

    if 'task_name' not in data or 'estimated_time' not in data:
        return jsonify({"error": "task_name과 estimated_time이 필요합니다."}), 400

    task = {
        "task_name": data['task_name'],
        "estimated_time": data['estimated_time']
    }

    data_queue.put(task)
    return jsonify({"status": "작업이 큐에 등록되었습니다.", "task": task}), 200

# Queue 확인용 제거예정
@app.route('/queue_size', methods=['GET'])
def queue_size():
    return jsonify({"queue_size": data_queue.qsize()}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=18080)