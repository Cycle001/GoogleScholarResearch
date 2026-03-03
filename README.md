## Introduction
Automatically search papers and save cleaned search results

## Usage
create config.json like this:
``` json
{
    "google": {
        "user_date_dir": "PATH\\TO\\Google\\Chrome\\Driver Auto Data"
    },
    "edge": {
        "user_date_dir": "PATH\\TO\\Microsoft\\Edge\\Driver Auto Data"
    },
    "save_dir": "PATH\\TO\\SAVE"
}
```
run command in terminal
```
python GoogleScholarResearch.py
```
## Dependency
selenium
BeautifulSoup
pandas
