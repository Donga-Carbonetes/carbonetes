import mysql.connector
from mysql.connector import Error

# 키(Key) 변환을 위한 매핑 규칙 정의
_KEY_MAPPING = {
    'id': 'task_id',
    'task_name': 'task_name',
    'dispatched_at': 'dispatched_at',
    'estimated_time': 'estimated_runtime',
    'actual_runtime': 'actual_runtime',
    'cpu_m': 'avg_cpu_usage',
    'memory': 'avg_mem_usage',
    'cluster_name': 'cluster_name',
    'caborn_intensity': 'carbon_intensity',
    'completed_at': 'completion_at',
    'queue_delay': 'queue_delay'
}

def get_processed_tasks(db_config: dict) -> list:
    """
    데이터베이스에서 최신 태스크 10개를 가져와 계산 및 키 변환 후 리스트로 반환합니다.

    Args:
        db_config (dict): 데이터베이스 연결 설정 딕셔너리

    Returns:
        list: 최종 처리된 태스크 데이터 (딕셔너리 리스트).
              오류 발생 시 빈 리스트를 반환합니다.
    """
    original_data = []
    connection = None
    cursor = None
    
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT
            id, task_name, dispatched_at, estimated_time, completed_at,
            cpu_m, memory, cluster_name, caborn_intensity,
            TIMESTAMPDIFF(SECOND, created_at, dispatched_at) AS queue_delay,
            TIMESTAMPDIFF(SECOND, dispatched_at, completed_at) AS actual_runtime
        FROM
            task_info
        ORDER BY
            created_at DESC
        LIMIT 10;
        """
        cursor.execute(query)
        original_data = cursor.fetchall()

    except Error as e:
        # 실제 운영 환경에서는 print 대신 로깅(logging) 라이브러리를 사용하는 것이 좋습니다.
        print(f"❌ 데이터베이스 처리 중 오류 발생: {e}")
        return [] # 오류가 발생하면 빈 리스트를 반환

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    # --- 키 변환 로직 ---
    transformed_data = []
    for row in original_data:
        new_row = {}
        for original_key, new_key in _KEY_MAPPING.items():
            if original_key in row:
                new_row[new_key] = row[original_key]
        transformed_data.append(new_row)
        
    return transformed_data