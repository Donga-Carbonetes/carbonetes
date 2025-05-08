"use client"

import { useState, useRef } from "react"
import "./SubmitForm.css"

function SubmitForm({ addTask }) {
  const [codeInputType, setCodeInputType] = useState("text")
  const [codeText, setCodeText] = useState("")
  const [codeFile, setCodeFile] = useState(null)
  const [sampleData, setSampleData] = useState(null)
  const [datasetSize, setDatasetSize] = useState("")
  const [targetLabels, setTargetLabels] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [validationError, setValidationError] = useState(null)
  const [submitSuccess, setSubmitSuccess] = useState(false)

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

    const missingVariables = requiredVariables.filter((variable) => !code.includes(variable))

    if (missingVariables.length > 0) {
      setValidationError(`다음 변수가 코드에 없습니다: ${missingVariables.join(", ")}`)
      return false
    }

    setValidationError(null)
    return true
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    setSubmitSuccess(false)

    try {
      // Validate inputs
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

      // Validate code text if using text input
      if (codeInputType === "text" && !validateCodeText(codeText)) {
        setIsSubmitting(false)
        return
      }

      // Generate a task name based on the code or file
      let taskName = "새 딥러닝 태스크"
      if (codeInputType === "text") {
        // Try to extract a name from the code (e.g., from comments or class names)
        const nameMatch = codeText.match(/# (.*?) model|class (.*?)[(:]|def (.*?)[(:]|"""(.*?)"""/)
        if (nameMatch) {
          const extractedName = nameMatch.find((match, index) => index > 0 && match)
          if (extractedName) taskName = extractedName.trim()
        }
      } else {
        taskName = codeFile.name.replace(".py", "").replace(/_/g, " ")
      }

      // Create a new task
      const newTask = {
        id: `task_${Math.random().toString(36).substring(2, 15)}`,
        name: taskName,
        status: "waiting",
        codeType: codeInputType,
        sampleDataType: sampleData.type || "application/octet-stream",
        datasetSize: Number.parseInt(datasetSize),
        targetLabels: Number.parseInt(targetLabels),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }

      // Add the task to the list
      addTask(newTask)

      // Reset form on success
      if (codeInputType === "text") {
        setCodeText("")
      } else {
        setCodeFile(null)
        if (codeFileRef.current) codeFileRef.current.value = ""
      }

      setSampleData(null)
      if (sampleDataRef.current) sampleDataRef.current.value = ""
      setDatasetSize("")
      setTargetLabels("")
      setSubmitSuccess(true)
    } catch (error) {
      console.error("Error submitting task:", error)
      setValidationError("태스크 제출 중 오류가 발생했습니다.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="submit-form-container">
      <form onSubmit={handleSubmit} className="submit-form">
        {/* Code Input Section */}
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
                코드에는 batch_size, learning_rate, training_epochs, loss_function, network, optimizer 변수가 포함되어야
                합니다.
              </p>
            </div>
          ) : (
            <div className="form-group">
              <label htmlFor="codeFile">코드 파일 (.py)</label>
              <div className="file-upload-area" onClick={() => codeFileRef.current?.click()}>
                <div className="file-upload-icon">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                    <polyline points="14 2 14 8 20 8" />
                    <path d="M8 16L16 16" />
                    <path d="M8 12L16 12" />
                    <path d="M8 8L10 8" />
                  </svg>
                </div>
                <p className="file-name">{codeFile ? codeFile.name : "파이썬 파일을 업로드하세요"}</p>
                <p className="file-size">
                  {codeFile ? `${(codeFile.size / 1024).toFixed(2)} KB` : ".py 파일만 허용됩니다"}
                </p>
                <input
                  ref={codeFileRef}
                  id="codeFile"
                  type="file"
                  accept=".py"
                  className="hidden-input"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setCodeFile(e.target.files[0])
                    }
                  }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Sample Data Upload */}
        <div className="form-section">
          <h2>샘플 데이터 업로드</h2>
          <div className="file-upload-area" onClick={() => sampleDataRef.current?.click()}>
            <div className="file-upload-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="file-name">{sampleData ? sampleData.name : "샘플 데이터를 업로드하세요"}</p>
            <p className="file-size">
              {sampleData ? `${(sampleData.size / 1024).toFixed(2)} KB` : "텍스트, 이미지, JSON, CSV 파일 지원"}
            </p>
            <input
              ref={sampleDataRef}
              id="sampleData"
              type="file"
              accept=".txt,.json,.csv,.jpg,.jpeg,.png"
              className="hidden-input"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSampleData(e.target.files[0])
                }
              }}
            />
          </div>
        </div>

        {/* Dataset Information */}
        <div className="form-section">
          <h2>데이터셋 정보</h2>

          <div className="form-group">
            <label htmlFor="datasetSize">전체 데이터셋 크기</label>
            <input
              id="datasetSize"
              type="number"
              placeholder="예: 10000"
              value={datasetSize}
              onChange={(e) => setDatasetSize(e.target.value)}
            />
            <p className="form-hint">전체 학습 데이터셋의 크기를 입력하세요.</p>
          </div>

          <div className="form-group">
            <label htmlFor="targetLabels">타겟 레이블 개수</label>
            <input
              id="targetLabels"
              type="number"
              placeholder="예: 10"
              value={targetLabels}
              onChange={(e) => setTargetLabels(e.target.value)}
            />
            <p className="form-hint">데이터셋의 타겟 레이블 개수를 입력하세요.</p>
          </div>
        </div>

        {/* Error and Success Messages */}
        {validationError && (
          <div className="alert error">
            <div className="alert-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <div className="alert-content">
              <h4>오류</h4>
              <p>{validationError}</p>
            </div>
          </div>
        )}

        {submitSuccess && (
          <div className="alert success">
            <div className="alert-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
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
            </div>
            <div className="alert-content">
              <h4>성공</h4>
              <p>태스크가 성공적으로 제출되었습니다. 모니터링 탭에서 진행 상황을 확인할 수 있습니다.</p>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <button type="submit" className="submit-button" disabled={isSubmitting}>
          {isSubmitting ? "제출 중..." : "태스크 제출"}
        </button>
      </form>
    </div>
  )
}

export default SubmitForm
