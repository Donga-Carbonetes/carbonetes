import kopf
import os
from kubernetes import client, config
from datetime import datetime, timezone
import asyncio

config.load_incluster_config()

@kopf.on.create('ml.carbonetes.io', 'v1', 'mltasks')
def handle_mltask(body, spec, meta, namespace, logger, patch, **kwargs):
    name = meta['name']
    script = spec.get('script')

    if not script:
        raise kopf.PermanentError("spec.script가 비어있습니다.")

    logger.info(f"[MLTask] {name} 생성 감지 - 코드 저장 및 Job 생성 시작")

    cm = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=f"{name}-script"),
        data={f"{name}.py": script}
    )
    core = client.CoreV1Api()
    core.create_namespaced_config_map(namespace, cm)

    batch = client.BatchV1Api()
    job_manifest = generate_job_manifest(name)
    batch.create_namespaced_job(namespace=namespace, body=job_manifest)

    logger.info(f"[MLTask] Job {name}-job 생성 완료")

    patch.status["phase"] = "waiting"
    patch.status["startTime"] = datetime.now(timezone.utc).isoformat()
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

# @kopf.on.field('ml.carbonetes.io', 'v1', 'mltasks', field='status.phase')
# async def on_terminated_phase(old, new, meta, namespace, logger, **kwargs):
#     name = meta['name']
#     if new == "terminated":
#         logger.info(f"[MLTask] {name}가 terminated 상태입니다. 5분 뒤 ConfigMap 및 mltask 리소스 삭제 예약됨.")
#         await asyncio.sleep(300)  # 5분 대기

#         # CoreV1Api 인스턴스
#         core = client.CoreV1Api()
#         # CustomObjectsApi 인스턴스
#         custom = client.CustomObjectsApi()

#         cm_name = f"{name}-script"

#         # ConfigMap 삭제
#         try:
#             core.delete_namespaced_config_map(
#                 name=cm_name,
#                 namespace=namespace,
#                 body=client.V1DeleteOptions()
#             )
#             logger.info(f"[MLTask] ConfigMap {cm_name} 삭제 완료.")
#         except client.exceptions.ApiException as e:
#             if e.status != 404:
#                 logger.error(f"[MLTask] ConfigMap 삭제 중 오류: {e}")
#             else:
#                 logger.warning(f"[MLTask] ConfigMap {cm_name} 이미 없음 (404)")

#         # mltask 리소스 자체 삭제
#         try:
#             custom.delete_namespaced_custom_object(
#                 group="ml.carbonetes.io",
#                 version="v1",
#                 namespace=namespace,
#                 plural="mltasks",
#                 name=name,
#                 body=client.V1DeleteOptions()
#             )
#             logger.info(f"[MLTask] Custom Resource {name} 삭제 완료.")
#         except client.exceptions.ApiException as e:
#             if e.status != 404:
#                 logger.error(f"[MLTask] Custom Resource 삭제 중 오류: {e}")
#             else:
#                 logger.warning(f"[MLTask] Custom Resource {name} 이미 없음 (404)")



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
                    "serviceAccountName": "mltask-updater",
                    "containers": [
                        {
                            "name": "exporter",
                            "image": "twkji/exporter:latest",
                            "volumeMounts": [
                                {"name": "script-volume", "mountPath": "/mnt"}
                            ],
                            "command": ["python", "exporter.py"],
                            "env": [ 
                                {"name": "MYSQL_HOST", "value": 'mysql'},
                                {"name": "MYSQL_PORT", "value": '3306'},
                                {"name": "MYSQL_USER", "value": "root"},
                                {"name": "MYSQL_PASSWORD", "value": os.getenv("MYSQL_PASSWORD")},
                                {"name": "MYSQL_DATABASE", "value": "carbonetes"},
                                {"name": "TASK_NAME", "value": f"{name}"},
                                {"name": "MINIO_HOST", "value": "minio-1747233997.minio"},
                                {"name": "MINIO_PORT", "value": "9000"},
                                {"name": "MINIO_USER", "value": "rootuser"},
                                {"name": "MINIO_PASSWORD", "value": "rootpass123"},
                                {"name": "SCHEDULER_HOST", 
                                 "valueFrom": {
                                     "secretKeyRef": {
                                         "name": "scheduler-secret",
                                         "key": "SCHEDULER_HOST"
                                     }
                                 }},
                                {"name": "SCHEDULER_PORT", 
                                 "valueFrom": {
                                     "secretKeyRef": {
                                         "name": "scheduler-secret",
                                         "key": "SCHEDULER_PORT"
                                     }
                                 }},

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
