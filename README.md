##### A project of the code repository mining seminar of the software architecture group at the Hasso Plattner Institute at the University of Potsdam
# Language Influence on Code Style - How learning a new programming language changes the way we code 

This is the repository for the "Language Influence on Code Style" project of the  code repository mining seminar SS20 of the software architecture group at the Hasso Plattner Institute at the University of Potsdam.

The project aims at exploring the influence of learning a new programming language on the code style of the old languages. For this, Java code quality (constitution) of Java developers that started learning Javascript or Python is compared to the one of Java developers that didn't.

## Structure of the repository
Most of the work that has been done in this project can be found in Jupyter notebooks. These are split horizontally by the problems they address. 

A good starting point is the [DataExplorer](DataExplorer.ipynb) notebook. It shows how the project base data is extracted from the GHTorrent dataset. It consists mainly of sql queries for view and table creation and for exploratory questions. The notebook results in views and tables, notably `lb_polyglots` and `lb_controlgroup` which include the groups that are compared in this project. The full data schema for this notebook can be found in [this](docs/Data_Schema_DataExplorer.pdf) diagram.

The data from the data explorer is taken for the [RepoAnalysis](RepoAnalysis.ipynb) notebook. This notebook describes the three big analysis runs that lead to the project commit metric data and the improvements that have been done between these runs. It brings together results from several sub projects: The two experiment groups from the data explorer are used to determine a set of repositories that should be analyzed. Downloading and curating the repositories is done by the [repoLibrarian](repoLibrarian.py) module. Information on the development of this module can be found in the [RepoLibrarian](RepoLibrarian.ipynb) notebook. The repositories are then analyzed with the help of the [repoAnalysis](repoAnalysis.py) module. The development history of this module can be found in the [RepoAnalysis_Historical](RepoAnalysis_Historical.ipynb) notebook. Additionally, insights during the analysis runs have been incorporated into the module and documented in the [RepoAnalysis](RepoAnalysis.ipynb) notebook.

The resulting analysis data for each run is combined with the user data from the data explorer in the Results_Iteration notebooks [#1](Results_Iteration#1.ipynb), [#2](Results_Iteration#2.ipynb), and [#3](Results_Iteration#3.ipynb) respectively. These notebooks describe the evaluations of the analysis runs, with the first resulting in many insights on the methodolohy, the second showing the feasability of the realization of these insights. The third run then uses the now proven technology, scales up the input data, and evaluates a bit more in depth.

The [UserAnalysis](UserAnalysis.ipynb) notebook is a small sideproject analyzing the intermediat experiment groups (especially the polyglots) from the data explorer.


## Resulting Artifacts
Besides the Notebooks, further artifacts can be explored:
### Tables
Note: All resulting tables are in schema named `crm20`.<br>
Aggregation of user data in the [DataExplorer](DataExplorer.ipynb) mainly lead to the creation of the `lb_polyglots` and `lb_controlgroup` tables, which contain information on java developers that have been classified as (not) learning Python or Javascript as secondary language.

Analysis of selected repositories in the [RepoAnalysis](RepoAnalysis.ipynb) lead to three result sets that can be found in the tables `lb_results1`, `lb_results2`, and `lb_results3`, the evaluation of which can be found in the Results_Iteration notebooks [#1](Results_Iteration#1.ipynb), [#2](Results_Iteration#2.ipynb), and [#3](Results_Iteration#3.ipynb).



## Setup
The technical requirements can be installed in a Python 3 environment with:
```
pip install -r requirements.txt
```
Jupyter lab must be installed to explore the notebooks of this project. Additionally, the Jupyter table of contents extension is recommended because it numbers all headings and allows quick navigation through the notebooks:
```
jupyter labextension install @jupyterlab/toc
```

The data is based on a fork of the [GHTorrent](https://ghtorrent.org/) database. The `engine` variable of the [dbUtils](dbUtils.py) module must be adapted to a valid connection.
