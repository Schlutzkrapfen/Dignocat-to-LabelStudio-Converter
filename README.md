# DiagnoCat to Label Studio Converter

This script automates the process of converting **DiagnoCat** dental annotations into a JSON format that **Label Studio** can import directly. It works by using a web crawler to fetch data from your DiagnoCat account for your uploaded images.

---

##  Installation

### 1. Clone the Repository
Open your terminal and run:
```bash
git clone [https://github.com/Schlutzkrapfen/Dignocat-to-LabelStudio-Converter.git](https://github.com/Schlutzkrapfen/Dignocat-to-LabelStudio-Converter.git)
cd Dignocat-to-LabelStudio-Converter
```


### 2. Install Dependencies

Install the required Python libraries using the requirements.txt file:
Bash
```bash
pip install -r requirements.txt
```

## Configuration (Setup)

Before running the script, you must configure how the labels are translated. This is done in the label_mapping.csv file.
###Mapping the CSV

The CSV file contains three columns: diagnocat_label, code, and label_category.

- diagnocat_label: This is the name of the label as it appears in DiagnoCat. You can find these names by clicking on any label within the DiagnoCat interface.
   - Note: If you don't want to use a specific label, simply leave the row blank.
<img width="2559" height="1599" alt="image" src="https://github.com/user-attachments/assets/6ffdb6ad-db7d-4f87-b075-b100f6b5ff1c" />
<img width="2559" height="1599" alt="image" src="https://github.com/user-attachments/assets/7e8e23ac-5577-4a60-b380-946be962e363" />
    
- code: This corresponds to the Label value in your Label Studio configuration.

- label_category: This corresponds to the name attribute of your <RectangleLabels> tag in Label Studio.

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
| diagnocat_label | code | label_category |
| :--- | :--- | :--- |
| Füllung | Metal-Filling | metal |

## Usage

Once the setup is complete, start the script:
Bash
```bash
    python main.py
```
A browser window will pop up asking you to Sign In to DiagnoCat.

<img width="2109" height="1371" alt="image" src="https://github.com/user-attachments/assets/1b043b62-92eb-426d-b9d1-38dcbe2560c9" />


After signing in, the script will automatically process the images.

### ⚠️ Important Warnings

 -   Do not move your mouse: The web crawler takes screenshots and uses hover effects to extract data. Having your mouse over the window may interfere with the data collection.

 -   Keep Focus: For best results, keep the automated browser window focused (on top) while it runs.
## Output

At the end of the process, the script will generate an output.json file.

You can upload this file directly to your Label Studio project to see your annotated images.




