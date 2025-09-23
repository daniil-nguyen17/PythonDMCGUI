#Welcome to to PythonDMCGui
This is a custom solution python GUI that serves to control a Galil machine using DMC code
##Requirements
- GCLib: https://www.galil.com/sw/pub/all/rn/gclib.html
- Conda: https://www.anaconda.com/download/success 
- Kivy: https://kivy.org/doc/stable/gettingstarted/installation.html 
- Python 3.13

##Setup instructions
- Set up conda
    - conda env create -f environment.yml - this is root directory
    - conda activate my_new_environment
- Install GCLib .exe installer - make sure it sets your path for x64 versions
- Run python "PythonDMCGUI\Demo layout\DMCCodeGUI.py"

##Links to resources: 
- DMC Code and Info: https://www.galil.com/learn/sample-dmc-code
- GCLib documentation: https://www.galil.com/sw/pub/all/doc/gclib/html/examples.html 