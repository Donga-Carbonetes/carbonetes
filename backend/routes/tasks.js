const express = require("express");
const multer = require("multer");
const Task = require("../models/task");
const { v4: uuidv4 } = require("uuid");

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

router.post("/", upload.fields([
  { name: "codeFile", maxCount: 1 },
  { name: "sampleData", maxCount: 1 }
]), async (req, res) => {
  try {
    const { taskname_user, dataset_size, label_count, codeType, codeText } = req.body;

    const task = await Task.create({
      id: uuidv4(),
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
