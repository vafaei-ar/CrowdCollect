const preview = document.querySelector("#preview");
const placeholder = document.querySelector("#camera-placeholder");
const statusPill = document.querySelector("#status-pill");
const recordingDot = document.querySelector("#recording-dot");
const stepLabel = document.querySelector("#step-label");
const promptText = document.querySelector("#prompt-text");
const promptHelp = document.querySelector("#prompt-help");
const movementDemo = document.querySelector("#movement-demo");
const demoTitle = document.querySelector("#demo-title");
const progressBar = document.querySelector("#progress-bar");
const message = document.querySelector("#message");
const cameraButton = document.querySelector("#camera-button");
const startButton = document.querySelector("#start-button");
const nextButton = document.querySelector("#next-button");
const finishButton = document.querySelector("#finish-button");
const retryButton = document.querySelector("#retry-button");
const tasks = JSON.parse(document.querySelector("#tasks-data").textContent);

let stream;
let recorder;
let chunks = [];
let taskIndex = 0;
let autoStopTimer;

function supportedMimeType() {
  const choices = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm", "video/mp4"];
  return choices.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function showError(text) {
  message.textContent = text;
  message.classList.add("error");
}

function demoForTask(task) {
  const text = task.toLowerCase();
  if (text.includes("smile")) return ["smile", "Animated example of a smile"];
  if (text.includes("fist") || text.includes("close") || text.includes("clench")) {
    return ["fist", "Animated example of closing an open hand into a fist"];
  }
  if (text.includes("palm") || text.includes("finger") || text.includes("open hand")) {
    return ["palm", "Animated example of showing an open palm"];
  }
  if (text.includes("raise") && (text.includes("arm") || text.includes("hand"))) {
    return ["arm", "Animated example of raising an arm"];
  }
  return ["generic", "Animated person demonstrating the requested movement"];
}

function setDemo(name, label) {
  movementDemo.className = `movement-demo demo-${name}`;
  demoTitle.textContent = label;
}

function updateTask() {
  stepLabel.textContent = `Movement ${taskIndex + 1} of ${tasks.length}`;
  promptText.textContent = tasks[taskIndex];
  promptHelp.textContent = "Hold the movement briefly, then continue when ready.";
  progressBar.style.width = `${((taskIndex + 1) / tasks.length) * 100}%`;
  nextButton.hidden = taskIndex === tasks.length - 1;
  finishButton.hidden = taskIndex !== tasks.length - 1;
  setDemo(...demoForTask(tasks[taskIndex]));
}

async function enableCamera() {
  message.textContent = "";
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    showError("This browser cannot record video. Try a current version of Chrome, Edge, Firefox, or Safari.");
    return;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    preview.srcObject = stream;
    placeholder.hidden = true;
    cameraButton.hidden = true;
    startButton.hidden = false;
    statusPill.textContent = "Camera ready";
    statusPill.classList.add("ready");
    promptText.textContent = "When you are ready, start the guided recording.";
    setDemo("position", "Position yourself in the camera frame");
  } catch (error) {
    showError("Camera access was not granted. Allow camera access in your browser and try again.");
  }
}

function startRecording() {
  chunks = [];
  taskIndex = 0;
  message.textContent = "";
  message.classList.remove("error");
  const mimeType = supportedMimeType();
  recorder = mimeType ? new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 1_200_000 }) : new MediaRecorder(stream);
  recorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  });
  recorder.start(1000);
  startButton.hidden = true;
  retryButton.hidden = true;
  recordingDot.hidden = false;
  statusPill.textContent = "Recording";
  statusPill.classList.add("recording");
  updateTask();
  autoStopTimer = window.setTimeout(() => finishRecording(true), 90_000);
}

function stopRecorder() {
  return new Promise((resolve) => {
    recorder.addEventListener("stop", resolve, { once: true });
    recorder.stop();
  });
}

async function finishRecording(automatic = false) {
  nextButton.hidden = true;
  finishButton.hidden = true;
  clearTimeout(autoStopTimer);
  promptText.textContent = "Preparing your recording…";
  promptHelp.textContent = automatic ? "The 90-second recording limit was reached." : "Please keep this page open.";
  setDemo("generic", "Recording is being prepared for upload");
  recordingDot.hidden = true;
  statusPill.textContent = "Uploading";
  await stopRecorder();
  await uploadRecording();
}

async function uploadRecording() {
  const type = recorder.mimeType || "video/webm";
  const extension = type.includes("mp4") ? "mp4" : "webm";
  const blob = new Blob(chunks, { type });
  if (blob.size > 45 * 1024 * 1024) {
    showError("This recording is too large. Please record a shorter session.");
    resetForRetry();
    return;
  }
  const body = new FormData();
  body.append("video", blob, `movement-session.${extension}`);
  try {
    const response = await fetch("/upload", { method: "POST", body });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Upload failed.");
    statusPill.textContent = "Sent";
    statusPill.className = "status-pill sent";
    promptText.textContent = "Thank you — your recording was sent.";
    promptHelp.textContent = "You may now close this page.";
    setDemo("generic", "Movement session complete");
    progressBar.style.width = "100%";
    stream.getTracks().forEach((track) => track.stop());
  } catch (error) {
    showError(error.message || "Upload failed. Please try again.");
    resetForRetry();
  }
}

function resetForRetry() {
  statusPill.textContent = "Camera ready";
  statusPill.className = "status-pill ready";
  retryButton.hidden = false;
  promptText.textContent = "Your recording has not been sent.";
  promptHelp.textContent = "You can record the sequence again.";
  setDemo("position", "Position yourself to record the session again");
}

cameraButton.addEventListener("click", enableCamera);
startButton.addEventListener("click", startRecording);
retryButton.addEventListener("click", startRecording);
nextButton.addEventListener("click", () => {
  taskIndex += 1;
  updateTask();
});
finishButton.addEventListener("click", () => finishRecording(false));
window.addEventListener("beforeunload", () => stream?.getTracks().forEach((track) => track.stop()));
