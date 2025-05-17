// self-signed 인증서 무시 (개발용에서만!)
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const express = require("express");
const multer = require("multer");
const { v4: uuidv4 } = require("uuid");
const Task = require("../models/task");
const k8s = require('@kubernetes/client-node'); // Kubernetes 클라이언트
const fs = require("fs");
const dayjs = require("dayjs");

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() }); // 메모리 저장

/**
 * ✅ MLTask 생성 함수
 */
async function createMLTaskFromFile(scriptPath, datashape, datasetSize, labelCount, namespace = 'default') {
  const scriptContent = fs.readFileSync(scriptPath, 'utf8');
  const taskName = `mltask-${dayjs().format('YYYYMMDDHHmmss')}`;

  const body = {
    apiVersion: 'ml.carbonetes.io/v1', // apiVersion은 반드시 group/version 형식
    kind: 'MLTask',
    metadata: { name: taskName },
    spec: {
      datashape,
      dataset_size: datasetSize,
      label_count: labelCount,
      script: scriptContent,
    },
  };

  const kc = new k8s.KubeConfig();
  kc.loadFromDefault(); // ~/.kube/config 사용

  const k8sApi = kc.makeApiClient(k8s.CustomObjectsApi); 

  console.log('✅ 현재 컨텍스트:', kc.getCurrentContext());
  console.log('🛠️ [디버깅] MLTask 생성 시 body:', JSON.stringify(body, null, 2));

  try {
    const result = await k8sApi.createNamespacedCustomObject.call(
      k8sApi,
      'ml.carbonetes.io',
      'v1',
      'default',
      'mltasks',
      body
    );
  
    console.log(`✅ MLTask ${taskName} 생성 완료`);
    return result.body;
  } catch (err) {
    console.error('❌ MLTask 생성 실패:', err.body || err.message || err);
    throw err;
  }
}

/**
 * ✅ POST /api/tasks - 태스크 등록 및 MLTask 생성
 */
router.post("/", upload.fields([
  { name: "codeFile", maxCount: 1 },
  { name: "sampleData", maxCount: 1 }
]), async (req, res) => {
  try {
    const { taskname_user, dataset_size, label_count, codeType, codeText } = req.body;
    const taskId = uuidv4(); 
    const task = await Task.create({
      id: uuidv4(),
      task_name: `mltask-${taskId}`, 
      taskname_user,
      dataset_size,
      label_count,
      codeType,
      data_shape: "",
      codeText: codeText || null,
      codeFileName: req.files?.codeFile?.[0]?.originalname || null,
      sampleDataName: req.files?.sampleData?.[0]?.originalname || null,
      status: "ready",  
    });

    // ✅ MLTask 생성 함수 호출
    await createMLTaskFromFile(
      "/carbonetes/exporter/sample_resnet.py", 
      [3, 32, 32],                             
      parseInt(dataset_size),
      parseInt(label_count)
    );

    res.json({ message: "등록 완료", newTask: task });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: "DB 저장 또는 MLTask 생성 실패", error: err });
  }
});

/**
 * ✅ GET /api/tasks - 태스크 목록 조회
 */
router.get("/", async (req, res) => {
  try {
    const tasks = await Task.findAll({ order: [["created_at", "DESC"]] });
    res.json({ tasks });
  } catch (err) {
    console.error("Task 목록 조회 실패:", err);
    res.status(500).json({ message: "불러오기 실패", error: err });
  }
});

module.exports = router;
