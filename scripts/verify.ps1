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

function Assert-Command {
  param(
    [Parameter(Mandatory = $true)][string]$Name
  )
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $Name"
  }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
  Invoke-Step -Name "Tooling: verify prerequisites" -ScriptBlock {
    Assert-Command -Name "node"
    Assert-Command -Name "uv"
    Assert-Command -Name "yarn"
  }

  Invoke-Step -Name "Contracts: validate examples" -ScriptBlock {
    node contracts/validate-contracts.mjs
  }

  Invoke-Step -Name "Python: lint (ruff)" -ScriptBlock {
    Push-Location python
    try {
      uv run ruff check .
    } finally {
      Pop-Location
    }
  }

  Invoke-Step -Name "Python: typecheck (mypy)" -ScriptBlock {
    Push-Location python
    try {
      uv run mypy .
    } finally {
      Pop-Location
    }
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

  Invoke-Step -Name "Python: telemetry tests" -ScriptBlock {
    Push-Location python/packages/telemetry
    try {
      uv run pytest
    } finally {
      Pop-Location
    }
  }

  Invoke-Step -Name "Frontend: lint" -ScriptBlock {
    Push-Location frontend
    try {
      yarn lint
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
