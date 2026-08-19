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

When no one-shot action is selected, the script starts interactive mode:
- `program INPUT` — set the program input
- `preview INPUT` — set the preview input
- `cut` — perform a cut
- `auto` — perform an automatic transition
- `state` — show the current program and preview inputs
- `help` — show the command list
- `quit` — disconnect and exit

For example, to connect to an ATEM 1 M/E Constellation HD and set camera 3 to program:
```bash
python atem_connect.py --ip 172.16.54.93 --program-input 3
```
