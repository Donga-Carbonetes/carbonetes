const express = require("express")
const cors = require("cors")
const multer = require("multer")
const app = express()
const PORT = 4000

app.use(cors())
app.use(express.json())

// 메모리 저장소 (DB 대신)
const tasks = []

// 파일 업로드 처리
const upload = multer({ storage: multer.memoryStorage() })

// GET /api/tasks → 전체 목록
app.get("/api/tasks", (req, res) => {
  res.json({ tasks })
})

// POST /api/tasks → 태스크 등록
app.post("/api/tasks", upload.fields([
  { name: "codeFile", maxCount: 1 },
  { name: "sampleData", maxCount: 1 }
]), (req, res) => {
  const { name, datasetSize, targetLabels, codeType, codeText } = req.body
  const id = `task_${Math.random().toString(36).substring(2, 12)}`
  const createdAt = new Date().toISOString()

  const newTask = {
    id,
    name,
    datasetSize: parseInt(datasetSize),
    targetLabels: parseInt(targetLabels),
    codeType,
    codeText: codeText || null,
    codeFileName: req.files?.codeFile?.[0]?.originalname || null,
    sampleDataName: req.files?.sampleData?.[0]?.originalname || null,
    status: "waiting",
    createdAt,
    updatedAt: createdAt,
  }

  tasks.push(newTask)
  res.json({ message: "등록 완료", newTask })
})

// 서버 시작
app.listen(PORT, () => {
  console.log(`✅ Server listening on http://localhost:${PORT}`)
})
