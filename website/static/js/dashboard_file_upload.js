document.addEventListener("DOMContentLoaded", () => {

  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('pdf-upload');
  const fileInfo = document.getElementById('file-info');
  const fileName = document.getElementById('file-name');
  const fileSize = document.getElementById('file-size');
  const removeFileBtn = document.getElementById('remove-file');
  const uploadProgress = document.getElementById('upload-progress');
  const progressBar = document.getElementById('progress-bar');
  const progressPercent = document.getElementById('progress-percent');
  const uploadBtn = document.getElementById('upload-btn');
  const cancelBtn = document.getElementById('cancel-btn');
  const successMessage = document.getElementById('success-message');
  const form = document.getElementById('pdf-upload-form');
  const URL = window.location.origin; // Base URL for your application
  let selectedFile = null;
  let uploadController = null;

  // ======= ADDED FOR WEBSOCKET & JOB STATUS =======
  let currentLoadingCardId = null;
  let ws = null;
  let jobId = null;

  async function restoreJobStatus() {
    jobId = localStorage.getItem('jobId');
    if (!jobId) return;

    try {
      const res = await fetch(`/job-status/${jobId}`);
      if (!res.ok) throw new Error("Job not found");
      const data = await res.json();

      if (data.status === "error") {
        localStorage.removeItem('jobId');
        removeLoadingCard();
        showFlashMessage('An error occurred during processing', true);}

      if (data.status === "processing") {
        createLoadingExamCard("Uploading Exam...");
        connectWebSocket();
      } else if (data.status === "done") {
        updateLoadingCardToSuccess(jobId, data.result.examName);
        localStorage.removeItem('jobId'); // clear after done
        
      }
    } catch (e) {
      console.warn("Could not restore job status:", e);
      localStorage.removeItem('jobId');
    }
  }

function connectWebSocket() {
    if (!jobId) return;

    ws = new WebSocket(`wss://${window.location.host}/ws/${jobId}`); //PRODUCTION-FLAG

    ws.onmessage = (event) => {
        if (event.data === "done") {
            fetch(`/job-status/${jobId}`)
              .then(r => r.json())
              .then(data => {
                if (data.status === "done" && data.result) {
                    updateLoadingCardToSuccess(data.result.examId, data.result.examName);
                    localStorage.removeItem('jobId');
                    // Send ack only if socket is still open
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send("ack");
                    }
                        ws.close();
                    }
                });
        }
    };

    ws.onclose = () => {
        console.log("WebSocket connection closed");
    };

    ws.onerror = (err) => {
        console.error("WebSocket error", err);
    };
}

  // ======= END ADDED SECTION =======


  function formatFileSize(bytes) {
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function handleFileSelect(file) {
    if (!file) return;

    if (file.type !== 'application/pdf') {
      alert('Please select a PDF file only.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert('File size must be less than 10MB.');
      return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);

    fileInfo.classList.remove('hidden');
    uploadBtn.disabled = false;
    dropZone.classList.add('highlight');
  }

  function resetForm() {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    uploadProgress.classList.add('hidden');
    successMessage.classList.add('hidden');
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Process Document';
    progressBar.style.width = '0%';
    progressPercent.textContent = '0%';
    dropZone.classList.remove('highlight');

    if (uploadController) {
      uploadController.abort();
      uploadController = null;
    }
  }

  dropZone.addEventListener('click', (e) => {
    if (e.target !== fileInput) {
      fileInput.click();
    }
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('highlight');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('highlight');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('highlight');
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;
  });

  fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
  });

  removeFileBtn.addEventListener('click', resetForm);
  cancelBtn.addEventListener('click', resetForm);

  // Override your existing form submit handler
  form.addEventListener('submit', async function(e) {
    e.preventDefault();

    const file = selectedFile;


    if (!file) {
      showFlashMessage('Please select a file first', true);
      return;
    }

    createLoadingExamCard(file.name);

    uploadProgress.classList.remove('hidden');
    setTimeout(() => {
      uploadProgress.classList.add('hidden');
      cancelBtn.click();
    }, 1500);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/upload-pdf', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (response.ok) {
        // Save jobId and connect websocket
        jobId = result.job_id || result.examId;
        if (jobId) {
          localStorage.setItem('jobId', jobId);
          connectWebSocket();
          showFlashMessage("Uploading Exam");
        }

        uploadProgress.classList.add('hidden');
        successMessage.classList.remove('hidden');
        resetForm();
        if (result.examId && result.examName) {
          console.log("Upload successful:", result);

          updateLoadingCardToSuccess(result.examId, result.examName);
        } else {
          removeLoadingCard();
          setTimeout(() => location.reload(), 1000);
        }

      } else {
        removeLoadingCard();
        showFlashMessage(result.detail || 'Upload failed', true);
        uploadProgress.classList.add('hidden');
      }
    } catch (error) {
      removeLoadingCard();
      showFlashMessage('Network error occurred', true);
      uploadProgress.classList.add('hidden');
    }
  });

  // Call restore on page load to resume any in-progress jobs
  restoreJobStatus();


  // Your existing card functions (unchanged)
  function createLoadingExamCard(filename) {
    const loadingCardId = 'loading-' + Date.now();
    currentLoadingCardId = loadingCardId;

    const loadingCard = document.createElement('div');
    loadingCard.id = loadingCardId;
    loadingCard.className = 'bg-white dark:bg-gray-800 p-5 rounded-xl shadow hover:shadow-lg transition border-2 border-blue-200 dark:border-green-600';

    loadingCard.innerHTML = `
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white break-words max-w-full">
          Processing Document
        </h3>
        <div class="loading-dots text-blue-600 dark:text-green-400">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">${filename}</p>
      <div class="mt-4 flex items-center justify-between">
        <span class="text-sm text-gray-400 dark:text-gray-500">Processing with AI...</span>
        <div class="text-xs bg-blue-100 dark:bg-green-900/30 text-blue-800 dark:text-green-300 px-3 py-1 rounded">
          In Progress
        </div>
      </div>
    `;

    const examsGrid = document.getElementById('exams-grid');
    examsGrid.insertBefore(loadingCard, examsGrid.firstChild);

    return loadingCardId;
  }

  function  updateLoadingCardToSuccess(examId, examName) {
    if (!currentLoadingCardId) return;

    const loadingCard = document.getElementById(currentLoadingCardId);
    if (loadingCard) {
      loadingCard.id = `exam-card-${examId}`;
      loadingCard.className = 'bg-white dark:bg-gray-800 p-5 rounded-xl shadow hover:shadow-lg transition flex flex-col justify-between min-h-[220px]';

      loadingCard.innerHTML = `
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white break-words max-w-full mb-4">
          ${examName}
        </h3>      
        <div class="mt-4 flex items-center justify-between">
         <a href="${URL}/exam/${examId}"  class="text-blue-600 dark:text-green-400 hover:underline text-sm">View PDF</a>

           <button  id="copy-btn" data-copy-url="${URL}/exam/${examId}"
                  class="text-xs bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white px-3 py-1 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition">
            Copy Link
          </button>
           <button id="delete-btn-${examId}" data-exam-id="${examId}" 
                class="text-xs bg-red-200 dark:bg-red-700 text-red-900 dark:text-white px-3 py-1 rounded hover:bg-red-300 dark:hover:bg-red-600 transition flex items-center justify-center">
          <svg class="w-6 h-6 text-gray-800 dark:text-white" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 18 20">
            <path d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z" clip-rule="evenodd" fill-rule="evenodd"></path>
          </svg>
        </button>
        </div>
      `;
    }
    currentLoadingCardId = null;
  }

  function removeLoadingCard() {
    if (currentLoadingCardId) {
      const loadingCard = document.getElementById(currentLoadingCardId);
      if (loadingCard) {
        loadingCard.remove();
      }
      currentLoadingCardId = null;
    }
  }

});
