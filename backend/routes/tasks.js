// self-signed 인증서 무시 (개발용에서만!)
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const express = require("express");
const multer = require("multer");
const { v4: uuidv4 } = require("uuid");
const Task = require("../models/task");
const k8s = require('@kubernetes/client-node');
const fs = require("fs");
const dayjs = require("dayjs");

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

/**
 * ✅ MLTask 생성 함수 (scriptContent 기반)
 */
async function createMLTask(taskName, scriptContent, datashape, datasetSize, labelCount, namespace = 'default') {
  const body = {
    apiVersion: 'ml.carbonetes.io/v1',
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
  kc.loadFromDefault();
  const k8sApi = kc.makeApiClient(k8s.CustomObjectsApi);

  console.log('✅ 현재 컨텍스트:', kc.getCurrentContext());
  console.log('🛠️ [디버깅] MLTask 생성 시 body:', JSON.stringify(body, null, 2));

  try {
    const result = await k8sApi.createNamespacedCustomObject(
      'ml.carbonetes.io',
      'v1',
      namespace,
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
    const { taskname_user, dataset_size, label_count, codeType, codeText, data_shape } = req.body;
    const taskId = uuidv4(); 
    const taskName = `mltask-${taskId}`;

    // ✅ 코드 내용 결정 (텍스트 or 업로드 파일)
    const scriptContent =
      codeType === "text"
        ? codeText
        : req.files?.codeFile?.[0]?.buffer.toString("utf-8");

    const task = await Task.create({
      id: taskId,
      task_name: taskName,
      taskname_user,
      dataset_size,
      label_count,
      codeType,
      data_shape: data_shape || "",
      codeText: codeType === "text" ? codeText : null,
      codeFileName: req.files?.codeFile?.[0]?.originalname || null,
      sampleDataName: req.files?.sampleData?.[0]?.originalname || null,
      status: "ready",
    });

    // ✅ MLTask 생성
    await createMLTask(
      taskName,
      scriptContent,
      data_shape.split(",").map(x => parseInt(x.trim())),
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