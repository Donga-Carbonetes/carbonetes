"use client"

import { useState, useRef } from "react"
import "./SubmitForm.css"

function SubmitForm({ addTask }) {
  const [taskName, setTaskName] = useState("")
  const [codeInputType, setCodeInputType] = useState("text")
  const [codeText, setCodeText] = useState("")
  const [codeFile, setCodeFile] = useState(null)
  const [sampleData, setSampleData] = useState(null)
  const [datasetSize, setDatasetSize] = useState("")
  const [targetLabels, setTargetLabels] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [validationError, setValidationError] = useState(null)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [dataShape, setDataShape] = useState("")
  const codeFileRef = useRef(null)
  const sampleDataRef = useRef(null)

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
      setValidationError(`다음 변수가 코드에 없습니다: ${missingVariables.join(", ")}`)
      return false
    }
    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    setSubmitSuccess(false)

    try {
      if (!taskName.trim()) {
        setValidationError("태스크 이름을 입력해주세요.")
        setIsSubmitting(false)
        return
      }

      if (codeInputType === "text" && !codeText.trim()) {
        setValidationError("코드를 입력해주세요.")
        setIsSubmitting(false)
        return
      }

      if (codeInputType === "file" && !codeFile) {
        setValidationError("코드 파일을 업로드해주세요.")
        setIsSubmitting(false)
        return
      }

      if (!sampleData) {
        setValidationError("샘플 데이터를 업로드해주세요.")
        setIsSubmitting(false)
        return
      }

      if (!datasetSize) {
        setValidationError("데이터셋 크기를 입력해주세요.")
        setIsSubmitting(false)
        return
      }

      if (!targetLabels) {
        setValidationError("타겟 레이블 개수를 입력해주세요.")
        setIsSubmitting(false)
        return
      }

      if (codeInputType === "text" && !validateCodeText(codeText)) {
        setIsSubmitting(false)
        return
      }

      const formData = new FormData()
      formData.append("taskname_user", taskName)
      formData.append("dataset_size", datasetSize);
      formData.append("label_count", targetLabels);
      formData.append("codeType", codeInputType)
      formData.append("data_shape", dataShape)
      if (codeInputType === "text") {
        formData.append("codeText", codeText)
      } else {
        formData.append("codeFile", codeFile)
      }

      formData.append("sampleData", sampleData)

      const response = await fetch("http://localhost:4000/api/tasks", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()
      addTask(data.newTask)
      setSubmitSuccess(true)

      // Reset
      setTaskName("")
      setCodeText("")
      setCodeFile(null)
      setSampleData(null)
      setDatasetSize("")
      setTargetLabels("")
      if (codeFileRef.current) codeFileRef.current.value = ""
      if (sampleDataRef.current) sampleDataRef.current.value = ""
    } catch (err) {
      console.error(err)
      setValidationError("태스크 제출 중 오류가 발생했습니다.")
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
                placeholder="딥러닝 코드를 여기에 붙여넣으세요..."
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

        <div className="form-section">
          <h2>샘플 데이터 업로드</h2>
          <input
            ref={sampleDataRef}
            type="file"
            accept=".txt,.json,.csv,.jpg,.jpeg,.png"
            onChange={(e) => setSampleData(e.target.files?.[0] || null)}
          />
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

        {validationError && <p className="error">{validationError}</p>}
        {submitSuccess && <p className="success">태스크가 성공적으로 제출되었습니다.</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "제출 중..." : "태스크 제출"}
        </button>
      </form>
    </div>
  )
}

export default SubmitForm
