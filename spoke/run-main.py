import mysql.connector
import os
from minio import Minio
from minio.error import S3Error
import subprocess

db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE")
}

minio_host = os.getenv("MINIO_HOST")
minio_port = os.getenv("MINIO_PORT")

client = Minio(
    f"{minio_host}:{minio_port}",
    access_key="rootuser",
    secret_key="rootpass123",
    secure=False
)

task_name = os.getenv("TASK_NAME")
bucket_name = "mybucket"
object_name = f"{task_name}.py"
download_dir = "./tmp/myapp"
os.makedirs(download_dir, exist_ok=True)

def update_task_status_and_completed_at(task_name, status):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    query = """
        UPDATE task_info SET status = %s, completed_at = NOW() WHERE task_name = %s
    """ 

    cursor.execute(query, (status, task_name))
    conn.commit()

    cursor.close()
    conn.close()

def download_task():
    download_path = os.path.abspath(os.path.join(download_dir, object_name))

    try:
        client.fget_object(bucket_name, object_name, download_path)
        print(f"Task downloaded to {download_path}")
        print(f"{object_name} downloaded")
        return download_path
    except S3Error as e:
        print(e)
        exit(1)
    
def run_task(download_path):
    try:
        process = subprocess.Popen(
            ["python", download_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # 줄 단위로 버퍼링
        )

        print(f"Task {task_name} executed")
        for line in process.stdout:
            print(line,end="")

        process.wait()
        print(f"\n✅ 실행 종료 (종료 코드: {process.returncode})")

        if process.returncode != 0:
            print("⚠️ 오류가 발생했습니다.")
            
        
        return process.returncode
            
    except Exception as e:
        print(f"❌ 실행 중 예외 발생: {e}")
        


if __name__ == "__main__":
    download_path = download_task()
    return_code = run_task(download_path)
    if return_code == 0:
        update_task_status_and_completed_at(task_name, "terminated")
        print(f"✅ 모든 프로그램이 정상적으로 종료되었습니다 (종료 코드: {return_code})")




