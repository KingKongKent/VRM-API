# Deploy Victron VRM API v1.5.7 to Local Home Assistant
# Target: 192.168.11.115

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying Victron VRM API v1.5.7" -ForegroundColor Cyan
Write-Host "Target: 192.168.11.115" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$HA_HOST = "192.168.11.115"
$HA_USER = "root"  # Change if using different user
$SOURCE_PATH = "custom_components\victron_vrm_api\"
$DEST_PATH = "/config/custom_components/victron_vrm_api/"

Write-Host "Files to deploy:" -ForegroundColor Yellow
Write-Host "  - sensor.py (with diagnostics endpoint support)" -ForegroundColor Green
Write-Host "  - manifest.json (v1.5.7)" -ForegroundColor Green
Write-Host ""

Write-Host "Deployment method options:" -ForegroundColor Yellow
Write-Host "  1. SCP (requires SSH access)" -ForegroundColor White
Write-Host "  2. Manual copy via File Share" -ForegroundColor White
Write-Host "  3. VS Code Remote SSH" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Select method (1-3) or press Enter to show commands only"

switch ($choice) {
    "1" {
        Write-Host "`nUsing SCP method..." -ForegroundColor Green
        Write-Host "Command that will be executed:" -ForegroundColor Yellow
        Write-Host "scp custom_components\victron_vrm_api\sensor.py ${HA_USER}@${HA_HOST}:${DEST_PATH}" -ForegroundColor Cyan
        Write-Host "scp custom_components\victron_vrm_api\manifest.json ${HA_USER}@${HA_HOST}:${DEST_PATH}" -ForegroundColor Cyan
        Write-Host ""
        
        $confirm = Read-Host "Execute SCP commands? (y/n)"
        if ($confirm -eq "y") {
            scp "$SOURCE_PATH\sensor.py" "${HA_USER}@${HA_HOST}:${DEST_PATH}"
            scp "$SOURCE_PATH\manifest.json" "${HA_USER}@${HA_HOST}:${DEST_PATH}"
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "`n✓ Files deployed successfully!" -ForegroundColor Green
            } else {
                Write-Host "`n✗ Deployment failed. Check SSH access." -ForegroundColor Red
                exit 1
            }
        }
    }
    "2" {
        Write-Host "`nManual copy method:" -ForegroundColor Green
        Write-Host "1. Open File Explorer" -ForegroundColor White
        Write-Host "2. Navigate to: \\$HA_HOST\config\custom_components\victron_vrm_api\" -ForegroundColor Cyan
        Write-Host "3. Copy these files:" -ForegroundColor White
        Write-Host "   - $SOURCE_PATH\sensor.py" -ForegroundColor Yellow
        Write-Host "   - $SOURCE_PATH\manifest.json" -ForegroundColor Yellow
        Write-Host ""
        Read-Host "Press Enter when files are copied"
    }
    "3" {
        Write-Host "`nVS Code Remote SSH method:" -ForegroundColor Green
        Write-Host "1. Open VS Code" -ForegroundColor White
        Write-Host "2. Connect to: ${HA_USER}@${HA_HOST}" -ForegroundColor Cyan
        Write-Host "3. Navigate to: $DEST_PATH" -ForegroundColor Cyan
        Write-Host "4. Upload sensor.py and manifest.json" -ForegroundColor White
        Write-Host ""
        Read-Host "Press Enter when files are uploaded"
    }
    default {
        Write-Host "`nSCP Commands:" -ForegroundColor Yellow
        Write-Host "scp custom_components\victron_vrm_api\sensor.py ${HA_USER}@${HA_HOST}:${DEST_PATH}" -ForegroundColor Cyan
        Write-Host "scp custom_components\victron_vrm_api\manifest.json ${HA_USER}@${HA_HOST}:${DEST_PATH}" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "File Share Path:" -ForegroundColor Yellow
        Write-Host "\\$HA_HOST\config\custom_components\victron_vrm_api\" -ForegroundColor Cyan
        Write-Host ""
        exit 0
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Restart Home Assistant" -ForegroundColor Yellow
Write-Host "   Settings → System → Restart" -ForegroundColor White
Write-Host ""
Write-Host "2. Check for errors" -ForegroundColor Yellow
Write-Host "   Settings → System → Logs" -ForegroundColor White
Write-Host ""
Write-Host "3. Verify new sensors (after restart)" -ForegroundColor Yellow
Write-Host "   Developer Tools → States → Filter 'vrm'" -ForegroundColor White
Write-Host ""
Write-Host "Expected new sensors per device:" -ForegroundColor Green
Write-Host "  - Battery 288: +7 sensors" -ForegroundColor White
Write-Host "  - Battery 291: +7 sensors" -ForegroundColor White
Write-Host "  - Solar Charger 289: +5 sensors" -ForegroundColor White
Write-Host "  - Solar Charger 290: +5 sensors" -ForegroundColor White
Write-Host "  - MultiPlus 291: +4 sensors" -ForegroundColor White
Write-Host ""
Write-Host "Total: +28 new diagnostic sensors" -ForegroundColor Green
Write-Host ""
