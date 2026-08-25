# DiagnoCat to Label Studio Converter

This script automates the process of converting **DiagnoCat** dental annotations into a JSON format that **Label Studio** can import directly. It works by using a web crawler to fetch data from your DiagnoCat account for your uploaded images.

---

##  Installation

### 1. Clone the Repository
Open your terminal and run:
```bash
git clone https://github.com/Schlutzkrapfen/Dignocat-to-LabelStudio-Converter.git
cd Dignocat-to-LabelStudio-Converter
```


### 2. Install Dependencies
Install the required Python libraries using the requirements.txt file:
#### On Linux/macOS:


Bash
```bash
# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
# Install the necessary browser (Chromium)
playwright install chromium
```
#### On Windows:
Bash
```bash
# Create a virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
# Install the necessary browser (Chromium)
playwright install chromium
```

## Configuration (Setup)

Before running the script, you must configure how the labels are translated. This is done in the label_mapping.csv file.
### Mapping the CSV

The CSV file contains four columns: `diagnocat_label`, `code`, `label_category`, and `options`.

- **`diagnocat_label`**: The name of the label as it appears in DiagnoCat. You can find these names by clicking on any label within the DiagnoCat interface.
  > **Note:** If you don't want to use a specific label, simply leave the row blank.
<img width="2559" height="1599" alt="image" src="https://github.com/user-attachments/assets/6ffdb6ad-db7d-4f87-b075-b100f6b5ff1c" />
<img width="2559" height="1599" alt="image" src="https://github.com/user-attachments/assets/7e8e23ac-5577-4a60-b380-946be962e363" />
    
- **`code`**: Corresponds to the `value` attribute of your `<Label>` tag in Label Studio.

- **`label_category`**: Corresponds to the `name` attribute of your `<RectangleLabels>` tag in Label Studio.

- **`options`**: Allows you to pass specific modifiers or AI processing flags to a label. Multiple options must be separated by a comma (e.g., `inward,combine`).

#### Available Options

- **`inward`**: Uses all labels except the furthest outer teeth (wisdom teeth).
- **`outward`**: Uses only the furthest outer teeth (wisdom teeth).
- **`combine`**: If two teeth share the same label and are adjacent to each other, it combines them into a single label.
- **`splith`**:  Splits the label into two parts horizontally on each edge with a width of 1.
- **`hole`**: gets the hole theeth instead of just a part of the thoot
- **`height:<float>`**: Multiplier applied to the annotation's height, always growing in the direction of the jaw.
- **`ownjson`**: the task uses its own dedicated JSON file instead of the shared one. 
- **`neighborsconnect`**: Skips saving the label if the bounding boxes of the left and right neighboring teeth already connect/overlap with each other.
- **`ai:<model_name>`**: Uses a secondary AI model to split the label into more parts. See the **AI Models** section below.
##### AI Models

If you want to split or refine a label into smaller parts, you can attach an AI model to it using the `ai:<model_name>` option.

1. **Model Location:** Save your model file inside the `AI-models/` directory (e.g., `AI-models/crown.pth`).
2. **Usage in Options:** Add `ai:` followed by the model filename in the `options` column (e.g., `ai:crown.pth`).
3. **AI Mapping File:** Configure `ai-label.csv` to map the AI outputs.
   - It works identically to `label_mapping.csv`, but without the `options` column.
   - Replace `diagnocat_label` with `ai_label` (the label name predicted by your AI model).

### Example:

If your Label Studio configuration looks like this:
```bash
XML

<RectangleLabels name="metal" toName="image">
  <Label value="Metal-Crown"/>
  <Label value="Metal-Filling"/>
</RectangleLabels>
```

To map the DiagnoCat label "Füllung" to "Metal-Filling", your CSV row should look like this:
| diagnocat_label | code | label_category | options |
| :--- | :--- | :--- | :--- |
| Füllung | Metal-Filling | metal | ai:filling.pth,inward |

## Usage

Once the setup is complete, start the script:
Bash
```bash
python main.py
```

You can optionally pass **ID arguments** to control which items are processed:

| Syntax | Description | Example |
|--------|-------------|---------|
| *(no args)* | Process all items | `python main.py` |
| `N` | Process a single item by index | `python main.py 3` |
| `N+` | Process from index N to the end | `python main.py 5+` |
| `A B` | Process a range from index A to B (inclusive) | `python main.py 2 7` |


A browser window will pop up asking you to Sign In to DiagnoCat.

<img width="2109" height="1371" alt="image" src="https://github.com/user-attachments/assets/1b043b62-92eb-426d-b9d1-38dcbe2560c9" />


After signing in, the script will automatically process the images.

### ⚠️ Important Warnings

 -   Do not move your mouse: The web crawler takes screenshots and uses hover effects to extract data. Having your mouse over the window may interfere with the data collection.

 -   Keep Focus: For best results, keep the automated browser window focused (on top) while it runs.

 -    Keep Zoom at 100%: The program does not check the browser's zoom level. If it's not at 100%, screenshots will be incorrect.
## Output

At the end of the process, the script will generate an output.json file.

You can upload this file directly to your Label Studio project to see your annotated images.
