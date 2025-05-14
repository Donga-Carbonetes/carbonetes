"use client";

import { useState, useEffect } from "react";
import "./TaskMonitor.css";

function TaskMonitor() {
  const [tasks, setTasks] = useState([]);
  const [activeTab, setActiveTab] = useState("all");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTasks = () => {
      fetch("http://localhost:4000/api/tasks")
      .then((res) => res.json())
      .then((data) => {
        const mappedTasks = data.tasks.map(task => ({
          id: task.id,
          name: task.taskname_user,  
          datasetSize: task.dataset_size,
          targetLabels: task.label_count,
          status: (task.status || "ready") === "ready" ? "waiting" : task.status,
          createdAt: task.created_at,
          updatedAt: task.updated_at,
        }));
        setTasks(mappedTasks);
        setIsLoading(false);
      })
    
        .catch((err) => {
          console.error("목록 로딩 실패:", err);
          setIsLoading(false);
        });
    };
  
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, []);
  

  const getFilteredTasks = () => {
    if (activeTab === "all") return tasks;
    return tasks.filter((task) => task.status === activeTab);
  };

  const taskCounts = {
    all: tasks.length,
    waiting: tasks.filter((t) => t.status === "waiting").length,
    running: tasks.filter((t) => t.status === "running").length,
    completed: tasks.filter((t) => t.status === "completed").length,
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";// null 체크를 추가
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(date);
  };
  

  const getStatusBadge = (status) => {
    switch (status) {
      case "waiting":
        return <span className="status-badge waiting">대기 중</span>;
      case "running":
        return <span className="status-badge running">실행 중</span>;
      case "completed":
        return <span className="status-badge completed">완료됨</span>;
      case "failed":
        return <span className="status-badge failed">실패</span>;
      default:
        return <span className="status-badge">{status}</span>;
    }
  };

  const filteredTasks = getFilteredTasks();

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
          {Object.entries(taskCounts).map(([key, count]) => (
            <button
              key={key}
              className={`task-tab ${activeTab === key ? "active" : ""}`}
              onClick={() => setActiveTab(key)}
            >
              {key === "all" ? "전체" : key === "waiting" ? "대기 중" : key === "running" ? "실행 중" : "완료됨"} ({count})
            </button>
          ))}
        </div>

        <div className="task-table-container">
          {isLoading ? (
            <div className="loading-container">불러오는 중...</div>
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
                    <td>{task.id.toString().substring(0, 8)}</td>
                    <td>{task.name}</td>
                    <td>{getStatusBadge(task.status)}</td>
                    <td>{task.datasetSize}</td>
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
  );
}

export default TaskMonitor;
