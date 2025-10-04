################################################
# Memetic Algorithm (메머틱 알고리즘) 프로젝트의 학습기(Learning Loop) 코드입니다.
################################################

import os
import logging




# DB Configuration
db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "carbonetes"
}

def learning_loop(task_name, estimated_time):
    logging.info('Nice~')
    
