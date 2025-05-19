"use client"

import { useState } from "react"
import SubmitForm from "./components/SubmitForm"
import TaskMonitor from "./components/TaskMonitor"
import "./App.css"
// const API_URL = "http://localhost:4000/api/tasks"; // 백엔드 주소
const HOST = process.env.BACKEND_HOST
const PORT = process.env.BACKEND_PORT
const API_URL = f`http://${HOST}:${PORT}/api/tasks`; // 백엔드 주소

function App() {
  const [activeTab, setActiveTab] = useState("submit")
  const [tasks, setTasks] = useState([
    // {
    //   id: "task_1234567890",
    //   name: "MNIST 분류기",
    //   status: "completed",
    //   codeType: "text",
    //   sampleDataType: "image/png",
    //   datasetSize: 60000,
    //   targetLabels: 10,
    //   createdAt: "2025-05-04T10:30:00Z",
    //   updatedAt: "2025-05-04T11:45:00Z",
    // },
    // {
    //   id: "task_2345678901",
    //   name: "감성 분석 모델",
    //   status: "running",
    //   codeType: "file",
    //   sampleDataType: "text/plain",
    //   datasetSize: 25000,
    //   targetLabels: 2,
    //   createdAt: "2025-05-04T14:20:00Z",
    //   updatedAt: "2025-05-04T14:20:00Z",
    // },
    // {
    //   id: "task_3456789012",
    //   name: "이미지 세그멘테이션",
    //   status: "waiting",
    //   codeType: "text",
    //   sampleDataType: "image/jpeg",
    //   datasetSize: 8000,
    //   targetLabels: 20,
    //   createdAt: "2025-05-04T15:10:00Z",
    //   updatedAt: "2025-05-04T15:10:00Z",
    // },
  ])

  const addTask = (newTask) => {
    setTasks([newTask, ...tasks])
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>딥러닝 태스크 관리 시스템</h1>
      </header>

      <div className="tab-container">
        <div className="tabs">
          <button className={`tab ${activeTab === "submit" ? "active" : ""}`} onClick={() => setActiveTab("submit")}>
            태스크 제출
          </button>
          <button className={`tab ${activeTab === "monitor" ? "active" : ""}`} onClick={() => setActiveTab("monitor")}>
            태스크 모니터링
          </button>
        </div>

        <div className="tab-content">
          {activeTab === "submit" ? <SubmitForm addTask={addTask} /> : <TaskMonitor tasks={tasks} />}
        </div>
      </div>
    </div>
  )
}

export default App
