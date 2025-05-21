# task_processor.py
import logging
import time

kluster_nodes = 2 # Slave Node 수

def process_task(task_name, estimated_time):
    logging.info(f"처리 시작 - 작업 이름: {task_name}, 예상 시간: {estimated_time}초")
    try:
        

        time.sleep(estimated_time)
        logging.info(f"처리 완료 - 작업 이름: {task_name}")
        
    except Exception as e:
        logging.error(f"작업 처리 중 오류 발생 - 작업 이름: {task_name}, 에러: {e}")