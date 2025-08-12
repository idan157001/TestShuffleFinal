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

  let selectedFile = null;
  let uploadController = null;

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
  });

  fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
  });

  removeFileBtn.addEventListener('click', resetForm);
  cancelBtn.addEventListener('click', resetForm);









 // Handle form submission for PDF upload
  document.getElementById('pdf-upload-form').addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const fileInput = document.getElementById('pdf-upload');
      const file = fileInput.files[0];
      
      if (!file) {
        showFlashMessage('Please select a file first', true);
        return;
      }

      // Create loading card immediately
      createLoadingExamCard(file.name);
      
      // Show upload progress
      document.getElementById('upload-progress').classList.remove('hidden');
      setTimeout(() => {
         document.getElementById('upload-progress').classList.add('hidden');
        document.getElementById("cancel-btn").click()},1500);
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/upload-pdf', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();
        console.log(result);
        if (response.ok) {
          // Hide upload progress
          document.getElementById('upload-progress').classList.add('hidden');

          // Show success message
          const successMessage = document.getElementById('success-message');
          if (successMessage) {
            successMessage.classList.remove('hidden');
          }
          
          // Reset form
          fileInput.value = '';
          document.getElementById('file-info').classList.add('hidden');
          document.getElementById('upload-btn').disabled = true;

          // Note: You'll need to get the actual exam data from your backend
          // This is a placeholder - replace with actual data from response
          if (result.examId && result.examName) {
            updateLoadingCardToSuccess(result.examId, result.examName);
          } else {
            // If no exam data returned, remove loading card and reload page
            removeLoadingCard();
            setTimeout(() => location.reload(), 1000);
          }
          
        } else {
          removeLoadingCard();
          showFlashMessage(result.detail || 'Upload failed', true);
          document.getElementById('upload-progress').classList.add('hidden');
        }
      } catch (error) {
        removeLoadingCard();
        showFlashMessage('Network error occurred', true);
        document.getElementById('upload-progress').classList.add('hidden');
      }
    });








// handle card loading and success updates for exam processing
  let currentLoadingCardId = null;

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

    function updateLoadingCardToSuccess(examId, examName) {
      if (!currentLoadingCardId) return;
      
      const loadingCard = document.getElementById(currentLoadingCardId);
      if (loadingCard) {

        loadingCard.id = `exam-${examId}`;
        loadingCard.className = 'bg-white dark:bg-gray-800 p-5 rounded-xl shadow hover:shadow-lg transition';
        
        loadingCard.innerHTML = `
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white break-words max-w-full">
            ${examName}
          </h3>      
          <div class="mt-4 flex items-center justify-between">
            <a href="http://127.0.0.1:8000/exam/${examId}" class="text-blue-600 dark:text-green-400 hover:underline text-sm">View PDF</a>
            
            <button onclick="copyToClipboard('http://127.0.0.1:8000/exam/${examId}')" 
                    class="text-xs bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white px-3 py-1 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition">
              Copy Link
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
