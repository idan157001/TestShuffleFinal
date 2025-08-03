document.addEventListener("DOMContentLoaded", () => {
  const examsGrid = document.getElementById('exams-grid');

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
      .then(() => {
        showFlashMessage("Link copied to clipboard!");
      })
      .catch(err => {
        showFlashMessage("Failed to copy: " + err, true);
      });
  }

  function showFlashMessage(message, isError = false) {
    const flash = document.getElementById("flash-message");
    flash.textContent = message;

    flash.classList.remove("bg-green-500", "bg-red-500");
    flash.classList.add(isError ? "bg-red-500" : "bg-green-500");

    flash.classList.remove("hidden", "opacity-0");
    flash.classList.add("opacity-100");

    setTimeout(() => {
      flash.classList.remove("opacity-100");
      flash.classList.add("opacity-0");

      setTimeout(() => {
        flash.classList.add("hidden");
      }, 300);
    }, 2000);
  }

  const deleteModal = document.getElementById('delete-modal');
  const modalExamName = document.getElementById('modal-exam-name');
  const cancelBtn = document.getElementById('cancel-delete');
  const confirmBtn = document.getElementById('confirm-delete');

  let selectedExamId = null;

  // Make sure examsGrid exists before adding listener
  if (examsGrid) {
    examsGrid.addEventListener('click', (event) => {
      const target = event.target;
      if (target.tagName === 'BUTTON' && target.id.startsWith('delete-btn-')) {
        selectedExamId = target.dataset.examId;
        modalExamName.textContent = target.dataset.examName;
        deleteModal.classList.remove('hidden');
      }
    });
  } else {
    console.warn('examsGrid element not found!');
  }

  cancelBtn.addEventListener('click', () => {
    selectedExamId = null;
    deleteModal.classList.add('hidden');
  });

  confirmBtn.addEventListener('click', async () => {
  if (!selectedExamId) return;

  try {
    const response = await fetch(`/delete_exam/${selectedExamId}`, {
      method: 'DELETE',
    });

    if (response.ok) {
      // Remove the card from DOM
      const card = document.getElementById(`exam-card-${selectedExamId}`);
      if (card) card.remove();

      // Hide modal and reset
      deleteModal.classList.add('hidden');
      selectedExamId = null;

      showFlashMessage('Exam deleted successfully.');
    } else {
      // If backend returns error status
      showFlashMessage('Failed to delete exam.', true);
    }
  } catch (error) {
    // Network or other errors
    showFlashMessage('Error deleting exam.', true);
    console.error('Delete exam error:', error);
  }
});

  window.copyToClipboard = copyToClipboard;
  window.showFlashMessage = showFlashMessage; // Expose to global scope
});
