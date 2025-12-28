$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$global:PSNativeCommandUseErrorActionPreference = $true

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][scriptblock]$ScriptBlock
  )
  Write-Host ""
  Write-Host "==> $Name"
  $global:LASTEXITCODE = 0
  & $ScriptBlock
  if ($LASTEXITCODE -ne 0) {
    throw "Step failed: $Name (exit $LASTEXITCODE)"
  }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
  Invoke-Step -Name "Contracts: validate examples" -ScriptBlock {
    node contracts/validate-contracts.mjs
  }

  Invoke-Step -Name "Python: engine tests" -ScriptBlock {
    Push-Location python/packages/engine
    try {
      uv run pytest
    } finally {
      Pop-Location
    }
  }

  Invoke-Step -Name "Python: API tests" -ScriptBlock {
    Push-Location python/apps/api
    try {
      uv run pytest
    } finally {
      Pop-Location
    }
  }

  Invoke-Step -Name "Python: arena tests" -ScriptBlock {
    Push-Location python/packages/arena
    try {
      uv run pytest
    } finally {
      Pop-Location
    }
  }

  Invoke-Step -Name "Frontend: build" -ScriptBlock {
    Push-Location frontend
    try {
      yarn build
    } finally {
      Pop-Location
    }
  }

  Write-Host ""
  Write-Host "All checks passed."
} finally {
  Pop-Location
}
