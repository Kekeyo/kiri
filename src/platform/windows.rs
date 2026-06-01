use crate::model::{RawListenerEntry, RawProcessEntry, RawProcessInfo};
use crate::platform::PlatformError;
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Command;

pub fn get_listening_ports_raw() -> Vec<RawListenerEntry> {
    get_listening_ports_raw_checked().unwrap_or_default()
}

pub fn get_listening_ports_raw_checked() -> Result<Vec<RawListenerEntry>, PlatformError> {
    let script = r#"
$ErrorActionPreference = 'SilentlyContinue'
Get-NetTCPConnection -State Listen | ForEach-Object {
  $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  [PSCustomObject]@{
    LocalPort = $_.LocalPort
    OwningProcess = $_.OwningProcess
    ProcessName = if ($process) { $process.ProcessName } else { "pid-$($_.OwningProcess)" }
  }
} | ConvertTo-Json -Compress
"#;

    let raw = powershell_output(script)?;
    Ok(parse_listener_json(&raw))
}

pub fn get_listener_on_port_raw_checked(
    port: u16,
) -> Result<Option<RawListenerEntry>, PlatformError> {
    let script = format!(
        r#"
$ErrorActionPreference = 'SilentlyContinue'
Get-NetTCPConnection -State Listen -LocalPort {port} | ForEach-Object {{
  $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  [PSCustomObject]@{{
    LocalPort = $_.LocalPort
    OwningProcess = $_.OwningProcess
    ProcessName = if ($process) {{ $process.ProcessName }} else {{ "pid-$($_.OwningProcess)" }}
  }}
}} | ConvertTo-Json -Compress
"#
    );

    let raw = powershell_output(&script)?;
    Ok(parse_listener_json(&raw)
        .into_iter()
        .find(|entry| entry.port == port))
}

pub fn parse_listener_json(raw: &str) -> Vec<RawListenerEntry> {
    let mut entries = Vec::new();

    for value in json_objects(raw) {
        let Some(port) = value
            .get("LocalPort")
            .and_then(serde_json::Value::as_u64)
            .and_then(|port| u16::try_from(port).ok())
        else {
            continue;
        };
        if port == 0 {
            continue;
        }
        let Some(pid) = value
            .get("OwningProcess")
            .and_then(serde_json::Value::as_u64)
            .and_then(|pid| u32::try_from(pid).ok())
        else {
            continue;
        };

        entries.push(RawListenerEntry {
            port,
            pid,
            process_name: value
                .get("ProcessName")
                .and_then(serde_json::Value::as_str)
                .filter(|name| !name.is_empty())
                .unwrap_or("unknown")
                .to_string(),
        });
    }

    entries.sort_by_key(|entry| entry.port);
    entries.dedup_by_key(|entry| entry.port);
    entries
}

pub fn batch_process_info(pids: &[u32]) -> HashMap<u32, RawProcessInfo> {
    if pids.is_empty() {
        return HashMap::new();
    }

    let filter = pids
        .iter()
        .map(|pid| format!("ProcessId = {pid}"))
        .collect::<Vec<String>>()
        .join(" OR ");
    let escaped_filter = filter.replace('\'', "''");
    let script = format!(
        r#"
$ErrorActionPreference = 'SilentlyContinue'
$cpuByPid = @{{}}
Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | ForEach-Object {{
  if ($_.IDProcess -gt 0) {{
    $cpuByPid[[uint32]$_.IDProcess] = [double]$_.PercentProcessorTime
  }}
}}
$culture = [Globalization.CultureInfo]::InvariantCulture
Get-CimInstance Win32_Process -Filter '{escaped_filter}' | ForEach-Object {{
  $process = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
  $created = $_.CreationDate
  $lstart = if ($created) {{ $created.ToString('MMM d HH:mm:ss yyyy', $culture) }} else {{ '' }}
  [PSCustomObject]@{{
    ProcessId = $_.ProcessId
    ParentProcessId = $_.ParentProcessId
    Status = if ($process) {{ $process.Responding }} else {{ $true }}
    CpuPercent = if ($cpuByPid.ContainsKey([uint32]$_.ProcessId)) {{ $cpuByPid[[uint32]$_.ProcessId] }} else {{ 0 }}
    WorkingSet64 = if ($process) {{ $process.WorkingSet64 }} else {{ 0 }}
    LStart = $lstart
    CommandLine = if ($_.CommandLine) {{ $_.CommandLine }} elseif ($_.ExecutablePath) {{ $_.ExecutablePath }} else {{ $_.Name }}
  }}
}} | ConvertTo-Json -Compress
"#
    );

    let Ok(raw) = powershell_output(&script) else {
        return HashMap::new();
    };
    parse_process_json(&raw)
}

pub fn parse_process_json(raw: &str) -> HashMap<u32, RawProcessInfo> {
    let mut processes = HashMap::new();

    for value in json_objects(raw) {
        let Some(pid) = value
            .get("ProcessId")
            .and_then(serde_json::Value::as_u64)
            .and_then(|pid| u32::try_from(pid).ok())
        else {
            continue;
        };
        let Some(ppid) = value
            .get("ParentProcessId")
            .and_then(serde_json::Value::as_u64)
            .and_then(|pid| u32::try_from(pid).ok())
        else {
            continue;
        };

        let rss_kb = value
            .get("WorkingSet64")
            .and_then(serde_json::Value::as_u64)
            .map(|bytes| bytes / 1024)
            .unwrap_or_default();
        let cpu = value
            .get("CpuPercent")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or_default();
        let lstart = value
            .get("LStart")
            .and_then(serde_json::Value::as_str)
            .unwrap_or_default()
            .to_string();
        let command = value
            .get("CommandLine")
            .and_then(serde_json::Value::as_str)
            .unwrap_or_default()
            .to_string();
        if lstart.is_empty() || command.is_empty() {
            continue;
        }

        processes.insert(
            pid,
            RawProcessInfo {
                ppid,
                stat: "R".to_string(),
                cpu,
                rss_kb,
                lstart,
                command,
            },
        );
    }

    processes
}

pub fn batch_cwd(pids: &[u32]) -> HashMap<u32, PathBuf> {
    if pids.is_empty() {
        return HashMap::new();
    }

    let filter = pids
        .iter()
        .map(|pid| format!("ProcessId = {pid}"))
        .collect::<Vec<String>>()
        .join(" OR ");
    let escaped_filter = filter.replace('\'', "''");
    let script = format!(
        r#"
$ErrorActionPreference = 'SilentlyContinue'
Get-CimInstance Win32_Process -Filter '{escaped_filter}' | ForEach-Object {{
  $directory = if ($_.ExecutablePath) {{ Split-Path -Parent $_.ExecutablePath }} else {{ '' }}
  [PSCustomObject]@{{
    ProcessId = $_.ProcessId
    Directory = $directory
  }}
}} | ConvertTo-Json -Compress
"#
    );

    let Ok(raw) = powershell_output(&script) else {
        return HashMap::new();
    };
    parse_cwd_json(&raw)
}

pub fn get_all_processes_raw() -> Vec<RawProcessEntry> {
    get_all_processes_raw_checked().unwrap_or_default()
}

pub fn get_all_processes_raw_checked() -> Result<Vec<RawProcessEntry>, PlatformError> {
    let script = r#"
$ErrorActionPreference = 'SilentlyContinue'
$culture = [Globalization.CultureInfo]::InvariantCulture
$totalMemory = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
$cpuByPid = @{}
Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | ForEach-Object {
  if ($_.IDProcess -gt 0) {
    $cpuByPid[[uint32]$_.IDProcess] = [double]$_.PercentProcessorTime
  }
}
Get-CimInstance Win32_Process | ForEach-Object {
  $process = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
  $workingSet = if ($process) { $process.WorkingSet64 } else { 0 }
  $created = $_.CreationDate
  $lstart = if ($created) { $created.ToString('MMM d HH:mm:ss yyyy', $culture) } else { '' }
  [PSCustomObject]@{
    ProcessId = $_.ProcessId
    Name = $_.Name
    CpuPercent = if ($cpuByPid.ContainsKey([uint32]$_.ProcessId)) { $cpuByPid[[uint32]$_.ProcessId] } else { 0 }
    MemoryPercent = if ($totalMemory -gt 0) { [Math]::Round(($workingSet / $totalMemory) * 100, 2) } else { 0 }
    WorkingSet64 = $workingSet
    LStart = $lstart
    CommandLine = if ($_.CommandLine) { $_.CommandLine } elseif ($_.ExecutablePath) { $_.ExecutablePath } else { $_.Name }
  }
} | ConvertTo-Json -Compress
"#;

    let raw = powershell_output(script)?;
    Ok(parse_all_process_json(&raw, std::process::id()))
}

pub fn parse_all_process_json(raw: &str, current_pid: u32) -> Vec<RawProcessEntry> {
    let mut entries = Vec::new();

    for value in json_objects(raw) {
        let Some(pid) = value
            .get("ProcessId")
            .and_then(serde_json::Value::as_u64)
            .and_then(|pid| u32::try_from(pid).ok())
        else {
            continue;
        };
        if pid <= 4 || pid == current_pid {
            continue;
        }

        let command = value
            .get("CommandLine")
            .and_then(serde_json::Value::as_str)
            .unwrap_or_default()
            .to_string();
        let lstart = value
            .get("LStart")
            .and_then(serde_json::Value::as_str)
            .unwrap_or_default()
            .to_string();
        if command.is_empty() || lstart.is_empty() {
            continue;
        }

        entries.push(RawProcessEntry {
            pid,
            process_name: value
                .get("Name")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("unknown")
                .trim_end_matches(".exe")
                .to_string(),
            cpu: value
                .get("CpuPercent")
                .and_then(serde_json::Value::as_f64)
                .unwrap_or_default(),
            mem_percent: value
                .get("MemoryPercent")
                .and_then(serde_json::Value::as_f64)
                .unwrap_or_default(),
            rss_kb: value
                .get("WorkingSet64")
                .and_then(serde_json::Value::as_u64)
                .map(|bytes| bytes / 1024)
                .unwrap_or_default(),
            lstart,
            command,
        });
    }

    entries
}

fn powershell_output(script: &str) -> Result<String, PlatformError> {
    let output = Command::new("powershell")
        .args(["-NoProfile", "-NonInteractive", "-Command", script])
        .output()
        .map_err(|error| PlatformError::new("powershell", error.to_string()))?;

    if !output.status.success() {
        return Err(PlatformError::new(
            "powershell",
            command_failure_message(&output.stderr, output.status.code()),
        ));
    }

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

fn command_failure_message(stderr: &[u8], code: Option<i32>) -> String {
    let stderr = String::from_utf8_lossy(stderr).trim().to_string();
    if stderr.is_empty() {
        format!(
            "exit status {}",
            code.map_or_else(|| "unknown".to_string(), |code| code.to_string())
        )
    } else {
        stderr
    }
}

pub fn parse_cwd_json(raw: &str) -> HashMap<u32, PathBuf> {
    let mut cwd = HashMap::new();

    for value in json_objects(raw) {
        let Some(pid) = value
            .get("ProcessId")
            .and_then(serde_json::Value::as_u64)
            .and_then(|pid| u32::try_from(pid).ok())
        else {
            continue;
        };
        let Some(directory) = value
            .get("Directory")
            .and_then(serde_json::Value::as_str)
            .filter(|directory| !directory.is_empty())
        else {
            continue;
        };
        cwd.insert(pid, PathBuf::from(directory));
    }

    cwd
}

fn json_objects(raw: &str) -> Vec<serde_json::Value> {
    let Ok(value) = serde_json::from_str::<serde_json::Value>(raw.trim()) else {
        return Vec::new();
    };

    match value {
        serde_json::Value::Array(values) => values,
        serde_json::Value::Object(_) => vec![value],
        _ => Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_listener_json_array_and_single_object() {
        let raw = r#"
[
  {"LocalPort":3000,"OwningProcess":42872,"ProcessName":"node"},
  {"LocalPort":9222,"OwningProcess":19382,"ProcessName":"chrome"}
]
"#;

        let entries = parse_listener_json(raw);

        assert_eq!(
            entries,
            vec![
                RawListenerEntry {
                    port: 3000,
                    pid: 42872,
                    process_name: "node".to_string(),
                },
                RawListenerEntry {
                    port: 9222,
                    pid: 19382,
                    process_name: "chrome".to_string(),
                },
            ]
        );

        let single = parse_listener_json(
            r#"{"LocalPort":5432,"OwningProcess":1000,"ProcessName":"postgres"}"#,
        );
        assert_eq!(single.len(), 1);
        assert_eq!(single[0].port, 5432);
    }

    #[test]
    fn parses_process_json() {
        let raw = r#"
{"ProcessId":42872,"ParentProcessId":1,"CpuPercent":3.5,"WorkingSet64":10485760,"LStart":"May 20 14:12:44 2026","CommandLine":"node C:\\repo\\app\\server.js"}
"#;

        let processes = parse_process_json(raw);
        let process = processes.get(&42872).expect("process should parse");

        assert_eq!(process.ppid, 1);
        assert_eq!(process.cpu, 3.5);
        assert_eq!(process.rss_kb, 10240);
        assert_eq!(process.lstart, "May 20 14:12:44 2026");
        assert_eq!(process.command, "node C:\\repo\\app\\server.js");
    }

    #[test]
    fn parses_cwd_json_from_executable_directory() {
        let raw = r#"
[
  {"ProcessId":42872,"Directory":"C:\\repo\\app"},
  {"ProcessId":42873,"Directory":""}
]
"#;

        let cwd = parse_cwd_json(raw);

        assert_eq!(cwd.get(&42872), Some(&PathBuf::from("C:\\repo\\app")));
        assert!(!cwd.contains_key(&42873));
    }

    #[test]
    fn parses_all_process_json() {
        let raw = r#"
[
  {"ProcessId":4,"Name":"System","CpuPercent":0,"MemoryPercent":0,"WorkingSet64":1,"LStart":"May 20 14:12:44 2026","CommandLine":"System"},
  {"ProcessId":42872,"Name":"node.exe","CpuPercent":2.5,"MemoryPercent":1.5,"WorkingSet64":10485760,"LStart":"May 20 14:12:44 2026","CommandLine":"node C:\\repo\\app\\server.js"}
]
"#;

        let entries = parse_all_process_json(raw, 99999);

        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].pid, 42872);
        assert_eq!(entries[0].process_name, "node");
        assert_eq!(entries[0].cpu, 2.5);
        assert_eq!(entries[0].mem_percent, 1.5);
        assert_eq!(entries[0].rss_kb, 10240);
    }
}
