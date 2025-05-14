const express = require("express");            // Express 웹 프레임워크
const multer = require("multer");              // 파일 업로드를 처리해주는 미들웨어
const Task = require("../models/task");        // Sequelize 모델: task_info 테이블
const { v4: uuidv4 } = require("uuid");        // 고유한 ID 생성기

const router = express.Router();               // 라우터 객체 생성
const upload = multer({ storage: multer.memoryStorage() });  // 파일을 메모리에 저장하도록 multer 설정


/**
 * POST /api/tasks
 * 새로운 태스크 등록
 */
router.post("/", upload.fields([//사용자가 올리는 파일 2개(codeFile, sampleData)를 받기 위한 multer 설정
  { name: "codeFile", maxCount: 1 },
  { name: "sampleData", maxCount: 1 }
]), async (req, res) => {
  try {
    const { taskname_user, dataset_size, label_count, codeType, codeText } = req.body;

    const task = await Task.create({//DB에 새로운 태스크를 생성
      id: uuidv4(),  // UUID로 고유 ID 생성
      taskname_user,   
      dataset_size,
      label_count,
      codeType,
      data_shape: "", 
      codeText: codeText || null,
      codeFileName: req.files?.codeFile?.[0]?.originalname || null,
      sampleDataName: req.files?.sampleData?.[0]?.originalname || null,
    });

    res.json({ message: "등록 완료", newTask: task });
  } catch (err) {
    console.error(err);
    res.status(500).json({ message: "DB 저장 실패", error: err });
  }
});


/**
 * GET /api/tasks
 * 태스크 목록 조회 (기본: 생성일 기준 최신순)
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
