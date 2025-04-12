document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const uploadButton = document.querySelector(".upload-button");
  const submitButton = form.querySelector('button[type="submit"]');
  const resultsSection = document.getElementById("results-section");
  const markdownContent = document.getElementById("markdown-content");
  const structuredContent = document.getElementById("structured-content");
  const errorMessage = document.getElementById("error-message");
  const loading = document.getElementById("loading");
  const selectedFile = document.getElementById("selected-file");
  const uploadSection = document.querySelector(".upload-section");
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");
  const continueButton = document.getElementById("continue-button");
  const documentTypeSelect = document.getElementById("document-type");

  // Initialize markdown-it
  const md = window.markdownit();

  // Initially disable continue button
  if (continueButton) {
    continueButton.disabled = true;
  }

  // Handle upload button click
  if (uploadButton) {
    uploadButton.addEventListener("click", () => {
      fileInput.click();
    });
  }

  // Handle file input change
  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) {
      selectedFile.textContent = `Selected: ${file.name}`;
      selectedFile.style.display = "block";
      if (continueButton) {
        continueButton.disabled = false;
      }
      uploadSection.classList.add("has-file");
    } else {
      selectedFile.style.display = "none";
      if (continueButton) {
        continueButton.disabled = true;
      }
      uploadSection.classList.remove("has-file");
    }
  });

  // Handle drag and drop
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    uploadSection.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ["dragenter", "dragover"].forEach((eventName) => {
    uploadSection.addEventListener(eventName, highlight, false);
  });

  ["dragleave", "drop"].forEach((eventName) => {
    uploadSection.addEventListener(eventName, unhighlight, false);
  });

  function highlight() {
    uploadSection.classList.add("drag-active");
  }

  function unhighlight() {
    uploadSection.classList.remove("drag-active");
  }

  uploadSection.addEventListener("drop", handleDrop, false);

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const file = dt.files[0];

    if (file) {
      fileInput.files = dt.files;
      selectedFile.textContent = `Selected: ${file.name}`;
      selectedFile.style.display = "block";
      if (continueButton) {
        continueButton.disabled = false;
      }
      uploadSection.classList.add("has-file");
    }
  }

  // Handle continue button click
  if (continueButton) {
    continueButton.addEventListener("click", async () => {
      const file = fileInput.files[0];
      if (!file) {
        if (errorMessage) {
          errorMessage.textContent = "Please select a file to upload";
          errorMessage.style.display = "block";
        }
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_type", documentTypeSelect.value);

      continueButton.disabled = true;
      continueButton.textContent = "Processing...";

      try {
        const response = await fetch("/upload", {
          method: "POST",
          body: formData,
        });

        const data = await response.json();

        if (data.success) {
          // Store the data in localStorage
          localStorage.setItem(
            "documentData",
            JSON.stringify({
              id: data.id,
              markdown: data.markdown,
              chunks: data.chunks,
              document_type: documentTypeSelect.value,
              previewUrl: data.previewUrl,
            })
          );

          // Redirect to configure page
          window.location.href = `/configure?id=${data.id}`;
        } else {
          throw new Error(data.error || "Failed to process document");
        }
      } catch (error) {
        console.error("Upload error:", error);
        if (errorMessage) {
          errorMessage.textContent =
            error.message || "An error occurred while uploading the file";
          errorMessage.style.display = "block";
        }
        continueButton.disabled = false;
        continueButton.textContent = "Continue to Configure Fields";
      }
    });
  }

  // Handle document type change
  if (documentTypeSelect) {
    documentTypeSelect.addEventListener("change", () => {
      // You can add any specific logic for document type changes here
    });
  }

  // Handle tab switching
  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.getAttribute("data-target");

      // Update active states
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      tabContents.forEach((content) => content.classList.remove("active"));

      button.classList.add("active");
      document.getElementById(targetId).classList.add("active");
    });
  });

  // Handle file upload
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) {
      showError("Please select a file to upload");
      return;
    }

    // Show loading state
    loading.classList.add("visible");
    errorMessage.style.display = "none";
    resultsSection.classList.remove("visible");
    submitButton.disabled = true;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentTypeSelect.value);

    try {
      // Start the document processing
      const response = await fetch("/process", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.task_id) {
        // Start polling for task status
        await pollTaskStatus(data.task_id);
      } else {
        throw new Error("No task ID received from server");
      }
    } catch (error) {
      showError("An error occurred while uploading the file");
      console.error("Upload error:", error);
    } finally {
      loading.classList.remove("visible");
      submitButton.disabled = !fileInput.files.length;
    }
  });

  async function pollTaskStatus(taskId) {
    const maxAttempts = 60; // Maximum number of polling attempts (5 minutes with 5-second intervals)
    const interval = 5000; // Poll every 5 seconds
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await fetch(`/task/${taskId}`);
        const data = await response.json();

        switch (data.status) {
          case "completed":
            // Display results
            markdownContent.textContent = data.result.markdown;
            structuredContent.textContent = JSON.stringify(
              data.result,
              null,
              2
            );
            resultsSection.classList.add("visible");

            // Store the data in localStorage
            localStorage.setItem(
              "documentData",
              JSON.stringify({
                id: taskId,
                markdown: data.result.markdown,
                document_type: documentTypeSelect.value,
              })
            );

            // Activate first tab
            tabButtons[0].click();

            // Reset file input
            fileInput.value = "";
            selectedFile.style.display = "none";

            // Handle successful upload
            window.location.href = "/configure?id=" + taskId;
            return;

          case "failed":
            showError(data.error || "Failed to process document");
            return;

          case "processing":
            // Continue polling
            if (attempts < maxAttempts) {
              attempts++;
              setTimeout(poll, interval);
            } else {
              showError("Processing timeout. Please try again.");
            }
            break;

          case "pending":
            // Continue polling
            if (attempts < maxAttempts) {
              attempts++;
              setTimeout(poll, interval);
            } else {
              showError("Processing timeout. Please try again.");
            }
            break;
        }
      } catch (error) {
        console.error("Polling error:", error);
        showError("Error checking task status");
      }
    };

    // Start polling
    await poll();
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = "block";
  }
});
