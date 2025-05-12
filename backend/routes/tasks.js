const express = require('express');
const multer = require('multer');
const path = require('path');

const router = express.Router();

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + '-' + file.originalname);
  }
});

const upload = multer({ storage: storage });

let tasks = []; // 메모리 내 임시 저장소

router.post('/', upload.fields([
  { name: 'codeFile', maxCount: 1 },
  { name: 'sampleData', maxCount: 1 }
]), (req, res) => {
  const { datasetSize, targetLabels, codeType } = req.body;

  const newTask = {
    id: `task_${Date.now()}`,
    name: req.body.name || "unnamed-task",
    datasetSize: parseInt(datasetSize),
    targetLabels: parseInt(targetLabels),
    codeType,
    status: 'ready',
    createdAt: new Date().toISOString(),
    codeFile: req.files['codeFile']?.[0]?.filename || null,
    sampleData: req.files['sampleData']?.[0]?.filename || null,
  };

  tasks.push(newTask);
  res.json({ success: true, task: newTask });
});

router.get('/', (req, res) => {
  res.json({ tasks });
});

module.exports = router;
