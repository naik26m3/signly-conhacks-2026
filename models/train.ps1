# Run the letter classifier training
$venv = Join-Path $PSScriptRoot ".venv_directml"
$python = Join-Path $venv "Scripts\python.exe"

# Convert notebook to script then run
& $python -m jupyter nbconvert --to script "$PSScriptRoot\letterClassifier.ipynb" --output-dir $PSScriptRoot
& $python "$PSScriptRoot\letterClassifier.py"
