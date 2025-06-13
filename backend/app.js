process.env.NODE_EXTRA_CA_CERTS = "/root/k3s-ca.crt";

const express = require("express");
const multer = require("multer");
const Task = require("./models/Task");
const taskRoutes = require("./routes/tasks");
const cors = require("cors");

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

// ✅ CORS 허용 (프론트와 통신 허용)
app.use(cors());

// ✅ JSON, form 데이터 파싱 허용
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ✅ 태스크 API 라우터 등록 (/routes/tasks.js에 정의된 POST/GET 라우터 사용)
app.use("/api/tasks", taskRoutes);

// ✅ 소켓 적용: http 서버로 감싸기
const http = require("http");
const socket = require("./socket");
const server = http.createServer(app);
socket.init(server);

// ✅ 서버 실행
const PORT = 4000;
server.listen(PORT, "0.0.0.0", () => {
  console.log(`✅ Server listening on http://0.0.0.0:${PORT}`);
});
