"use client"

import { useState, useEffect } from "react"
import "./TaskMonitor.css"

function TaskMonitor({ tasks }) {
  const [activeTab, setActiveTab] = useState("all")
  const [isLoading, setIsLoading] = useState(true)
  const [filteredTasks, setFilteredTasks] = useState([])

  useEffect(() => {
    let isMounted = true // cleanup 대비용
  
    const fetchTasks = () => {
      fetch("http://localhost:4000/api/tasks")
        .then((res) => res.json())
        .then((data) => {
          if (isMounted) {
            setFilteredTasks(data.tasks)
            setIsLoading(false)
          }
        })
        .catch((err) => {
          console.error("목록 로딩 실패:", err)
          setIsLoading(false)
        })
    }
  
    fetchTasks()
    const interval = setInterval(fetchTasks, 3000)
  
    return () => {
      isMounted = false
      clearInterval(interval)
    }
  }, [])
  
  
  

  const getStatusBadge = (status) => {
    switch (status) {
      case "waiting":
        return (
          <span className="status-badge waiting">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            대기 중
          </span>
        )
      case "running":
        return (
          <span className="status-badge running">
            <svg
              className="spinner"
              xmlns="http://www.w3.org/2000/svg"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
              <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
              <line x1="2" y1="12" x2="6" y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
              <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
              <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
            </svg>
            실행 중
          </span>
        )
      case "completed":
        return (
          <span className="status-badge completed">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            완료됨
          </span>
        )
      case "failed":
        return (
          <span className="status-badge failed">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            실패
          </span>
        )
      default:
        return <span className="status-badge">{status}</span>
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(date)
  }

  const getTaskCounts = () => {
    const counts = {
      all: tasks.length,
      waiting: tasks.filter((task) => task.status === "waiting").length,
      running: tasks.filter((task) => task.status === "running").length,
      completed: tasks.filter((task) => task.status === "completed").length,
    }
    return counts
  }

  const taskCounts = getTaskCounts()

  return (
    <div className="task-monitor-container">
      <div className="stats-cards">
        <div className="stat-card">
          <div className="stat-title">전체 태스크</div>
          <div className="stat-value">{taskCounts.all}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">대기 중</div>
          <div className="stat-value waiting">{taskCounts.waiting}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">실행 중</div>
          <div className="stat-value running">{taskCounts.running}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">완료됨</div>
          <div className="stat-value completed">{taskCounts.completed}</div>
        </div>
      </div>

      <div className="task-list-container">
        <h2>태스크 목록</h2>

        <div className="task-tabs">
          <button className={`task-tab ${activeTab === "all" ? "active" : ""}`} onClick={() => setActiveTab("all")}>
            전체 ({taskCounts.all})
          </button>
          <button
            className={`task-tab ${activeTab === "waiting" ? "active" : ""}`}
            onClick={() => setActiveTab("waiting")}
          >
            대기 중 ({taskCounts.waiting})
          </button>
          <button
            className={`task-tab ${activeTab === "running" ? "active" : ""}`}
            onClick={() => setActiveTab("running")}
          >
            실행 중 ({taskCounts.running})
          </button>
          <button
            className={`task-tab ${activeTab === "completed" ? "active" : ""}`}
            onClick={() => setActiveTab("completed")}
          >
            완료됨 ({taskCounts.completed})
          </button>
        </div>

        <div className="task-table-container">
          {isLoading ? (
            <div className="loading-container">
              <div className="spinner-large"></div>
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="no-tasks-message">태스크가 없습니다.</div>
          ) : (
            <table className="task-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>태스크 이름</th>
                  <th>상태</th>
                  <th>데이터셋 크기</th>
                  <th>레이블 수</th>
                  <th>제출 시간</th>
                  <th>업데이트 시간</th>
                </tr>
              </thead>
              <tbody>
                {filteredTasks.map((task) => (
                  <tr key={task.id}>
                    <td className="task-id">{task.id.substring(0, 8)}</td>
                    <td>{task.name}</td>
                    <td>{getStatusBadge(task.status)}</td>
                    <td>{task.datasetSize.toLocaleString()}</td>
                    <td>{task.targetLabels}</td>
                    <td>{formatDate(task.createdAt)}</td>
                    <td>{formatDate(task.updatedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

export default TaskMonitor
