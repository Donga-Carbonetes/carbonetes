import kopf
import os
from kubernetes import client, config
from datetime import datetime

config.load_incluster_config()

@kopf.on.create('ml.carbonetes.io', 'v1', 'mltasks')
def handle_mltask(body, spec, meta, namespace, logger, **kwargs):
    name = meta['name']
    script = spec.get('script')

    if not script:
        raise kopf.PermanentError("spec.script가 비어있습니다.")

    logger.info(f"[MLTask] {name} 생성 감지 - 코드 저장 및 Job 생성 시작")

    # ✅ 1. script를 ConfigMap으로 저장
    cm = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=f"{name}-script"),
        data={"main.py": script}
    )
    core = client.CoreV1Api()
    core.create_namespaced_config_map(namespace, cm)

    # ✅ 2. Job 생성
    batch = client.BatchV1Api()
    job_manifest = generate_job_manifest(name)
    batch.create_namespaced_job(namespace=namespace, body=job_manifest)

    logger.info(f"[MLTask] Job {name}-job 생성 완료")
    return {"phase": "running", "dispatchedTime": datetime.utcnow().isoformat()}


def generate_job_manifest(name):
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"{name}-job"
        },
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "exporter",
                            "image": "twkji/exporter:latest",  # ✅ 실제 이미지
                            "volumeMounts": [
                                {"name": "script-volume", "mountPath": "/mnt"}
                            ],
                            "command": ["python", "exporter.py"],
                            "env": [  # ✅ MySQL 환경변수 주입
                                {"name": "MYSQL_HOST", "value": "your-mysql-host"},
                                {"name": "MYSQL_PORT", "value": "3306"},
                                {"name": "MYSQL_USER", "value": "root"},
                                {"name": "MYSQL_PASSWORD", "value": "your-password"},
                                {"name": "MYSQL_DATABASE", "value": "carbonetes"},
                            ]
                        }
                    ],
                    "restartPolicy": "Never",
                    "volumes": [
                        {
                            "name": "script-volume",
                            "configMap": {
                                "name": f"{name}-script"
                            }
                        }
                    ]
                }
            }
        }
    }
