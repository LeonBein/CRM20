<span style="font-size:200%">Language Influence on Code Style - How learning a new programming language changes the way we code</span>

### A project of the code repository mining seminar of the software architecture group at the Hasso Plattner Institute at the University of Potsdam
---

This is the repository for the "Language Influence on Code Style" project of the  code repository mining seminar SS20 of the software architecture group at the Hasso Plattner Institute at the University of Potsdam.

The project aims at exploring the influence of learning a new programming language on the code style of the old languages. For this, Java code quality (constitution) of Java developers that started learning Javascript or Python is compared to the one of Java developers that didn't.

## Structure of the repository
### Notebooks
Most of the work that has been done in this project can be found in Jupyter notebooks. These are split horizontally by the problems they address. 

A good starting point is the [DataExplorer](DataExplorer.ipynb) notebook. It shows how the project base data is extracted from the GHTorrent dataset. It consists mainly of sql queries for view and table creation and for exploratory questions. The notebook results in views and tables, notably `lb_polyglots` and `lb_controlgroup` which include the groups that are compared in this project. The full data schema for this notebook can be found in [this](docs/Data_Schema_DataExplorer.pdf) diagram.