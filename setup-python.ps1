$ErrorActionPreference = "Stop"
Write-Host "Downloading Python embeddable..."
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -OutFile "python-embed.zip"
Write-Host "Extracting..."
Expand-Archive -Path "python-embed.zip" -DestinationPath "python-local" -Force
Write-Host "Configuring for pip..."
$pthPath = "python-local\python311._pth"
(Get-Content $pthPath) -replace '#import site', 'import site' | Set-Content $pthPath
Write-Host "Downloading get-pip.py..."
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "python-local\get-pip.py"
Write-Host "Installing pip..."
.\python-local\python.exe .\python-local\get-pip.py
Write-Host "Installing requirements..."
.\python-local\python.exe -m pip install -r requirements.txt
Write-Host "Setup complete."
