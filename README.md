# 📊 Automatically generate Excel report with charts (Python)

## ✅ Description:
Python script automatically generates a report from an Excel spreadsheet with sales and builds a graph. 
Can be used for e-commerce, marketing, inventory control and management reports.

## 🔧 Technologies used:
- Python 3
- Pandas
- OpenPyXL
- Matplotlib

## 🚀 Functionality:
- Parsing an Excel file with sales data
- Calculation of totals and averages
- Plotting dynamics
- Saving the finished report to Excel

## 🖥 Example of use:
```bash
python main.py
```

## 🎛 ATEM switcher connection (`atem_connect.py`)

Connects to a Blackmagic ATEM video switcher via [PyATEMMax](https://pypi.org/project/PyATEMMax/), confirms the connection and prints device information (model, protocol version, video mode). Exit with `Ctrl+C` — the script disconnects cleanly.

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run
```bash
python atem_connect.py --ip 192.168.1.240
```

Options:
- `--ip` — IP address of the ATEM device (default `192.168.1.240`)
- `--timeout` — connection timeout in seconds (default `10`)
- `--program-input INPUT` — set the program input and exit
- `--preview-input INPUT` — set the preview input and exit
- `--cut` — perform a cut and exit
- `--auto` — perform an automatic transition and exit
- `--me ME` — mix effect block for one-shot actions and interactive commands (default `0`)
- `--camera CAMERA` — camera number for camera-control actions (`1`-`20`)
- `--iris IRIS` — set iris (`0`-`2048`)
- `--focus FOCUS` — set focus (`0`-`65535`)
- `--auto-focus` — trigger auto-focus
- `--auto-iris` — trigger auto-iris
- `--gain GAIN` — set gain (`512`, `1024`, `2048`, or `4096`)
- `--white-balance KELVIN` — set white balance (`3200`, `4500`, `5000`, `5600`, `6500`, or `7500`)
- `--zoom NORMALIZED` — set normalized zoom (`0.0`-`1.0`)
- `--shutter SECONDS` — set shutter to one of `1/50`, `1/60`, `1/75`, `1/90`, `1/100`, `1/120`, `1/150`, `1/180`, `1/250`, `1/360`, `1/500`, `1/750`, `1/1000`, `1/1450`, or `1/2000`

When no one-shot action is selected, the script starts interactive mode:
- `program INPUT` — set the program input
- `preview INPUT` — set the preview input
- `cut` — perform a cut
- `auto` — perform an automatic transition
- `state` — show the current program and preview inputs
- `camera CAMERA` — show a compact camera state summary
- `iris CAMERA VALUE` — set iris (`0`-`2048`)
- `focus CAMERA VALUE` — set focus (`0`-`65535`)
- `auto-focus CAMERA` — trigger auto-focus
- `auto-iris CAMERA` — trigger auto-iris
- `gain CAMERA VALUE` — set gain (`512`, `1024`, `2048`, or `4096`)
- `white-balance CAMERA KELVIN` — set white balance (`3200`, `4500`, `5000`, `5600`, `6500`, or `7500`)
- `zoom CAMERA VALUE` — set normalized zoom (`0.0`-`1.0`)
- `shutter CAMERA VALUE` — set shutter to one of the listed shutter values
- `help` — show the command list
- `quit` — disconnect and exit

For example, to connect to an ATEM 1 M/E Constellation HD and set camera 3 to program:
```bash
python atem_connect.py --ip 172.16.54.93 --program-input 3
```

For example, to set camera 1 focus and trigger auto-iris:
```bash
python atem_connect.py --ip 172.16.54.93 --camera 1 --focus 30000 --auto-iris
```
