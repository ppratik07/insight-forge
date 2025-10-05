// Application State
let currentChartType = "auto";
let currentChartMode = "single"; // 'single' or 'multi'
let currentData = null;
let isProcessing = false;
let uploadedFile = null;
let uploadedPdf = null; // New: For PDF
let pdfSessionId = null; // New: Store session_id from PDF upload

// DOM Elements
const homePage = document.getElementById("homePage");
const resultsPage = document.getElementById("resultsPage");
const loadingOverlay = document.getElementById("loadingOverlay");
const loadingText = document.getElementById("loadingText");

// Home page elements
const textInput = document.getElementById("textInput");
const fileInput = document.getElementById("fileInput");
const uploadArea = document.getElementById("uploadArea");
const uploadedFileDisplay = document.getElementById("uploadedFile");
const clearTextBtn = document.getElementById("clearTextBtn");
const analyzeTextBtn = document.getElementById("analyzeTextBtn");
const analyzeFileBtn = document.getElementById("analyzeFileBtn");
const removeFileBtn = document.getElementById("removeFileBtn");
const chartTypeButtons = document.querySelectorAll(".chart-type-btn");
const chartModeButtons = document.querySelectorAll(".chart-mode-btn");

// New PDF elements
const pdfInput = document.getElementById("pdfInput");
const pdfUploadArea = document.getElementById("pdfUploadArea");
const uploadedPdfDisplay = document.getElementById("uploadedPdf");
const analyzePdfBtn = document.getElementById("analyzePdfBtn");
const removePdfBtn = document.getElementById("removePdfBtn");
const extractedChartsContainer = document.getElementById(
  "extractedChartsContainer"
);
const pdfQuerySection = document.getElementById("pdfQuerySection");
const pdfQueryInput = document.getElementById("pdfQueryInput");
const submitPdfQueryBtn = document.getElementById("submitPdfQueryBtn");
const pdfQueryResponse = document.getElementById("pdfQueryResponse");

// Results page elements
const backToHomeBtn = document.getElementById("backToHomeBtn");
const downloadAllChartsBtn = document.getElementById("downloadAllChartsBtn");
const loadingState = document.getElementById("loadingState");
const chartsContainer = document.getElementById("chartsContainer");

// Chart.js Configuration
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = "#64748b";

// Data Labels Plugin for Chart.js
const dataLabelsPlugin = {
  id: "dataLabels",
  afterDatasetsDraw: function (chart) {
    const chartType = chart.config.type;
    const ctx = chart.ctx;
    const datasets = chart.data.datasets;

    datasets.forEach((dataset, datasetIndex) => {
      const meta = chart.getDatasetMeta(datasetIndex);
      if (!meta.hidden) {
        meta.data.forEach((element, index) => {
          const value = dataset.data[index];
          const total = dataset.data.reduce((sum, val) => sum + val, 0);

          let text = "";
          if (chartType === "pie" || chartType === "doughnut") {
            const percentage = ((value / total) * 100).toFixed(1);
            text = `${percentage}%`;
          } else if (chartType === "bar") {
            text = value.toString();
          } else if (chartType === "line") {
            text = value.toString();
          }

          if (text) {
            ctx.font = "bold 14px Arial";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";

            let x, y;
            if (chartType === "pie" || chartType === "doughnut") {
              // For pie charts, position text in center of slice with white text and shadow
              const centerPoint = element.getCenterPoint();
              x = centerPoint.x;
              y = centerPoint.y;

              // White text with shadow for pie charts (over colored backgrounds)
              ctx.fillStyle = "#ffffff";
              ctx.shadowColor = "rgba(0, 0, 0, 0.5)";
              ctx.shadowBlur = 3;
              ctx.shadowOffsetX = 1;
              ctx.shadowOffsetY = 1;
            } else if (chartType === "bar") {
              // For bar charts, position text at top of bar
              x = element.x;
              y = element.y - 10;

              // Dark text with white outline for visibility over white background
              ctx.strokeStyle = "#ffffff";
              ctx.lineWidth = 3;
              ctx.strokeText(text, x, y);
              ctx.fillStyle = "#1f2937";
            } else if (chartType === "line") {
              // For line charts, position text above point
              x = element.x;
              y = element.y - 15;

              // Dark text with white outline for visibility over white background
              ctx.strokeStyle = "#ffffff";
              ctx.lineWidth = 3;
              ctx.strokeText(text, x, y);
              ctx.fillStyle = "#1f2937";
            }

            // Draw the text
            ctx.fillText(text, x, y);

            // Reset shadow and stroke settings
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;
            ctx.strokeStyle = "transparent";
            ctx.lineWidth = 1;
          }
        });
      }
    });
  },
};

// Register the plugin with Chart.js
Chart.register(dataLabelsPlugin);

// Chart Colors
const CHART_COLORS = {
  primary: "#2563eb",
  secondary: "#10b981",
  tertiary: "#f59e0b",
  quaternary: "#a855f7",
  quinary: "#ef4444",
  senary: "#06b6d4",
  septenary: "#84cc16",
  octonary: "#f97316",
};

// API Configuration
const API_BASE_URL = window.location.origin;

// Utility Functions
function showLoading(text = "Processing...") {
  loadingText.textContent = text;
  loadingOverlay.style.display = "flex";
}

function hideLoading() {
  loadingOverlay.style.display = "none";
}

function showHomePage() {
  homePage.style.display = "block";
  resultsPage.style.display = "none";
}

function showResultsPage(showPdfSection = false) {
  homePage.style.display = "none";
  resultsPage.style.display = "block";
  loadingState.style.display = "block";
  chartsContainer.style.display = "none";
  extractedChartsContainer.style.display = "none";
  pdfQuerySection.style.display = showPdfSection ? "block" : "none"; // New: Toggle PDF query section
}

function formatDataForChart(chartData, chartType) {
  console.log("Raw chartData received:", chartData); // DEBUG: Check what's coming from backend/LLM

  // If chartData already has Chart.js format (data.labels and data.datasets), use it directly
  if (
    chartData &&
    chartData.data &&
    chartData.data.labels &&
    chartData.data.datasets
  ) {
    console.log("Using pre-formatted Chart.js data");
    return chartData.data;
  }

  // Handle legacy dataPoints structure
  let dataPoints = [];

  if (chartData && chartData.dataPoints) {
    dataPoints = chartData.dataPoints;
  } else if (chartData && Array.isArray(chartData)) {
    dataPoints = chartData;
  } else {
    console.warn("Unexpected data format received:", chartData);
    // Fallback data for demonstration
    dataPoints = [
      { label: "Data 1", value: 30 },
      { label: "Data 2", value: 45 },
      { label: "Data 3", value: 25 },
    ];
  }

  // FIXED: Robust label extraction with inference and fallbacks
  const labels = dataPoints.map((point, i) => {
    let label =
      point.label || point.name || point.category || `Category ${i + 1}`;
    // Infer from context if still empty (e.g., for pie, use "Slice" + i)
    if (!label || label.trim() === "") {
      label =
        chartType === "pie" || chartType === "doughnut"
          ? `Segment ${i + 1}`
          : `Item ${i + 1}`;
    }
    label = label.trim().substring(0, 20); // Truncate long labels, prevent overflow
    return label || `Label ${i + 1}`; // Absolute fallback
  });

  const values = dataPoints.map((point) => point.value || point.amount || 0);

  console.log("Generated labels:", labels); // DEBUG: Verify here—should be ["Remote Work", "Office Work"]
  console.log("Generated values:", values);

  const datasets = [
    {
      data: values,
      backgroundColor:
        chartType === "line" || chartType === "area"
          ? CHART_COLORS.primary
          : [
              CHART_COLORS.primary,
              CHART_COLORS.secondary,
              CHART_COLORS.tertiary,
              CHART_COLORS.quaternary,
              CHART_COLORS.quinary,
              CHART_COLORS.senary,
              CHART_COLORS.septenary,
              CHART_COLORS.octonary,
            ].slice(0, values.length),
      borderColor:
        chartType === "line" || chartType === "area"
          ? CHART_COLORS.primary
          : "rgba(255, 255, 255, 0.8)",
      borderWidth: chartType === "pie" || chartType === "doughnut" ? 2 : 1,
      fill: chartType === "area",
      label: "Dataset", // Explicit dataset label for tooltips
    },
  ];

  if (chartType === "line" || chartType === "area") {
    datasets[0].tension = 0.4;
    datasets[0].pointBackgroundColor = CHART_COLORS.primary;
    datasets[0].pointBorderColor = "#ffffff";
    datasets[0].pointBorderWidth = 2;
    datasets[0].pointRadius = 6;
  }

  const formattedData = { labels, datasets };
  console.log("Final formatted data:", formattedData); // DEBUG: Full output
  return formattedData;
}

function getChartOptions(chartType, title) {
  const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 2000,
      easing: "easeInOutQuart",
    },
    plugins: {
      title: {
        display: true,
        text: title,
        font: {
          size: 16,
          weight: "600",
        },
        color: "#1e293b",
        padding: 20,
      },
      legend: {
        position:
          chartType === "pie" || chartType === "doughnut" ? "bottom" : "top",
        display: true,
        labels: {
          padding: 20,
          usePointStyle: false,
          font: {
            size: 12,
          },
          color: "#64748b",
          boxWidth: 20,
          generateLabels: function (chart) {
            console.log(
              "generateLabels called for chart:",
              chart.config.type,
              "with labels:",
              chart.data.labels
            ); // Your existing log (good!)

            const data = chart.data;
            const dataset = data.datasets[0];
            const total = dataset.data.reduce(
              (sum, value) => sum + (value || 0),
              0
            );

            if (!data.labels || !data.labels.length || total === 0) {
              console.warn(
                "generateLabels: Skipping due to no labels or total=0"
              );
              return []; // Graceful empty
            }

            const legendItems = data.labels.map((label, i) => {
              const value = dataset.data[i] || 0;
              let labelText = label;

              const currentType = chart.config.type;
              if (currentType === "pie" || currentType === "doughnut") {
                const percentage =
                  total > 0 ? ((value / total) * 100).toFixed(1) : "0.0";
                labelText = `${label}: ${value} (${percentage}%)`;
              } else {
                labelText = `${label}: ${value}`;
              }

              const item = {
                text: labelText, // REQUIRED: This drives the visible text
                fillStyle: dataset.backgroundColor[i] || "#gray", // Color for dot
                strokeStyle: dataset.borderColor || dataset.backgroundColor[i],
                lineWidth: dataset.borderWidth || 0,
                pointStyle: "circle", // Shape of dot
                hidden: false, // FORCE VISIBLE
                index: i,
              };

              console.log(`Generated legend item ${i}:`, item); // NEW: Log each item

              return item;
            });

            console.log("Full legend items returned:", legendItems); // NEW: Log the array
            console.log(
              "Array length:",
              legendItems.length,
              "vs labels length:",
              data.labels.length
            ); // NEW: Check match

            return legendItems;
          },
        },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        titleColor: "#ffffff",
        bodyColor: "#ffffff",
        borderColor: "#475569",
        borderWidth: 1,
        cornerRadius: 8,
        padding: 12,
        callbacks: {
          label: function (context) {
            const label = context.dataset.label || "";
            const value =
              context.parsed.y !== undefined
                ? context.parsed.y
                : context.parsed;
            const datasetData = context.dataset.data;

            // Calculate percentage for pie/doughnut charts
            if (chartType === "pie" || chartType === "doughnut") {
              const total = datasetData.reduce((a, b) => a + b, 0);
              const percentage = ((value / total) * 100).toFixed(1);
              return `${context.label}: ${value} (${percentage}%)`;
            }

            // For other chart types, show label and value
            if (chartType === "line" || chartType === "area") {
              return `${label}: ${value}`;
            }

            // For bar charts
            if (chartType === "bar") {
              return `${context.label}: ${value}`;
            }

            // Default format
            return `${context.label}: ${value}`;
          },
          title: function (context) {
            if (chartType === "pie" || chartType === "doughnut") {
              return context[0].dataset.label || title;
            }
            return context[0].label || title;
          },
        },
      },
    },
    // Custom callback for hover effects
    onHover: function (event, elements) {
      event.native.target.style.cursor =
        elements.length > 0 ? "pointer" : "default";
    },
  };

  if (chartType === "bar") {
    baseOptions.scales = {
      y: {
        beginAtZero: true,
        grid: {
          color: "#e2e8f0",
        },
        ticks: {
          color: "#64748b",
        },
      },
      x: {
        grid: {
          display: false,
        },
        ticks: {
          color: "#64748b",
        },
      },
    };
  } else if (chartType === "line" || chartType === "area") {
    baseOptions.scales = {
      y: {
        beginAtZero: true,
        grid: {
          color: "#e2e8f0",
        },
        ticks: {
          color: "#64748b",
        },
      },
      x: {
        grid: {
          color: "#f1f5f9",
        },
        ticks: {
          color: "#64748b",
        },
      },
    };
  }

  return baseOptions;
}

function createChartElement(chartConfig, confidence) {
  const chartCard = document.createElement("div");
  chartCard.className = "chart-card";

  const confidencePercent = Math.round(confidence * 100);
  const title =
    chartConfig.title || chartConfig.chartTitle || "Data Visualization";
  const description =
    chartConfig.description ||
    chartConfig.analysisDescription ||
    "AI-generated chart based on your data";

  chartCard.innerHTML = `
    <div class="chart-header">
      <div class="chart-title">
        <h3 data-testid="text-chart-title">${title}</h3>
        <span class="confidence-badge" data-testid="badge-confidence">${confidencePercent}% confidence</span>
      </div>
      <p class="chart-subtitle" data-testid="text-chart-description">${description}</p>
    </div>
    <div class="chart-content">
      <canvas class="chart-canvas" data-testid="canvas-chart"></canvas>
      <div class="chart-controls">
        <div class="chart-export-controls">
          <button class="btn btn-ghost btn-sm copy-btn" data-testid="button-copy-chart" title="Copy chart image to clipboard">
            <i data-lucide="copy"></i>
            Copy
          </button>
          <button class="btn btn-ghost btn-sm download-img-btn" data-testid="button-download-image" title="Download chart as PNG">
            <i data-lucide="download"></i>
            Image
          </button>
        </div>
      </div>
    </div>
  `;

  return chartCard;
}

function renderChart(canvas, chartData, chartType, title) {
  const ctx = canvas.getContext("2d");

  // Destroy existing chart if it exists
  if (canvas.chart) {
    canvas.chart.destroy();
  }

  const data = formatDataForChart(chartData, chartType);
  const options = getChartOptions(chartType, title);

  // Override chart options if provided in chartData
  if (chartData && chartData.options) {
    Object.assign(options, chartData.options);
    // Ensure our responsive settings remain
    options.responsive = true;
    options.maintainAspectRatio = false;
  }

  let ChartClass;
  switch (chartType) {
    case "bar":
      ChartClass = Chart;
      options.type = "bar";
      break;
    case "pie":
      ChartClass = Chart;
      options.type = "pie";
      break;
    case "line":
      ChartClass = Chart;
      options.type = "line";
      break;
    case "doughnut":
      ChartClass = Chart;
      options.type = "doughnut";
      break;
    case "area":
      ChartClass = Chart;
      options.type = "line";
      data.datasets[0].fill = true;
      break;
    default:
      ChartClass = Chart;
      options.type = "bar";
  }

  canvas.chart = new Chart(ctx, {
    type: options.type,
    data: data,
    options: options,
  });

  return canvas.chart;
}

// Export Functions
async function copyChartToClipboard(canvas) {
  try {
    canvas.toBlob(async (blob) => {
      const item = new ClipboardItem({ "image/png": blob });
      await navigator.clipboard.write([item]);
      showNotification("Chart copied to clipboard!", "success");
    });
  } catch (error) {
    console.error("Failed to copy chart:", error);
    showNotification("Failed to copy chart to clipboard", "error");
  }
}

function downloadChartAsImage(canvas, title) {
  try {
    // Create high-resolution canvas for better quality
    const originalWidth = canvas.width;
    const originalHeight = canvas.height;
    const scale = 3; // 3x resolution for better quality

    // Create temporary high-res canvas
    const tempCanvas = document.createElement("canvas");
    const tempCtx = tempCanvas.getContext("2d");

    tempCanvas.width = originalWidth * scale;
    tempCanvas.height = originalHeight * scale;

    // Enable image smoothing for better quality
    tempCtx.imageSmoothingEnabled = true;
    tempCtx.imageSmoothingQuality = "high";

    // Scale and draw the original canvas
    tempCtx.drawImage(
      canvas,
      0,
      0,
      originalWidth * scale,
      originalHeight * scale
    );

    // Download the high-resolution image
    const link = document.createElement("a");
    link.download = `${title
      .replace(/[^a-z0-9]/gi, "_")
      .toLowerCase()}_chart.png`;
    link.href = tempCanvas.toDataURL("image/png", 1.0); // Maximum quality
    link.click();

    showNotification("High-quality chart image downloaded!", "success");
  } catch (error) {
    console.error("Failed to download chart image:", error);
    showNotification("Failed to download chart image", "error");
  }
}

function showNotification(message, type = "info") {
  // Create notification element
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.textContent = message;

  // Style the notification
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 24px;
    border-radius: 8px;
    color: white;
    font-weight: 600;
    z-index: 10000;
    opacity: 0;
    transform: translateX(100%);
    transition: all 0.3s ease;
    max-width: 300px;
  `;

  // Set background color based on type
  switch (type) {
    case "success":
      notification.style.backgroundColor = "#10b981";
      break;
    case "error":
      notification.style.backgroundColor = "#ef4444";
      break;
    case "info":
    default:
      notification.style.backgroundColor = "#2563eb";
      break;
  }

  // Add to page
  document.body.appendChild(notification);

  // Animate in
  setTimeout(() => {
    notification.style.opacity = "1";
    notification.style.transform = "translateX(0)";
  }, 10);

  // Remove after 3 seconds
  setTimeout(() => {
    notification.style.opacity = "0";
    notification.style.transform = "translateX(100%)";
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 3000);
}

// API Functions
async function analyzeTextData(text, chartType = "auto") {
  const response = await fetch(`${API_BASE_URL}/api/analyze-data`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, chartType }),
  });
  if (!response.ok)
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  return await response.json();
}

async function analyzeTextDataMulti(text, maxCharts = 5) {
  const response = await fetch(`${API_BASE_URL}/api/analyze-data-multi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, maxCharts }),
  });
  if (!response.ok)
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  return await response.json();
}

async function parseCSVData(csvContent) {
  const response = await fetch(`${API_BASE_URL}/api/parse-csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ csvContent }),
  });
  if (!response.ok)
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  return await response.json();
}

// New: Upload PDF API
async function uploadPdf(pdfFile) {
  const formData = new FormData();
  formData.append("file", pdfFile);

  const response = await fetch(`${API_BASE_URL}/api/upload-pdf`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok)
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  return await response.json();
}

// New: Query PDF API
async function queryPdf(query, sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId }),
  });
  if (!response.ok)
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  return await response.json();
}

// Event Handlers
function handleChartModeSelection(event) {
  // Find the button element (in case user clicked on nested element)
  const button =
    event.currentTarget.closest(".chart-mode-btn") || event.currentTarget;

  chartModeButtons.forEach((btn) => btn.classList.remove("active"));
  button.classList.add("active");
  currentChartMode = button.dataset.mode;
}

function handleChartTypeSelection(event) {
  chartTypeButtons.forEach((btn) => btn.classList.remove("active"));
  event.currentTarget.classList.add("active");
  currentChartType = event.currentTarget.dataset.type;
}

function handleTextInput() {
  const hasText = textInput.value.trim().length > 0;
  analyzeTextBtn.disabled = !hasText || isProcessing;
}

function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (file.type !== "text/csv" && file.type !== "text/plain") {
    alert("Please upload a CSV or TXT file.");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    uploadedFile = {
      name: file.name,
      content: e.target.result,
    };

    uploadArea.style.display = "none";
    uploadedFileDisplay.style.display = "flex";
    uploadedFileDisplay.querySelector(".file-name").textContent = file.name;
    analyzeFileBtn.disabled = false;
  };

  reader.readAsText(file);
}

function handleFileDrop(event) {
  event.preventDefault();
  uploadArea.classList.remove("drag-active");

  const files = Array.from(event.dataTransfer.files);
  const file = files[0];

  if (!file || (file.type !== "text/csv" && file.type !== "text/plain")) {
    alert("Please upload a CSV or TXT file.");
    return;
  }

  // Simulate file input change
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  fileInput.files = dataTransfer.files;
  handleFileUpload({ target: { files: [file] } });
}

function handleDragOver(event) {
  event.preventDefault();
  uploadArea.classList.add("drag-active");
}

function handleDragLeave(event) {
  event.preventDefault();
  uploadArea.classList.remove("drag-active");
}

function clearText() {
  textInput.value = "";
  handleTextInput();
}

function removeFile() {
  uploadedFile = null;
  uploadArea.style.display = "block";
  uploadedFileDisplay.style.display = "none";
  fileInput.value = "";
  analyzeFileBtn.disabled = true;
}

async function analyzeText() {
  if (!textInput.value.trim() || isProcessing) return;

  isProcessing = true;
  analyzeTextBtn.disabled = true;

  try {
    showLoading("Analyzing your data...");

    const text = textInput.value.trim();

    let result;
    if (currentChartMode === "multi") {
      result = await analyzeTextDataMulti(text);
    } else {
      result = await analyzeTextData(text, currentChartType);
    }

    hideLoading();

    if (result.success) {
      currentData = result.data;
      showResultsPage();
      displayResults(result.data);
    } else {
      alert("Error analyzing data: " + (result.error || "Unknown error"));
    }
  } catch (error) {
    hideLoading();
    alert("Error analyzing data: " + error.message);
  } finally {
    isProcessing = false;
    analyzeTextBtn.disabled = false;
  }
}

async function analyzeFile() {
  if (!uploadedFile || isProcessing) return;

  isProcessing = true;
  analyzeFileBtn.disabled = true;

  try {
    showLoading("Processing your file...");

    const result = await parseCSVData(uploadedFile.content);

    hideLoading();

    if (result.success) {
      currentData = result.data;
      showResultsPage();
      displayResults(result.data);
    } else {
      alert("Error processing file: " + (result.error || "Unknown error"));
    }
  } catch (error) {
    hideLoading();
    alert("Error processing file: " + error.message);
  } finally {
    isProcessing = false;
    analyzeFileBtn.disabled = false;
  }
}

// New: PDF Upload Handlers
function handlePdfUpload(event) {
  const file = event.target.files[0];
  if (!file || file.type !== "application/pdf") {
    alert("Please upload a PDF file.");
    return;
  }

  uploadedPdf = file;
  pdfUploadArea.style.display = "none";
  uploadedPdfDisplay.style.display = "flex";
  uploadedPdfDisplay.querySelector(".pdf-name").textContent = file.name;
  analyzePdfBtn.disabled = false;
}

function handlePdfDrop(event) {
  event.preventDefault();
  pdfUploadArea.classList.remove("drag-active");

  const file = event.dataTransfer.files[0];
  if (!file || file.type !== "application/pdf") {
    alert("Please upload a PDF file.");
    return;
  }

  pdfInput.files = new DataTransfer().items.add(file).files;
  handlePdfUpload({ target: { files: [file] } });
}

function removePdf() {
  uploadedPdf = null;
  pdfUploadArea.style.display = "block";
  uploadedPdfDisplay.style.display = "none";
  pdfInput.value = "";
  analyzePdfBtn.disabled = true;
  pdfSessionId = null;
}

async function analyzePdf() {
  if (!uploadedPdf || isProcessing) return;
  isProcessing = true;
  analyzePdfBtn.disabled = true;
  try {
    showLoading("Processing your PDF...");
    const result = await uploadPdf(uploadedPdf);
    hideLoading();
    if (result.success) {
      pdfSessionId = result.session_id;
      showResultsPage(true);
      displayExtractedCharts(result.extracted_charts);
      // Display session ID for reuse
      const sessionInfo = document.createElement("p");
      sessionInfo.textContent = `Session ID: ${pdfSessionId} (Save this to reuse without reprocessing)`;
      extractedChartsContainer.appendChild(sessionInfo);
    } else {
      alert(
        "Error processing PDF: " +
          (result.error || result.detail || "Unknown error")
      );
    }
  } catch (error) {
    hideLoading();
    alert("Error processing PDF: " + error.message);
  } finally {
    isProcessing = false;
    analyzePdfBtn.disabled = false;
  }
}

// Add function to query with existing session ID
function queryWithSessionId() {
  const sessionIdInput = prompt("Enter Session ID to reuse:");
  if (sessionIdInput) {
    pdfSessionId = sessionIdInput;
    showResultsPage(true);
    // Optionally fetch charts for the session
    fetch(`/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "List all charts",
        session_id: pdfSessionId,
      }),
    })
      .then((response) => response.json())
      .then((result) => {
        if (result.success && result.data.existing_charts) {
          displayExtractedCharts(result.data.existing_charts);
        } else {
          alert(
            "Failed to load session: " + (result.detail || "Invalid session ID")
          );
        }
      })
      .catch((error) => alert("Error querying session: " + error.message));
  }
}

// Add button to reuse session ID (add to index.html and call this function)
document
  .getElementById("reuseSessionBtn")
  ?.addEventListener("click", queryWithSessionId);

// New: Display Extracted Charts
function displayExtractedCharts(charts) {
  extractedChartsContainer.innerHTML = ""; // Clear previous content
  if (charts && charts.length > 0) {
    extractedChartsContainer.style.display = "block";
    // Ensure .extracted-charts-grid exists
    let grid = extractedChartsContainer.querySelector(".extracted-charts-grid");
    if (!grid) {
      grid = document.createElement("div");
      grid.className = "extracted-charts-grid";
      extractedChartsContainer.appendChild(grid);
    }
    // Add title if not present
    if (!extractedChartsContainer.querySelector("h3")) {
      const title = document.createElement("h3");
      title.textContent = "Extracted Charts from PDF";
      extractedChartsContainer.insertBefore(title, grid);
    }
    charts.forEach((chart, index) => {
      const imgElement = document.createElement("div");
      imgElement.className = "extracted-chart";
      imgElement.innerHTML = `
        <img src="${chart.base64}" alt="Extracted Chart ${
        index + 1
      }" style="max-width: 100%; margin-bottom: 10px;">
        <p>${chart.description}</p>
      `;
      grid.appendChild(imgElement);
    });
  } else {
    extractedChartsContainer.style.display = "none";
  }
}

// ... (rest of the file unchanged)

// New: Submit PDF Query
async function submitPdfQuery() {
  const query = pdfQueryInput.value.trim();
  if (!query || !pdfSessionId || isProcessing) return;

  isProcessing = true;
  submitPdfQueryBtn.disabled = true;

  try {
    showLoading("Querying your PDF...");

    const result = await queryPdf(query, pdfSessionId);

    hideLoading();

    if (result.success) {
      const data = result.data;
      pdfQueryResponse.innerHTML = `<p><strong>Answer:</strong> ${data.answer}</p>`;

      if (data.intent === "viz" && data.chart_config) {
        // Render generated chart
        chartsContainer.style.display = "block";
        chartsContainer.innerHTML = "";
        const chartCard = createChartElement(
          { title: "Generated Chart from Query", description: data.answer },
          data.confidence || 0.9
        );
        chartsContainer.appendChild(chartCard);
        const canvas = chartCard.querySelector(".chart-canvas");
        renderChart(
          canvas,
          data.chart_config.data,
          data.chart_config.type,
          "Generated Chart"
        );
      }

      if (data.existing_charts && data.existing_charts.length > 0) {
        pdfQueryResponse.innerHTML += "<h4>Relevant Existing Charts:</h4>";
        data.existing_charts.forEach((chart) => {
          pdfQueryResponse.innerHTML += `<img src="${chart.base64}" alt="Existing Chart" style="max-width: 300px; margin: 10px;"><p>${chart.description}</p>`;
        });
      }
    } else {
      alert("Error querying PDF: " + (result.error || "Unknown error"));
    }
  } catch (error) {
    hideLoading();
    alert("Error querying PDF: " + error.message);
  } finally {
    isProcessing = false;
    submitPdfQueryBtn.disabled = false;
    pdfQueryInput.value = ""; // Clear input
  }
}

function displayResults(data) {
  console.log("Displaying results with data:", data);

  loadingState.style.display = "none";
  chartsContainer.style.display = "block";

  chartsContainer.innerHTML = "";

  if (data.multiChartAnalysis) {
    // Show Download All Charts button for multi-chart mode
    downloadAllChartsBtn.style.display = "block";
    // Multiple charts
    console.log("Rendering multiple charts:", data.chartConfigs);
    data.chartConfigs.forEach((chartConfig, index) => {
      const confidence =
        data.multiChartAnalysis.confidenceScores?.[index] || 0.9;
      const chartCard = createChartElement(chartConfig, confidence);
      chartsContainer.appendChild(chartCard);

      const canvas = chartCard.querySelector(".chart-canvas");
      setTimeout(() => {
        const title =
          chartConfig.title || chartConfig.chartTitle || `Chart ${index + 1}`;

        // For multi-chart, analyzedData might be in chartConfig directly or nested
        const analyzedData =
          chartConfig.analyzedData || chartConfig.dataPoints || chartConfig;
        console.log(`Rendering chart ${index + 1} with data:`, analyzedData);

        renderChart(canvas, analyzedData, chartConfig.type, title);

        // Add export functionality
        const copyBtn = chartCard.querySelector(".copy-btn");
        const downloadImgBtn = chartCard.querySelector(".download-img-btn");

        copyBtn.addEventListener("click", () => copyChartToClipboard(canvas));
        downloadImgBtn.addEventListener("click", () =>
          downloadChartAsImage(canvas, title)
        );
      }, index * 200);
    });
  } else {
    // Hide Download All Charts button for single chart mode
    downloadAllChartsBtn.style.display = "none";
    // Single chart
    console.log("Rendering single chart:", data.chartConfig);
    const chartConfig = data.chartConfig;
    const confidence = Object.values(data.confidence || {})[0] || 0.9;
    const chartCard = createChartElement(chartConfig, confidence);
    chartsContainer.appendChild(chartCard);

    const canvas = chartCard.querySelector(".chart-canvas");
    setTimeout(() => {
      const title =
        chartConfig.title ||
        chartConfig.chartTitle ||
        data.analyzedData?.title ||
        "Data Visualization";
      console.log("Rendering single chart with data:", data.analyzedData);

      renderChart(canvas, data.analyzedData, chartConfig.type, title);

      // Add export functionality
      const copyBtn = chartCard.querySelector(".copy-btn");
      const downloadImgBtn = chartCard.querySelector(".download-img-btn");

      copyBtn.addEventListener("click", () => copyChartToClipboard(canvas));
      downloadImgBtn.addEventListener("click", () =>
        downloadChartAsImage(canvas, title)
      );
    }, 100);
  }

  // Re-initialize Lucide icons for new elements
  lucide.createIcons();
}

function backToHome() {
  showHomePage();
  // Reset state
  currentData = null;
  chartsContainer.innerHTML = "";
}

async function downloadAllCharts() {
  try {
    showNotification("Preparing to download all charts...", "info");

    // Get all chart canvases
    const canvases = document.querySelectorAll(".chart-canvas");
    if (canvases.length === 0) {
      throw new Error("No charts found to download");
    }

    // Download each chart individually with high quality
    for (let i = 0; i < canvases.length; i++) {
      const canvas = canvases[i];
      const chartCard = canvas.closest(".chart-card");
      const titleElement = chartCard?.querySelector(".chart-title h3");
      const title = titleElement?.textContent || `Chart_${i + 1}`;

      // Create high-resolution canvas for better quality
      const originalWidth = canvas.width;
      const originalHeight = canvas.height;
      const scale = 3; // 3x resolution for better quality

      // Create temporary high-res canvas
      const tempCanvas = document.createElement("canvas");
      const tempCtx = tempCanvas.getContext("2d");

      tempCanvas.width = originalWidth * scale;
      tempCanvas.height = originalHeight * scale;

      // Enable image smoothing for better quality
      tempCtx.imageSmoothingEnabled = true;
      tempCtx.imageSmoothingQuality = "high";

      // Scale and draw the original canvas
      tempCtx.drawImage(
        canvas,
        0,
        0,
        originalWidth * scale,
        originalHeight * scale
      );

      // Download the high-resolution image
      const link = document.createElement("a");
      link.download = `${title
        .replace(/[^a-z0-9]/gi, "_")
        .toLowerCase()}_chart.png`;
      link.href = tempCanvas.toDataURL("image/png", 1.0); // Maximum quality
      link.style.display = "none";

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Small delay between downloads
      if (i < canvases.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }

    showNotification(
      `${canvases.length} high-quality charts downloaded successfully!`,
      "success"
    );
  } catch (error) {
    console.error("Failed to download charts:", error);
    showNotification("Failed to download charts: " + error.message, "error");
  }
}

// Initialize Event Listeners
function initializeEventListeners() {
  // Chart mode selection
  chartModeButtons.forEach((btn) => {
    btn.addEventListener("click", handleChartModeSelection);
  });

  // Chart type selection
  chartTypeButtons.forEach((btn) => {
    btn.addEventListener("click", handleChartTypeSelection);
  });

  // Text input
  textInput.addEventListener("input", handleTextInput);
  clearTextBtn.addEventListener("click", clearText);
  analyzeTextBtn.addEventListener("click", analyzeText);

  // File upload
  fileInput.addEventListener("change", handleFileUpload);
  uploadArea.addEventListener("click", () => fileInput.click());
  uploadArea.addEventListener("dragover", handleDragOver);
  uploadArea.addEventListener("dragleave", handleDragLeave);
  uploadArea.addEventListener("drop", handleFileDrop);
  removeFileBtn.addEventListener("click", removeFile);
  analyzeFileBtn.addEventListener("click", analyzeFile);

  // Results page
  backToHomeBtn.addEventListener("click", backToHome);
  downloadAllChartsBtn.addEventListener("click", downloadAllCharts);

  // New: PDF upload listeners
  pdfInput.addEventListener("change", handlePdfUpload);
  pdfUploadArea.addEventListener("click", () => pdfInput.click());
  pdfUploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    pdfUploadArea.classList.add("drag-active");
  });
  pdfUploadArea.addEventListener("dragleave", () =>
    pdfUploadArea.classList.remove("drag-active")
  );
  pdfUploadArea.addEventListener("drop", handlePdfDrop);
  removePdfBtn.addEventListener("click", removePdf);
  analyzePdfBtn.addEventListener("click", analyzePdf);

  // New: PDF query listener
  submitPdfQueryBtn.addEventListener("click", submitPdfQuery);
  pdfQueryInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") submitPdfQuery();
  });

  // Initialize button states
  handleTextInput();
}

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
  initializeEventListeners();
  showHomePage();
});

function clearSession() {
  if (!pdfSessionId) {
    alert("No session ID available to clear");
    return;
  }
  fetch(`/api/clear-session/${pdfSessionId}`, { method: "DELETE" })
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        alert(result.message);
        pdfSessionId = null;
        showResultsPage(false);
      } else {
        alert("Failed to clear session: " + (result.detail || "Unknown error"));
      }
    })
    .catch((error) => alert("Error clearing session: " + error.message));
}

// Add to event listeners
document
  .getElementById("clearSessionBtn")
  ?.addEventListener("click", clearSession);
