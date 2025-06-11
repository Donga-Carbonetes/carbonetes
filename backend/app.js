process.env.NODE_EXTRA_CA_CERTS = "/root/k3s-ca.crt";
const express = require("express")
const multer = require("multer")
const Task = require("./models/Task")
const taskRoutes = require("./routes/tasks");
const app = express()
const upload = multer({ storage: multer.memoryStorage() })
const cors = require("cors");

 // CORS 허용 (프론트와 통신 허용)
app.use(cors());

// 태스크 API 라우터 등록 (/routes/tasks.js에 정의된 POST/GET 라우터 사용)
app.use("/api/tasks", taskRoutes);

// JSON, form 데이터 파싱 허용
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

// 전체 태스크 조회
app.get("/api/tasks", async (req, res) => {
  const tasks = await Task.findAll();
  order: [['created_at', 'ASC']], // 오래된 순으로 정렬
  res.json({ tasks }); 
})

// 소켓 적용: http 서버로 감싸기
const http = require("http");
const socket = require("./socket");
const server = http.createServer(app);
socket.init(server);

// POST 요청: 태스크 등록
app.post(
  "/api/tasks",
  upload.fields([
    { name: "codeFile", maxCount: 1 },
    { name: "sampleData", maxCount: 1 },
  ]),
  async (req, res) => {
    try {
      const { name, datasetSize, targetLabels, codeType, codeText } = req.body
      const codeFile = req.files?.codeFile?.[0]
      const sampleData = req.files?.sampleData?.[0]

      const id = `task_${Math.random().toString(36).substring(2, 12)}`
      const createdAt = new Date().toISOString()
      const updatedAt = createdAt

      const newTask = await Task.create({
        id,
        name,
        datasetSize,
        targetLabels,
        codeType,
        codeText,
        codeFileName: codeFile?.originalname || null,
        sampleDataName: sampleData?.originalname || null,
        createdAt,
        updatedAt,
      })

      console.log("새 태스크 등록됨:", newTask.toJSON())
      res.status(201).json({ newTask })
    } catch (err) {
      console.error("태스크 등록 중 오류:", err)
      res.status(500).json({ error: "태스크 등록 실패" })
    }
  }
)

// 서버 실행
const PORT = 4000
server.listen(PORT, "0.0.0.0", () => {
  console.log(`✅ Server listening on http://0.0.0.0:${PORT}`)
})

