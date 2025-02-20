document.documentElement.setAttribute("class", "dark");

const baseUrl = window.BACKEND_URL;
let isWebRTCActive = false;
let peerConnection;
let dataChannel;

function handleTrack(event) {
  const audioOutput = document.getElementById("audio-output");
  audioOutput.innerHTML = "";

  // Create container
  const audioContainer = document.createElement("div");
  audioContainer.className =
    "w-full max-w-2xl mx-auto p-4 rounded-lg border border-blue-400/30 bg-gradient-to-br from-blue-400/10 to-blue-400/5 backdrop-blur-sm transition-all duration-300";

  // Create flex container for icon and audio
  const flexContainer = document.createElement("div");
  flexContainer.className = "flex items-center justify-center gap-4";

  // Create icon container
  const iconContainer = document.createElement("div");
  iconContainer.className =
    "w-8 h-8 rounded-full bg-blue-400/20 flex items-center justify-center";
  iconContainer.innerHTML = `
    <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path>
    </svg>
  `;

  // Create audio element container
  const audioElementContainer = document.createElement("div");
  audioElementContainer.className = "w-3/4";

  // Create audio element
  const audioElement = document.createElement("audio");
  audioElement.srcObject = event.streams[0];
  audioElement.autoplay = true;
  audioElement.controls = true;
  audioElement.className = "w-full";
  audioElement.style.cssText = `
    height: 32px;
    border-radius: 8px;
    background: transparent;
  `;

  // Create status text
  const statusText = document.createElement("div");
  statusText.className = "mt-2 text-sm text-gray-400 text-center";
  statusText.textContent = "Voice Chat Active";

  // Assemble the elements
  audioElementContainer.appendChild(audioElement);
  flexContainer.appendChild(iconContainer);
  flexContainer.appendChild(audioElementContainer);
  audioContainer.appendChild(flexContainer);
  audioContainer.appendChild(statusText);
  audioOutput.appendChild(audioContainer);

  // Show the audio output
  audioOutput.classList.remove("hidden");
}

function createDataChannel() {
  dataChannel = peerConnection.createDataChannel("response");

  dataChannel.addEventListener("open", () => {
    console.log("Data channel opened");
    configureData();
  });

  let pendingUserTranscript = null;
  let pendingAssistantTranscript = null;

  dataChannel.addEventListener("message", async (ev) => {
    const msg = JSON.parse(ev.data);

    // Log user transcription
    if (msg.type === "conversation.item.input_audio_transcription.completed") {
      console.log("User transcript received:", msg);
      pendingUserTranscript = msg?.transcript || "";
    }

    // Log assistant transcription
    if (msg.type === "response.output_item.done") {
      console.log("Assistant transcript received:", msg);
      pendingAssistantTranscript = msg?.item?.content?.[0]?.transcript || "";
    }

    // Ensure user transcript appears first
    if (pendingUserTranscript && pendingAssistantTranscript) {
      finalizeTranscription(pendingUserTranscript, "user");
      finalizeTranscription(pendingAssistantTranscript, "assistant");

      // Clear stored values after displaying
      pendingUserTranscript = null;
      pendingAssistantTranscript = null;
    }

    // Handle function call
    if (msg.type === "response.function_call_arguments.done") {
      handleFunctionCall(msg);
    }
  });
}

async function handleFunctionCall(msg) {
  const result = await handleLocalFunction(msg);
  const event = {
    type: "conversation.item.create",
    item: {
      type: "function_call_output",
      call_id: msg.call_id,
      output: JSON.stringify(result),
    },
  };
  dataChannel.send(JSON.stringify(event));
}

async function handleLocalFunction(msg) {
  if (msg.name === "getPdfInfo") {
    return handleGetPdfInfo();
  }
  if (msg.name === "uploadPdf") {
    return handlePdfUpload(JSON.parse(msg.arguments));
  }
  return { error: "Function not found" };
}

async function handleGetPdfInfo() {
  try {
    const response = await fetch(`${baseUrl}/pdf-info`);
    return await response.json();
  } catch (error) {
    return { error: error.toString() };
  }
}

async function handlePdfUpload(args) {
  try {
    const formData = new FormData();
    formData.append("file", args.file);

    const response = await fetch(`${baseUrl}/upload-pdf`, {
      method: "POST",
      body: formData,
    });
    return await response.json();
  } catch (error) {
    return { error: error.toString() };
  }
}

function configureData() {
  const event = {
    type: "session.update",
    session: {
      modalities: ["text", "audio"],
      tools: [
        {
          type: "function",
          name: "uploadPdf",
          description: "Upload a PDF file to the server",
          parameters: {
            type: "object",
            properties: {
              file: { type: "object", description: "PDF file to upload" },
            },
            required: ["file"],
          },
        },
        {
          type: "function",
          name: "getPdfInfo",
          description: "Get information about current PDF",
          parameters: {},
        },
      ],
    },
  };
  dataChannel.send(JSON.stringify(event));
}

function toggleVoiceChat() {
  const button = document.getElementById("toggleWebRTCButton");

  if (isWebRTCActive) {
    // Stop WebRTC and show alert
    stopWebRTC();
    button.classList.remove("recording");
    document.getElementById("audio-output").innerHTML = "";

    // Create and show the "Voice Chat Off" alert
    const offAlert = createAlert(
      "Voice Chat Disabled",
      "Voice chat has been turned off",
      "success"
    );
    offAlert.classList.add("voice-chat-alert");
    document.body.appendChild(offAlert);

    // Remove alert after animation
    setTimeout(() => {
      offAlert.style.opacity = "0";
      offAlert.style.transform = "translateY(-10px)";
      setTimeout(() => offAlert.remove(), 300);
    }, 2000);
  } else {
    // Show processing alert while WebRTC starts
    const processingAlert = createProcessingAlert("Initializing voice chat...");
    processingAlert.classList.add("voice-chat-processing");
    document.body.appendChild(processingAlert);

    setTimeout(() => {
      processingAlert.style.opacity = "0";
      processingAlert.style.transform = "translateY(-10px)";
      setTimeout(() => processingAlert.remove(), 2000);
    }, 2000);

    try {
      // Start WebRTC
      startWebRTC();
      button.classList.add("recording");

      // Create and show the "Voice Chat On" alert
      const onAlert = createAlert(
        "Voice Chat Enabled",
        "Voice chat is now active. Start speaking to interact.",
        "success"
      );
      onAlert.classList.add("voice-chat-alert");

      // Remove processing alert and show success alert
      setTimeout(() => {
        const processingAlerts = document.querySelectorAll(
          ".voice-chat-processing"
        );
        processingAlerts.forEach((alert) => {
          alert.style.opacity = "0";
          alert.style.transform = "translateY(-10px)";
          setTimeout(() => alert.remove(), 300);
        });

        document.body.appendChild(onAlert);

        // Remove success alert after delay
        setTimeout(() => {
          onAlert.style.opacity = "0";
          onAlert.style.transform = "translateY(-10px)";
          setTimeout(() => onAlert.remove(), 300);
        }, 2000);
      }, 1000);
    } catch (error) {
      // Handle errors
      const errorAlert = createAlert(
        "Error",
        "Failed to initialize voice chat. Please check your microphone permissions.",
        "error"
      );
      document.body.appendChild(errorAlert);

      // Remove processing and error alerts
      const processingAlerts = document.querySelectorAll(
        ".voice-chat-processing"
      );
      processingAlerts.forEach((alert) => alert.remove());

      setTimeout(() => {
        errorAlert.style.opacity = "0";
        errorAlert.style.transform = "translateY(-10px)";
        setTimeout(() => errorAlert.remove(), 300);
      }, 2000);

      // Reset button state
      button.classList.remove("recording");
    }
  }
}

function startWebRTC() {
  if (isWebRTCActive) return;

  try {
    peerConnection = new RTCPeerConnection();
    peerConnection.ontrack = handleTrack;
    createDataChannel();

    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        stream
          .getTracks()
          .forEach((track) =>
            peerConnection.addTransceiver(track, { direction: "sendrecv" })
          );

        peerConnection
          .createOffer()
          .then((offer) => {
            peerConnection.setLocalDescription(offer);

            fetch(`${baseUrl}/rtc-connect`, {
              method: "POST",
              body: offer.sdp,
              headers: { "Content-Type": "application/sdp" },
            })
              .then((r) => r.text())
              .then((answer) => {
                peerConnection.setRemoteDescription({
                  sdp: answer,
                  type: "answer",
                });
                isWebRTCActive = true;
              })
              .catch((error) => {
                throw new Error("Failed to connect to server");
              });
          })
          .catch((error) => {
            throw new Error("Failed to create offer");
          });
      })
      .catch((error) => {
        throw new Error("Microphone access denied");
      });
  } catch (error) {
    isWebRTCActive = false;
    throw error;
  }
}

function stopWebRTC() {
  if (!isWebRTCActive) return;

  peerConnection.getReceivers().forEach((receiver) => receiver.track.stop());

  if (dataChannel) dataChannel.close();
  if (peerConnection) peerConnection.close();

  peerConnection = null;
  dataChannel = null;
  isWebRTCActive = false;
}

function finalizeTranscription(text, role) {
  const transcriptElementId =
    role === "user" ? "live-transcript-user" : "live-transcript-assistant";
  const transcriptElement = document.getElementById(transcriptElementId);

  if (transcriptElement) {
    transcriptElement.remove(); // Remove temporary transcript
  }

  appendChatMessage(text, role); // Save as a final message
}

// Chat Functions
function appendChatMessage(content, role) {
  const messages = document.getElementById("chat-messages");
  if (!messages) return;

  const messageClass =
    role === "user"
      ? "border-yellow-500/30 from-yellow-500/10 to-yellow-500/5"
      : "border-green-500/30 from-green-500/10 to-green-500/5";

  messages.innerHTML += `
    <div class="p-4 border ${messageClass} rounded-lg bg-gradient-to-br mb-4 transition-all duration-300">
      <div class="flex items-start justify-between">
        <div class="flex-grow">
          <p class="font-semibold ${
            role === "user" ? "text-yellow-500" : "text-green-500"
          }">
            ${role === "user" ? "You" : "Assistant"}:
          </p>
          <p class="ms-2">${content}</p>
        </div>
      </div>
    </div>
  `;

  messages.scrollTop = messages.scrollHeight;
}

async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  appendChatMessage(message, "user");
  input.value = "";

  try {
    const response = await fetch(`${baseUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: message }),
    });

    const data = await response.json();
    if (data.response) {
      appendChatMessage(data.response, "assistant");
    }
  } catch (error) {
    appendChatMessage(`Error: ${error.message}`, "error");
  }
}

async function clearChat() {
  try {
    const response = await fetch(`${baseUrl}/clear-chat`, {
      method: "POST",
    });

    if (response.ok) {
      document.getElementById("chat-messages").innerHTML = "";
      document.getElementById("audio-output").innerHTML = "";
      document.getElementById("chat-input").value = "";
      // Add a success message
      const messages = document.getElementById("chat-messages");
      messages.innerHTML = `
          <div class="rounded-lg items-center p-4 border border-green-500/30 rounded-lg bg-gradient-to-br from-green-500/10 to-green-500/5 hover:from-green-500/20 hover:to-green-500/10 hover:border-green-500/50">
              <p class="text-green-500">Chat history cleared successfully!</p>
          </div>
      `;
      // Remove success message after 2 seconds
      setTimeout(() => {
        messages.innerHTML = "";
      }, 2000);
    } else {
      const data = await response.json();
      const messages = document.getElementById("chat-messages");
      messages.innerHTML += `
          <div class="rounded-lg items-center p-4 border border-red-500/30 rounded-lg bg-gradient-to-br from-red-500/10 to-red-500/5 hover:from-red-500/20 hover:to-red-500/10 hover:border-red-500/50">
              <p class="text-red-500">Error clearing chat: ${data.error}</p>
          </div>
      `;
    }
  } catch (error) {
    console.error("Error clearing chat:", error);
    const messages = document.getElementById("chat-messages");
    messages.innerHTML += `
        <div class="rounded-lg items-center p-4 border border-red-500/30 rounded-lg bg-gradient-to-br from-red-500/10 to-red-500/5 hover:from-red-500/20 hover:to-red-500/10 hover:border-red-500/50">
            <p class="text-red-500">Error clearing chat: ${error.message}</p>
        </div>
    `;
  }
}

function copyToClipboard(text, tooltipId) {
  navigator.clipboard.writeText(text).then(() => {
    const tooltip = document.getElementById(tooltipId);
    tooltip.textContent = "Copied!";
    tooltip.classList.add("copied");
    setTimeout(() => {
      tooltip.textContent = "Copy";
      tooltip.classList.remove("copied");
    }, 1000);
  });
}

function showLoadingButton(buttonId, loadingText) {
  const button = document.getElementById(buttonId);
  if (button) {
    button.disabled = true;
    button.classList.add("loading");
    button.innerHTML = `
      <div class="flex items-center justify-center">
        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        ${loadingText}
      </div>
    `;
  }
}

function resetButton(buttonId, originalText) {
  const button = document.getElementById(buttonId);
  if (button) {
    button.disabled = false;
    button.classList.remove("loading");
    button.innerHTML = originalText;
  }
}

// Container visibility functions
function hideUploadContainer(containerId) {
  const container = document.getElementById(containerId);
  if (container) {
    container.style.display = "none";
  }
}

function showUploadContainer(containerId) {
  const container = document.getElementById(containerId);
  if (container) {
    container.style.display = "block";
  }
}

// File upload event listeners
document
  .getElementById("file-upload-jd")
  ?.addEventListener("change", function () {
    showLoadingButton("upload-jd-btn", "Analyzing JD...");
    hideUploadContainer("jd-upload-container");

    const alertDiv = createProcessingAlert("Analyzing Job Description... Please wait.");
    document.body.appendChild(alertDiv);

    setTimeout(() => {
      alertDiv.remove();
    }, 1500);
  });

document
  .getElementById("file-upload-cvs")
  ?.addEventListener("change", function () {
    showLoadingButton("upload-cvs-btn", "Processing CVs...");
    hideUploadContainer("cv-upload-container");

    const alertDiv = createProcessingAlert("Processing CVs... Please wait");
    document.body.appendChild(alertDiv);

    setTimeout(() => {
      alertDiv.remove();
    }, 1500);
  });

document.getElementById("compare-btn")?.addEventListener("click", function () {
  const alertDiv = createProcessingAlert("Analyzing and comparing CVs...");
  alertDiv.classList.add("processing-alert"); // Add class for identification
  document.body.appendChild(alertDiv);

  const compareBtn = this;
  const compareText = compareBtn.querySelector(".compare-btn-text");
  const compareLoading = compareBtn.querySelector(".compare-btn-loading");

  compareBtn.disabled = true;
  compareText.classList.add("hidden");
  compareLoading.classList.remove("hidden");

  fetch(`${baseUrl}/compare-cvs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Comparison failed");
      }
      return response.json();
    })
    .then((data) => {
      // Show success alert
      const successAlert = createAlert(
        "Success",
        "CV comparison completed successfully",
        "success"
      );
      document.body.appendChild(successAlert);

      setTimeout(() => {
        successAlert.style.opacity = "0";
        successAlert.style.transform = "translateY(-10px)";
        setTimeout(() => successAlert.remove(), 300);
      }, 2000);
    })
    .finally(() => {
      compareBtn.disabled = false;
      compareText.classList.remove("hidden");
      compareLoading.classList.add("hidden");

      const processingAlerts = document.querySelectorAll(".processing-alert");
      processingAlerts.forEach((alert) => {
        alert.style.opacity = "0";
        alert.style.transform = "translateY(-10px)";
        setTimeout(() => alert.remove(), 300);
      });
    });
});
// Process button event listener
document.addEventListener('DOMContentLoaded', function() {
  const processBtn = document.getElementById("process-btn-pdf");
  
  if (processBtn) {
    processBtn.addEventListener("click", function(e) {
      e.preventDefault(); // Prevent default form submission if within a form
      
      // Create and show processing alert
      const alertDiv = createProcessingAlert("Processing CV... Please wait");
      alertDiv.classList.add("processing-alert");
      document.body.appendChild(alertDiv);

      // Disable button and show loading state
      const processText = this.querySelector(".process-btn-text");
      const processLoading = this.querySelector(".process-btn-loading");
      
      if (processText && processLoading) {
        this.disabled = true;
        processText.classList.add("hidden");
        processLoading.classList.remove("hidden");
      }

      // Make the API call
      fetch(`${baseUrl}/process-pdf`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Processing failed");
          }
          return response.json();
        })
        .then((data) => {
          // Show success alert
          const successAlert = createAlert(
            "Success",
            "PDF processing completed successfully",
            "success"
          );
          document.body.appendChild(successAlert);

          // Remove success alert after delay
          setTimeout(() => {
            successAlert.style.opacity = "0";
            successAlert.style.transform = "translateY(-10px)";
            setTimeout(() => successAlert.remove(), 300);
          }, 2000);
        })
        .catch((error) => {
          // Show error alert
          const errorAlert = createAlert(
            "Error",
            error.message || "Failed to process PDF",
            "error"
          );
          document.body.appendChild(errorAlert);

          // Remove error alert after delay
          setTimeout(() => {
            errorAlert.style.opacity = "0";
            errorAlert.style.transform = "translateY(-10px)";
            setTimeout(() => errorAlert.remove(), 300);
          }, 2000);
        })
        .finally(() => {
          // Re-enable button and restore original state
          if (processText && processLoading) {
            this.disabled = false;
            processText.classList.remove("hidden");
            processLoading.classList.add("hidden");
          }

          // Remove processing alert
          const processingAlerts = document.querySelectorAll(".processing-alert");
          processingAlerts.forEach((alert) => {
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-10px)";
            setTimeout(() => alert.remove(), 300);
          });
        });
    });
  }
});


function createProcessingAlert(message) {
  const alertDiv = document.createElement("div");
  alertDiv.className =
    "fixed top-4 right-4 p-4 rounded-lg bg-blue-400/10 border border-blue-400/30 text-white transition-all duration-300 z-50";
  alertDiv.innerHTML = `
        <div class="flex items-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            ${message}
        </div>
    `;
  return alertDiv;
}

async function clearMatching() {
  try {
    const response = await fetch(`${baseUrl}/clear-matching`, {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error("Clear failed");
    }

    showUploadContainer("jd-upload-container");
    showUploadContainer("cv-upload-container");

    document.getElementById("file-upload-jd").value = "";
    document.getElementById("file-upload-cvs").value = "";
    document.getElementById("matching-results").innerHTML = "";
  } catch (error) {
    console.error("Error clearing documents:", error);
  }
}

function createErrorAlert(message) {
  const alertDiv = document.createElement("div");
  alertDiv.className =
    "fixed top-4 right-4 p-4 rounded-lg bg-red-400/10 border border-red-400/30 text-white animate-fade-in";
  alertDiv.innerHTML = `
    <div class="flex items-center">
      <svg class="w-5 h-5 text-red-400 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
      </svg>
      ${message}
    </div>
  `;
  return alertDiv;
}

function createAlert(title, message, type) {
  const alertDiv = document.createElement("div");
  const bgColor = type === "success" ? "bg-green-400/10" : "bg-red-400/10";
  const borderColor =
    type === "success" ? "border-green-400/30" : "border-red-400/30";
  const textColor = type === "success" ? "text-green-400" : "text-red-400";

  alertDiv.className = `fixed top-4 right-4 p-4 rounded-lg ${bgColor} border ${borderColor} transition-all duration-300 z-50`;
  alertDiv.innerHTML = `
        <div class="flex items-center">
            <svg class="w-5 h-5 ${textColor} mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                ${
                  type === "success"
                    ? '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>'
                    : '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>'
                }
            </svg>
            <div>
                <div class="font-semibold ${textColor}">${title}</div>
                <div class="text-white text-sm">${message}</div>
            </div>
        </div>
    `;

  return alertDiv;
}

function toggleContent(header) {
  const content = header.nextElementSibling;
  const chevron = header.querySelector(".lucide-chevron-up");

  if (content.classList.contains("block")) {
    content.classList.remove("block");
    content.classList.add("hidden");
    chevron.style.transform = "rotate(180deg)";
  } else {
    content.classList.remove("hidden");
    content.classList.add("block");
    chevron.style.transform = "rotate(0deg)";
  }
}
