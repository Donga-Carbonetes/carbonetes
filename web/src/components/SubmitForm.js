"use client"

import { useState, useRef } from "react"
import Modal from "./Modal"
import "./Modal.css"
import "./SubmitForm.css"

const HOST = process.env.REACT_APP_BACKEND_HOST
const PORT = process.env.REACT_APP_BACKEND_PORT
const API_URL = "http://211.253.31.134:4000/api/tasks"
function SubmitForm({ addTask }) {
  const [taskName, setTaskName] = useState("")
  const [codeInputType, setCodeInputType] = useState("text")
  const [codeText, setCodeText] = useState("")
  const [codeFile, setCodeFile] = useState(null)
  const [datasetSize, setDatasetSize] = useState("")
  const [targetLabels, setTargetLabels] = useState("")
  const [dataShape, setDataShape] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [modalMessage, setModalMessage] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const codeFileRef = useRef(null)

  const validateCodeText = (code) => {
    const requiredVariables = [
      "batch_size",
      "learning_rate",
      "training_epochs",
      "loss_function",
      "network",
      "optimizer",
    ]
    const missingVariables = requiredVariables.filter((v) => !code.includes(v))
    if (missingVariables.length > 0) {
      throw new Error(`다음 변수가 코드에 없습니다: ${missingVariables.join(", ")}`)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      if (!taskName.trim()) throw new Error("태스크 이름을 입력해주세요.")
      if (codeInputType === "text" && !codeText.trim()) throw new Error("코드를 입력해주세요.")
      if (codeInputType === "file" && !codeFile) throw new Error("코드 파일을 업로드해주세요.")
      if (!datasetSize) throw new Error("데이터셋 크기를 입력해주세요.")
      if (!targetLabels) throw new Error("타겟 레이블 개수를 입력해주세요.")
      if (codeInputType === "text") validateCodeText(codeText)

      const formData = new FormData()
      formData.append("taskname_user", taskName)
      formData.append("dataset_size", datasetSize)
      formData.append("label_count", targetLabels)
      formData.append("codeType", codeInputType)
      formData.append("data_shape", dataShape)

      if (codeInputType === "text") {
        formData.append("codeText", codeText)
      } else {
        formData.append("codeFile", codeFile)
      }

      const response = await fetch(API_URL, {
        method: "POST",
        body: formData,
      })

      const data = await response.json()
      addTask(data.newTask)

      setModalMessage("✅ 태스크가 성공적으로 제출되었습니다.")
      setIsModalOpen(true)

      // Reset
      setTaskName("")
      setCodeText("")
      setCodeFile(null)
      setDatasetSize("")
      setTargetLabels("")
      setDataShape("")
      if (codeFileRef.current) codeFileRef.current.value = ""
    } catch (err) {
      console.error(err)
      setModalMessage(`❌ ${err.message || "태스크 제출 중 오류가 발생했습니다."}`)
      setIsModalOpen(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="submit-form-container">
      <form onSubmit={handleSubmit} className="submit-form">
        <div className="form-section">
          <h2>태스크 정보</h2>
          <div className="form-group">
            <label htmlFor="taskName">태스크 이름</label>
            <input
              id="taskName"
              type="text"
              placeholder="예: ResNet 학습 태스크"
              value={taskName}
              onChange={(e) => setTaskName(e.target.value)}
            />
            <p className="form-hint">식별하기 쉬운 태스크 이름을 입력하세요.</p>
          </div>
        </div>

        <div className="form-section">
          <h2>딥러닝 코드 입력</h2>
          <div className="code-input-tabs">
            <button
              type="button"
              className={`code-tab ${codeInputType === "text" ? "active" : ""}`}
              onClick={() => setCodeInputType("text")}
            >
              텍스트로 입력
            </button>
            <button
              type="button"
              className={`code-tab ${codeInputType === "file" ? "active" : ""}`}
              onClick={() => setCodeInputType("file")}
            >
              파일 업로드
            </button>
          </div>

          {codeInputType === "text" ? (
            <div className="form-group">
              <label htmlFor="codeText">코드 텍스트</label>
              <textarea
                id="codeText"
                placeholder="딥러닝 코드를 입력하세요"
                className="code-textarea"
                value={codeText}
                onChange={(e) => setCodeText(e.target.value)}
              />
              <p className="form-hint">
                코드에는 batch_size, learning_rate, training_epochs, loss_function, network, optimizer 변수가 포함되어야 합니다.
              </p>
            </div>
          ) : (
            <div className="form-group">
              <label htmlFor="codeFile">코드 파일 (.py)</label>
              <input
                ref={codeFileRef}
                type="file"
                accept=".py"
                onChange={(e) => setCodeFile(e.target.files?.[0] || null)}
              />
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="dataShape">데이터 쉐입</label>
          <input
            id="dataShape"
            type="text"
            placeholder="예: 3,32,32"
            value={dataShape}
            onChange={(e) => setDataShape(e.target.value)}
          />
          <p className="form-hint">쉼표로 구분된 숫자를 입력하세요 (예: 3,32,32)</p>
        </div>

        <div className="form-section">
          <h2>데이터셋 정보</h2>
          <div className="form-group">
            <label htmlFor="datasetSize">전체 데이터셋 크기</label>
            <input
              type="number"
              id="datasetSize"
              placeholder="예: 10000"
              value={datasetSize}
              onChange={(e) => setDatasetSize(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="targetLabels">타겟 레이블 개수</label>
            <input
              type="number"
              id="targetLabels"
              placeholder="예: 10"
              value={targetLabels}
              onChange={(e) => setTargetLabels(e.target.value)}
            />
          </div>
        </div>

        <button type="submit" className="submit-button" disabled={isSubmitting}>
          {isSubmitting ? "제출 중..." : "태스크 제출"}
        </button>
      </form>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        <p>{modalMessage}</p>
      </Modal>
    </div>
  )
}

export default SubmitForm
