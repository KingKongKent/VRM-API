# Deploy to Local Home Assistant (192.168.11.115)

## Files Updated for v1.5.7:
- `sensor.py` - Added diagnostics endpoint support with 18 new sensors
- `manifest.json` - Version bumped to 1.5.7

## New Sensors Added (from diagnostics endpoint):

### Battery Diagnostics (7 sensors per battery):
- Deepest discharge (Ah)
- Last discharge (Ah)
- Average discharge (Ah)
- Total Ah drawn
- Minimum voltage
- Maximum voltage
- Time since last full charge

### Solar Charger Diagnostics (5 sensors per charger):
- PV Voltage (alternate source)
- Max Power Yesterday
- Error Code
- PV Power
- MPPT State

### MultiPlus Diagnostics (4 sensors):
- Active Input Current Limit
- VE.Bus Error
- Low Battery warning
- Charge State

## Total New Sensors:
- Battery 288: +7 sensors
- Battery 291: +7 sensors  
- Solar Charger 289: +5 sensors
- Solar Charger 290: +5 sensors
- MultiPlus 291: +4 sensors
**Total: +28 sensors**

## Deployment Steps:

### Option 1: SCP/SFTP Upload
```powershell
# Copy entire custom_components folder to Home Assistant
scp -r custom_components/victron_vrm_api root@192.168.11.115:/config/custom_components/
```

### Option 2: VS Code Remote SSH
1. Open VS Code
2. Connect to SSH: root@192.168.11.115
3. Navigate to /config/custom_components/victron_vrm_api/
4. Copy sensor.py and manifest.json

### Option 3: File Share (if configured)
1. Access \\\\192.168.11.115\\config
2. Navigate to custom_components\\victron_vrm_api\\
3. Copy sensor.py and manifest.json

## After Deployment:

1. **Restart Home Assistant**:
   - Go to Settings → System → Restart
   - Or use Developer Tools → YAML → Restart

2. **Check Integration**:
   - Go to Settings → Devices & Services
   - Find "Victron VRM API"
   - Verify no errors

3. **Verify New Sensors**:
   - Battery 288 should show ~25 entities (was 18)
   - Battery 291 should show ~24 entities (was 17)
   - Solar Charger 289 should show ~11 entities (was 6)
   - Solar Charger 290 should show ~11 entities (was 6)
   - MultiPlus 291 should show ~40 entities (was 36)

4. **Wait for Data**:
   - Diagnostics coordinator polls every 60 seconds (same as overallstats)
   - New sensors will appear as data becomes available

## Testing:

Check if new sensors appear:
- Developer Tools → States
- Filter by "vrm"
- Look for entities with "diag" in the ID

Expected new entity examples:
- `sensor.vrm_battery_288_deepest_discharge`
- `sensor.vrm_battery_288_minimum_voltage`
- `sensor.vrm_solar_charger_289_pv_power`
- `sensor.vrm_solar_charger_289_mppt_state`
- `sensor.vrm_multiplus_291_active_input_current_limit`

## Rollback (if issues):

1. Copy back old files from `histrory file/` folder
2. Restart Home Assistant
3. Or disable integration and re-enable

## Notes:

- Diagnostics endpoint provides historical stats not available in widgets
- All new sensors have smart creation - only appear when data exists
- Coordinates with existing sensors - no duplicates
- Same scan interval as overall stats (60 seconds)
