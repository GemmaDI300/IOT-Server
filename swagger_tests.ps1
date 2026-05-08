# Script de pruebas Swagger API - IoT Server
Write-Host "======================================"
Write-Host "PRUEBAS DE SEGURIDAD Y FUNCIONALIDAD"
Write-Host "IoT Server API - Swagger UI Tests"
Write-Host "Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "======================================"

$results = @{
    total = 0
    passed = 0
    failed = 0
    vulnerable = 0
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Uri,
        [string]$Method = "GET",
        [hashtable]$Body = $null,
        [hashtable]$Headers = @{},
        [int]$ExpectedStatus = 200,
        [string]$TestType = "FUNCTIONAL"
    )
    
    $results.total++
    Write-Host "`n[$TestType] $Name"
    
    try {
        $params = @{
            Uri = $Uri
            Method = $Method
            UseBasicParsing = $true
            TimeoutSec = 10
        }
        
        if ($Headers.Count -gt 0) {
            $params.Headers = $Headers
        }
        
        if ($Body -ne $null) {
            $params.Body = ($Body | ConvertTo-Json)
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-WebRequest @params
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host "  ✅ PASSED - Status: $($response.StatusCode)"
            $results.passed++
            return $true
        } else {
            Write-Host "  ⚠️ UNEXPECTED - Expected: $ExpectedStatus, Got: $($response.StatusCode)"
            $results.failed++
            return $false
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq $ExpectedStatus) {
            Write-Host "  ✅ PASSED - Status: $statusCode (expected error)"
            $results.passed++
            return $true
        } elseif ($TestType -eq "SECURITY" -and $statusCode -ne 200) {
            Write-Host "  ✅ BLOCKED - Status: $statusCode (attack prevented)"
            $results.passed++
            return $true
        } else {
            Write-Host "  ❌ FAILED - Status: $statusCode, Error: $($_.Exception.Message)"
            if ($TestType -eq "SECURITY") {
                Write-Host "  🚨 VULNERABLE - Attack not properly blocked!"
                $results.vulnerable++
            }
            $results.failed++
            return $false
        }
    }
}

# ===== PRUEBAS DE AUTENTICACIÓN =====
Write-Host "`n`n===== AUTENTICACIÓN ====="

Test-Endpoint -Name "Login válido" `
    -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -Body @{email="admin@test.com"; password="pass123"} `
    -ExpectedStatus 200 `
    -TestType "FUNCTIONAL"

Test-Endpoint -Name "Login - credenciales inválidas" `
    -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -Body @{email="wrong@test.com"; password="wrongpass"} `
    -ExpectedStatus 401 `
    -TestType "FUNCTIONAL"

Test-Endpoint -Name "Login - SQL Injection email" `
    -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -Body @{email="admin' OR '1'='1"; password="x"} `
    -ExpectedStatus 401 `
    -TestType "SECURITY"

Test-Endpoint -Name "Login - XSS en email" `
    -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -Body @{email="<script>alert('XSS')</script>"; password="x"} `
    -ExpectedStatus 401 `
    -TestType "SECURITY"

# ===== RESUMEN =====
Write-Host "`n`n======================================"
Write-Host "RESUMEN DE PRUEBAS"
Write-Host "======================================"
Write-Host "Total ejecutadas: $($results.total)"
Write-Host "✅ Aprobadas: $($results.passed)"
Write-Host "❌ Fallidas: $($results.failed)"
Write-Host "🚨 Vulnerabilidades: $($results.vulnerable)"
Write-Host "======================================"
