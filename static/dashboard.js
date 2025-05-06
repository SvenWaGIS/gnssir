let currentConfig = {};
let configVisible = false;

// Toggle visibility of config section
function toggleConfig() {
  const section = document.getElementById("configSection");
  configVisible = !configVisible;
  section.style.display = configVisible ? "block" : "none";
}

// Render the config form
function renderForm(config) {
  const form = document.getElementById("configForm");
  form.innerHTML = "";

  const nonBooleans = [];
  const booleans = [];

  for (const [key, value] of Object.entries(config)) {
    const div = document.createElement("div");
    let inputField;

    if (typeof value === "boolean") {
      inputField = `<input type="checkbox" name="${key}" ${value ? "checked" : ""} />`;
      booleans.push({ key, inputField });
    } else {
      inputField = `<input name="${key}" value="${value !== null ? value : ""}" />`;
      nonBooleans.push({ key, inputField });
    }
  }

  const addEntry = ({ key, inputField }) => {
    const div = document.createElement("div");
    div.innerHTML = `
      <label>${key}:</label>
      ${inputField}
      <button type="button" onclick="deleteField('${key}')">Delete</button>
    `;
    form.appendChild(div);
  };

  nonBooleans.forEach(addEntry);
  booleans.forEach(addEntry);
}

async function refreshDropdown() {
  const res = await fetch("/list_configs");
  const stations = await res.json();
  const select = document.getElementById("stationSelect");
  select.innerHTML = "";
  stations.forEach(station => {
    const option = document.createElement("option");
    option.value = station;
    option.textContent = station;
    select.appendChild(option);
  });
}

async function loadConfig() {
    const station = document.getElementById("stationSelect").value;
    const res = await fetch(`/get_config?station=${station}`);
    const data = await res.json();
  
    if (data.error) {
      alert(data.error);
      currentConfig = {};
    } else {
      currentConfig = data;
    }
  
    renderForm(currentConfig);
    await refreshLogDropdown();
    updateSelectedStation(station);
  }
  

async function createConfig() {
  const station = prompt("Enter new station code:");
  if (!station) return;
  const res = await fetch(`/create_config?station=${station}`, { method: "POST" });
  const data = await res.json();
  alert(data.status || data.error);
  await refreshDropdown();
}

async function deleteConfig() {
  const station = document.getElementById("stationSelect").value;
  if (!confirm(`Delete config for station ${station}?`)) return;
  const res = await fetch(`/delete_config?station=${station}`, { method: "DELETE" });
  const data = await res.json();
  alert(data.status || data.error);
  currentConfig = {};
  renderForm(currentConfig);
  await refreshDropdown();
}

function addField() {
  const key = prompt("Enter new parameter name:");
  if (!key) return;
  currentConfig[key] = "";
  renderForm(currentConfig);
}

function deleteField(key) {
  if (confirm(`Are you sure you want to delete the field "${key}"?`)) {
    delete currentConfig[key];
    renderForm(currentConfig);
  }
}

async function saveConfig() {
  const station = document.getElementById("stationSelect").value;
  const inputs = document.querySelectorAll("#configForm input");
  const configToSave = {};

  inputs.forEach(input => {
    const name = input.name;
    if (input.type === "checkbox") {
      configToSave[name] = input.checked;
    } else {
      const val = input.value;
      configToSave[name] = val === "" ? null : isNaN(val) ? val : Number(val);
    }
  });

  const res = await fetch(`/set_config?station=${station}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(configToSave)
  });

  const result = await res.json();
  alert(result.status || result.error || "Saved");
  configVisible = false;
  document.getElementById("configSection").style.display = "none";
}

async function populateDropdown(url, dropdownId) {
  try {
    const response = await fetch(url);
    const data = await response.json();
    const dropdown = document.getElementById(dropdownId);
    dropdown.innerHTML = "";
    const key = dropdownId.includes("snr") ? "snr_files" : "nmea_files";

    data[key].forEach(file => {
      const option = document.createElement("option");
      option.value = file;
      option.textContent = file;
      dropdown.appendChild(option);
    });
  } catch (err) {
    console.error("Failed to fetch files:", err);
  }
}

function refreshFileDropdowns() {
  const station = "MYC2"; // Replace or read dynamically
  const year = "2025";    // Replace or read dynamically

  populateDropdown(`/list_snr_files_for_station?station=${station}&year=${year}`, "snrDropdown");
  populateDropdown(`/list_nmea_files_for_station?station=${station}&year=${year}`, "nmeaDropdown");
}

// Automatically load on page load
window.addEventListener("DOMContentLoaded", refreshFileDropdowns);


async function loadLogList() {
  const station = document.getElementById("stationSelect").value;
  const res = await fetch(`/log_files?station=${station}`);
  const files = await res.json();
  const select = document.getElementById("logFileSelect");
  select.innerHTML = "";
  files.forEach(f => {
    const opt = document.createElement("option");
    opt.value = f;
    opt.textContent = f;
    select.appendChild(opt);
  });
}

async function downloadLog() {
  const station = document.getElementById("stationSelect").value;
  const filename = document.getElementById("logFileSelect").value;
  window.location = `/download_log?station=${station}&filename=${filename}`;
}

document.getElementById("logFileSelect").addEventListener("change", previewLog);

async function previewLog() {
  const station = document.getElementById("stationSelect").value;
  const filename = document.getElementById("logFileSelect").value;
  if (!filename) return;
  const res = await fetch(`/read_log?station=${station}&filename=${filename}`);
  const data = await res.json();
  document.getElementById("logPreview").value = data.content || "Failed to load log.";
}

async function refreshLogDropdown() {
  const station = document.getElementById("stationSelect").value;
  const res = await fetch(`/list_logs?station=${station}`);
  const logs = await res.json();
  const select = document.getElementById("logFileSelect");
  select.innerHTML = "";

  if (logs.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No logs available";
    select.appendChild(option);
    return;
  }

  logs.forEach(filename => {
    const option = document.createElement("option");
    option.value = filename;
    option.textContent = filename;
    select.appendChild(option);
  });

  // Auto-select latest and preview
  select.selectedIndex = logs.length - 1;
  previewLog();
}

async function uploadNMEA() {
    const files = document.getElementById("nmeaFileInput").files;
    if (!files.length) {
      alert("Please select at least one file.");
      return;
    }
  
    const formData = new FormData();
    for (const file of files) {
      formData.append("nmea_files", file);
    }
  
    const res = await fetch("/process/", {
      method: "POST",
      body: formData
    });
  
    const result = await res.json();
    alert("Upload complete. Check logs for details.");
    console.log(result);
  
    // Extract station from first uploaded file
    const firstFilename = files[0].name;
    const match = firstFilename.match(/ZED_(\w{4})_/);
    if (match) {
      const station = match[1];
  
      // Set dropdown to station (if available)
      const select = document.getElementById("stationSelect");
      const option = [...select.options].find(opt => opt.value === station);
      if (option) {
        select.value = station;
        await loadConfig();
        await refreshLogDropdown();
        await previewLog();
        updateSelectedStation(station);  // Update the "Selected Station" label
  
        // Flash the dropdown briefly
        select.style.backgroundColor = "#ffff99"; // light yellow
        setTimeout(() => {
          select.style.backgroundColor = "";
        }, 1000);
      }
    }
  }  
  
  function updateSelectedStation(station) {
    const stationLabel = document.getElementById("currentStationLabel");
    if (stationLabel) {
      stationLabel.textContent = `Selected Station: ${station}`;
    }
  }
  

refreshDropdown();
