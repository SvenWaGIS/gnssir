#todo:
#how are changes in year (Folder structure!) or month handled
#make folder structure accesable/changeable? (graph for fold sturcture)
#get lat/lon/height from SARA txtfile! (and station/date?)
#fix time in logs to CET
#display files in dashboard (snr/nmea files!)
#Comment Code


from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from typing import List
from datetime import datetime, timedelta
import subprocess
import os
import requests
from starlette.datastructures import UploadFile as StarletteUploadFile
from io import BytesIO
import re
import glob
import json

# Write logs / cleanup old files
def write_log(station: str, message: str):
    log_dir = f"/etc/gnssrefl/refl_code/html_logs/{station}"
    os.makedirs(log_dir, exist_ok=True)

    log_filename = datetime.utcnow().strftime("%Y-%m-%d") + ".log"
    log_path = os.path.join(log_dir, log_filename)

    with open(log_path, "a") as f:
        f.write(message + "\n" + "-" * 40 + "\n")

def cleanup_old_logs():
    root_log_dir = "/etc/gnssrefl/refl_code/html_logs"
    for station_dir in glob.glob(f"{root_log_dir}/*"):
        for file in glob.glob(f"{station_dir}/*.log"):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file))
            if (datetime.utcnow() - file_mtime).days > 7:
                os.remove(file)

# api endpoints:
app = FastAPI()
@app.get("/")
def index():
    return FileResponse("static/index.html")
# Mount static folder at /static
app.mount("/static", StaticFiles(directory="static"), name="static")

#-------------- TEST FOLDER STRUCT ------------------------------------------------------
@app.get("/test_refl_code")
def test_refl_code():
    base_dir = "/app/refl_code"

    # Test write
    try:
        os.makedirs(base_dir, exist_ok=True)
        test_file = os.path.join(base_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Hello from Render!")

        # Test read
        with open(test_file, "r") as f:
            content = f.read()

        return JSONResponse(content={"status": "ok", "read_content": content})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)})
#----------------------------------------------------------------------------------------

# Log files
@app.get("/log_files/")
def list_log_files(station: str):
    log_dir = f"/etc/gnssrefl/refl_code/html_logs/{station}"
    if not os.path.isdir(log_dir):
        return []
    return sorted([f for f in os.listdir(log_dir) if f.endswith(".log")])

@app.get("/download_log/")
def download_log(station: str, filename: str):
    full_path = f"/etc/gnssrefl/refl_code/html_logs/{station}/{filename}"
    if not os.path.isfile(full_path):
        return {"error": "Log file not found"}
    return FileResponse(full_path, filename=filename)

@app.get("/read_log/")
def read_log(station: str, filename: str):
    log_path = f"/etc/gnssrefl/refl_code/html_logs/{station}/{filename}"
    if not os.path.isfile(log_path):
        return {"error": "Log file not found"}
    with open(log_path, "r") as f:
        return {"content": f.read()}
    
@app.get("/list_logs")
def list_logs(station: str):
    station_log_dir = f"/etc/gnssrefl/refl_code/html_logs/{station}"
    if not os.path.exists(station_log_dir):
        return []
    logs = sorted(os.listdir(station_log_dir))
    return logs

# Mount static files (Serverfiles)
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    with open("static/dashboard.html") as f:
        return f.read()

# Config files
@app.get("/list_configs")
def list_configs():
    config_files = glob.glob("/configs/*.json")
    return [os.path.basename(f).replace(".json", "") for f in config_files]

@app.post("/create_config")
def create_config(station: str):
    path = f"/configs/{station}.json"
    if os.path.exists(path):
        return {"error": "Config already exists"}
    default_config = {
        "latitude": None,
        "longitude": None,
        "height": None,
        "gzip": False,
        "overwrite": True,
        "snr": "",
        "year_end": "",
        "doy_end": "",
        "dec": "",
        "risky": False,
        "par": "",
        "orb": "",
        "hour": "",
        "debug": False,
        "merge_hours": 6,
        "nmea_retention_hours": 24,
        "snr_retention_days": 1,
        "rawdata_retention_days": 7
    }
    with open(path, "w") as f:
        json.dump(default_config, f, indent=2)
    return {"status": "created"}

@app.delete("/delete_config")
def delete_config(station: str):
    path = f"/configs/{station}.json"
    if not os.path.exists(path):
        return {"error": "Config not found"}
    os.remove(path)
    return {"status": "deleted"}

@app.get("/get_config")
def get_config(station: str):
    path = f"/configs/{station}.json"
    if not os.path.exists(path):
        return {"error": "Config not found"}
    with open(path) as f:
        return json.load(f)

@app.post("/set_config")
def set_config(station: str, config: dict):
    path = f"/configs/{station}.json"
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    return {"status": "saved"}

@app.get("/snr_files/")
def list_snr_files():
    snr_files = glob.glob("/etc/gnssrefl/refl_code/data_safe/snr/**/*.snr*", recursive=True)
    file_list = [file.replace("/etc/gnssrefl/refl_code/", "") for file in snr_files]
    return {"snr_files": file_list}

@app.get("/download_snr/")
def download_snr(filepath: str):
    full_path = f"/etc/gnssrefl/refl_code/{filepath}"
    return FileResponse(path=full_path, filename=filepath.split("/")[-1])

@app.get("/list_snr_files_for_station")
def list_snr_files_for_station(station: str, year: str):
    base_dir = f"/etc/gnssrefl/refl_code/data_safe/snr/{year}/{station}"
    if not os.path.exists(base_dir):
        return {"snr_files": []}
    files = sorted(os.listdir(base_dir))
    return {"snr_files": files}

@app.get("/list_nmea_files_for_station")
def list_nmea_files_for_station(station: str, year: str):
    base_dir = f"/etc/gnssrefl/refl_code/data_safe/nmea/{year}/{station}"
    if not os.path.exists(base_dir):
        return {"nmea_files": []}
    files = sorted(os.listdir(base_dir))
    return {"nmea_files": files}


# File upload from SARA-R5
UPLOAD_DIR = "Webserver/uploads"
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), request: Request = None):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_location = f"{UPLOAD_DIR}/{file.filename}"

    # Save file to disk
    contents = await file.read()
    with open(file_location, "wb") as f:
        f.write(contents)

    # Re-wrap into UploadFile-like object for internal call
    file_stream = BytesIO(contents)
    simulated_file = StarletteUploadFile(filename=file.filename, file=file_stream)

    # Call existing process_nmea function with this one file
    response = await process_nmea(nmea_files=[simulated_file])

    # Extract latest SNR file from response (you already return this from process_nmea!)
    snr_file_list = []
    if isinstance(response, dict):
        for key in ["snr_files", "generated_snr_files"]:
            if key in response:
                snr_file_list = response[key]
                break

    return {
        "status": "processed",
        "filename": file.filename,
        "snr_files": snr_file_list,
    }

# Process data with nmea2snr 
@app.post("/process/")
async def process_nmea(nmea_files: List[UploadFile] = File(...)):

    # Parse the first file for site, year, doy, hour
    first_file = nmea_files[0]
    first_filename = first_file.filename
    file_match = re.match(r"ZED_(\w{4})_(\d{4})_(\d{1,2})_(\d{1,2})_(\d{1,2})\.txt", first_filename)
    if not file_match:
        return {"error": "Filename does not match expected pattern"}

    site, year, month, day, hour = file_match.groups()
    date_obj = datetime(int(year), int(month), int(day), int(hour))
    doy = f"{date_obj.timetuple().tm_yday:03}"

    # Save uploaded files to rawData folder
    raw_data_dir = f"/etc/gnssrefl/refl_code/data_safe/rawdata/{year}/{site}"
    os.makedirs(raw_data_dir, exist_ok=True)

    for file in nmea_files:
        file_path = os.path.join(raw_data_dir, file.filename)
        with open(file_path, "wb") as f_out:
            f_out.write(await file.read())

    # Load station config
    config_path = f"/configs/{site}.json"
    try:
        with open(config_path) as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        return {"error": f"Config file for station {site} not found"}

    # Configurable parameters
    merge_hours = config.get("merge_hours", 6)


    all_files = glob.glob(f"/etc/gnssrefl/refl_code/data_safe/rawdata/{year}/{site}/*.txt")
    print(f"All available rawdata files: {all_files}")


    # Collect last X hours of data (handle day switches)
    times_to_collect = [date_obj - timedelta(hours=i) for i in range(merge_hours - 1, -1, -1)]
    collected_files = []

    print(f"Times to collect: {[tp.strftime('%Y-%m-%d %H') for tp in times_to_collect]}")
    print(f"Collected files for merging: {collected_files}")


    # Anchor day (from latest file timestamp)
    anchor_day = date_obj.day
    anchor_month = date_obj.month
    anchor_year = date_obj.year

    for time_point in times_to_collect:
        # Skip files from a previous day
        if (time_point.day != anchor_day or
            time_point.month != anchor_month or
            time_point.year != anchor_year):
            continue

        target_raw_dir = f"/etc/gnssrefl/refl_code/data_safe/rawdata/{time_point.year}/{site}"
        target_filename = f"ZED_{site}_{time_point.year}_{time_point.month}_{time_point.day}_{time_point.hour:02}.txt"
        target_path = os.path.join(target_raw_dir, target_filename)
        if os.path.exists(target_path):
            collected_files.append(target_path)

    if not collected_files:
        return {"error": "No NMEA files found for the specified merging window."}

    print(f"Collected files for merging: {collected_files}")

    # Create gnssrefl nmea folder
    gnssrefl_nmea_dir = f"/etc/gnssrefl/refl_code/nmea/{site}/{year}"
    os.makedirs(gnssrefl_nmea_dir, exist_ok=True)
    # Cleanup old files in gnssrefl nmea folder
    for file in glob.glob(f"{gnssrefl_nmea_dir}/*"):
        os.remove(file)
    # Create gnssrefl snr folder
    snr_dir = f"/etc/gnssrefl/refl_code/{year}/snr/{site}"
    os.makedirs(snr_dir, exist_ok=True)
    # Cleanup old SNR files before running nmea2snr
    for file in glob.glob(f"{snr_dir}/*.snr*"):
        os.remove(file)

    # Merge collected files into gnssrefl nmea folder
    gnssrefl_nmea_dir = f"/etc/gnssrefl/refl_code/nmea/{site}/{year}"
    os.makedirs(gnssrefl_nmea_dir, exist_ok=True)
    gnssrefl_merged_file = os.path.join(gnssrefl_nmea_dir, f"{site}{doy}0.{year[-2:]}.A")
    with open(gnssrefl_merged_file, "wb") as merged_file:
        for file_path in collected_files:
            with open(file_path, "rb") as f_in:
                merged_file.write(f_in.read())

    # Build nmea2snr command
    cmd = ["nmea2snr", site, year, doy]

    # Prioritized flags first (ordered)
    priority_flags = ["doy_end", "year_end", "latitude", "longitude", "height"]
    for param in priority_flags:
        if param in config and config[param] is not None:
            if param == "latitude":
                cmd += ["-lat", str(config[param])]
            elif param == "longitude":
                cmd += ["-lon", str(config[param])]
            elif param == "height":
                cmd += ["-height", str(config[param])]
            else:
                cmd += [f"-{param}", str(config[param])]

    # Add remaining parameters (excluding ones already added)
    other_params = {
        "snr": str,
        "dec": str,
        "par": str,
        "orb": str,
        "hour": str
    }

    for param, caster in other_params.items():
        if param in config and config[param] is not None:
            cmd += [f"-{param}", caster(config[param])]

    # Handle boolean flags
    bool_params = ["gzip", "overwrite", "risky", "debug"]
    for param in bool_params:
        if param in config and config[param] is not None:
            cmd += [f"-{param}", "true" if config[param] else "false"]

    # Run nmea2snr and capture the command
    command_str = " ".join(cmd)
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Immediately move merged NMEA file to data_safe/nmea with hourly prefix
    data_safe_nmea_dir = f"/etc/gnssrefl/refl_code/data_safe/nmea/{year}/{site}"
    os.makedirs(data_safe_nmea_dir, exist_ok=True)
    hour_prefix = f"{int(hour):02}"
    nmea_safe_filename = f"{hour_prefix}_{site}{doy}0.{year[-2:]}.A"
    subprocess.run(["cp", gnssrefl_merged_file, os.path.join(data_safe_nmea_dir, nmea_safe_filename)])

    # Immediately move SNR file to data_safe/snr with hourly prefix
    snr_dir = f"/etc/gnssrefl/refl_code/{year}/snr/{site}"
    data_safe_snr_dir = f"/etc/gnssrefl/refl_code/data_safe/snr/{year}/{site}"
    os.makedirs(data_safe_snr_dir, exist_ok=True)

    snr_files = glob.glob(f"{snr_dir}/*.snr*")
    for snr_file in snr_files:
        snr_filename = os.path.basename(snr_file)
        snr_safe_filename = f"{hour_prefix}_{snr_filename}"
        subprocess.run(["cp", snr_file, os.path.join(data_safe_snr_dir, snr_safe_filename)])
    
    current_time = datetime.now()
    # Cleanup old merged NMEA files in data_safe
    for file in glob.glob(f"{data_safe_nmea_dir}/*"):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file))
        if (current_time - file_mtime).total_seconds() > 48 * 3600:
            os.remove(file)

    # Cleanup old SNR files in data_safe
    for file in glob.glob(f"{data_safe_snr_dir}/*.snr*"):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file))
        if (current_time - file_mtime).days >= 7:
            os.remove(file)

    # Cleanup old rawdata files in data_safe
    rawdata_retention_days = config.get("rawdata_retention_days", 7)
    rawdata_dir = f"/etc/gnssrefl/refl_code/data_safe/rawdata/{year}/{site}"
    for file in glob.glob(f"{rawdata_dir}/*"):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file))
        if (current_time - file_mtime).days >= rawdata_retention_days:
            os.remove(file)

    # Construct log message BEFORE return
    timestamp = datetime.utcnow().isoformat()
    snr_output = result.stdout.strip().replace("\n", " ... ")
    snr_errors = result.stderr.strip().replace("\n", " ... ")
    command_str = " ".join(cmd)

    # Format merged file list with indentation
    merged_file_list = "\n\t" + "\n\t".join(collected_files) if collected_files else "\n\tNone"

    # Format SNR file list with brackets
    generated_snr_files = glob.glob(f"{snr_dir}/*.snr*")
    if generated_snr_files:
        snr_status = f"Generated {len(generated_snr_files)} file(s):\n\t[" + " | ".join(os.path.basename(f) for f in generated_snr_files) + "]"
    else:
        snr_status = "No SNR files created."

    # Compose log message
    log_message = (
        f"Timestamp: {timestamp}\n"
        f"Uploaded files: {[f.filename for f in nmea_files]}\n"
        f"{command_str}\n"
        f"Merged files:{merged_file_list}\n"
        f"SNR Status: {snr_status}\n"
        f"Stdout: {snr_output or 'None'}\n"
        f"Errors: {snr_errors or 'None'}"
    )
    write_log(site, log_message)
    cleanup_old_logs()

    # Return response
    return {
        "command": command_str,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
