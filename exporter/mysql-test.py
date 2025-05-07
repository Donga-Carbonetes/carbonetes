import os
from dotenv import load_dotenv
import mysql.connector

# .env 파일 불러오기
load_dotenv()

# 환경변수에서 정보 읽기
db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE")
}

# MySQL 연결
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# 간단한 쿼리 실행 예시
cursor.execute("SHOW TABLES")
for (table_name,) in cursor.fetchall():
    print("테이블:", table_name)

# 연결 종료
cursor.close()
conn.close()
