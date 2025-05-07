import kopf
import os
from kubernetes import client, config
from datetime import datetime, timezone

config.load_kube_config()

@kopf.on.create('ml.carbonetes.io', 'v1', 'mltasks')
def handle_mltask(body, spec, meta, namespace, logger, **kwargs):
    name = meta['name']
    script = spec.get('script')

    if not script:
        raise kopf.PermanentError("spec.script가 비어있습니다.")

    logger.info(f"[MLTask] {name} 생성 감지 - 코드 저장 및 Job 생성 시작")

    cm = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=f"{name}-script"),
        data={"main.py": script}
    )
    core = client.CoreV1Api()
    core.create_namespaced_config_map(namespace, cm)

    batch = client.BatchV1Api()
    job_manifest = generate_job_manifest(name)
    batch.create_namespaced_job(namespace=namespace, body=job_manifest)

    logger.info(f"[MLTask] Job {name}-job 생성 완료")
    return {"phase": "waiting", "startTime": datetime.now(timezone.utc).isoformat()}

@kopf.on.delete('ml.carbonetes.io', 'v1', 'mltasks')
def delete_mltask(body, spec, meta, namespace, logger, **kwargs):
    name = meta['name']
    batch = client.BatchV1Api()
    core = client.CoreV1Api()

    job_name = f"{name}-job"
    cm_name = f"{name}-script"

    try:
        logger.info(f"[MLTask] {name} 삭제 감지 - 관련 Job/ConfigMap 삭제 중...")

        # Job 삭제
        batch.delete_namespaced_job(
            name=job_name,
            namespace=namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground")
        )

        # ConfigMap 삭제
        core.delete_namespaced_config_map(
            name=cm_name,
            namespace=namespace,
            body=client.V1DeleteOptions()
        )

        logger.info(f"[MLTask] {name} 관련 리소스 삭제 완료")

    except client.exceptions.ApiException as e:
        logger.error(f"[MLTask] 삭제 중 오류 발생: {e}")


def generate_job_manifest(name):
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": f"{name}-job"
        },
        "spec": {
            "backoffLimit": 3,  
            "ttlSecondsAfterFinished": 600,  # 5분뒤 정리 job 삭제
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "exporter",
                            "image": "twkji/exporter:latest",
                            "volumeMounts": [
                                {"name": "script-volume", "mountPath": "/mnt"}
                            ],
                            "command": ["python", "exporter.py"],
                            "env": [ 
                                {"name": "MYSQL_HOST", "value": os.getenv("MYSQL_HOST")},
                                {"name": "MYSQL_PORT", "value": os.getenv("MYSQL_PORT")},
                                {"name": "MYSQL_USER", "value": "root"},
                                {"name": "MYSQL_PASSWORD", "value": os.getenv("MYSQL_PASSWORD")},
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
