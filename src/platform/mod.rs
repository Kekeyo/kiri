#[cfg(target_os = "macos")]
pub mod darwin;

#[cfg(target_os = "linux")]
pub mod linux;

#[cfg(target_os = "windows")]
pub mod windows;

use crate::model::{RawListenerEntry, RawProcessEntry, RawProcessInfo};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlatformError {
    pub command: String,
    pub message: String,
}

impl PlatformError {
    pub fn new(command: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            command: command.into(),
            message: message.into(),
        }
    }

    pub fn render_warning(&self) -> String {
        format!("Kiri warning: {} failed: {}", self.command, self.message)
    }
}

pub fn get_listening_ports_raw() -> Vec<RawListenerEntry> {
    get_listening_ports_raw_checked().unwrap_or_default()
}

pub fn get_listening_ports_raw_checked() -> Result<Vec<RawListenerEntry>, PlatformError> {
    platform_get_listening_ports_raw_checked()
}

pub fn get_listener_on_port_raw(port: u16) -> Option<RawListenerEntry> {
    get_listener_on_port_raw_checked(port).ok().flatten()
}

pub fn get_listener_on_port_raw_checked(
    port: u16,
) -> Result<Option<RawListenerEntry>, PlatformError> {
    platform_get_listener_on_port_raw_checked(port)
}

pub fn batch_process_info(pids: &[u32]) -> HashMap<u32, RawProcessInfo> {
    platform_batch_process_info(pids)
}

pub fn batch_cwd(pids: &[u32]) -> HashMap<u32, PathBuf> {
    platform_batch_cwd(pids)
}

pub fn get_all_processes_raw() -> Vec<RawProcessEntry> {
    get_all_processes_raw_checked().unwrap_or_default()
}

pub fn get_all_processes_raw_checked() -> Result<Vec<RawProcessEntry>, PlatformError> {
    platform_get_all_processes_raw_checked()
}

#[cfg(target_os = "macos")]
fn platform_get_listening_ports_raw_checked() -> Result<Vec<RawListenerEntry>, PlatformError> {
    darwin::get_listening_ports_raw_checked()
}

#[cfg(target_os = "macos")]
fn platform_get_listener_on_port_raw_checked(
    port: u16,
) -> Result<Option<RawListenerEntry>, PlatformError> {
    darwin::get_listener_on_port_raw_checked(port)
}

#[cfg(target_os = "macos")]
fn platform_batch_process_info(pids: &[u32]) -> HashMap<u32, RawProcessInfo> {
    darwin::batch_process_info(pids)
}

#[cfg(target_os = "macos")]
fn platform_batch_cwd(pids: &[u32]) -> HashMap<u32, PathBuf> {
    darwin::batch_cwd(pids)
}

#[cfg(target_os = "macos")]
fn platform_get_all_processes_raw_checked() -> Result<Vec<RawProcessEntry>, PlatformError> {
    darwin::get_all_processes_raw_checked()
}

#[cfg(target_os = "linux")]
fn platform_get_listening_ports_raw_checked() -> Result<Vec<RawListenerEntry>, PlatformError> {
    linux::get_listening_ports_raw_checked()
}

#[cfg(target_os = "linux")]
fn platform_get_listener_on_port_raw_checked(
    port: u16,
) -> Result<Option<RawListenerEntry>, PlatformError> {
    linux::get_listener_on_port_raw_checked(port)
}

#[cfg(target_os = "linux")]
fn platform_batch_process_info(pids: &[u32]) -> HashMap<u32, RawProcessInfo> {
    linux::batch_process_info(pids)
}

#[cfg(target_os = "linux")]
fn platform_batch_cwd(pids: &[u32]) -> HashMap<u32, PathBuf> {
    linux::batch_cwd(pids)
}

#[cfg(target_os = "linux")]
fn platform_get_all_processes_raw_checked() -> Result<Vec<RawProcessEntry>, PlatformError> {
    linux::get_all_processes_raw_checked()
}

#[cfg(target_os = "windows")]
fn platform_get_listening_ports_raw_checked() -> Result<Vec<RawListenerEntry>, PlatformError> {
    windows::get_listening_ports_raw_checked()
}

#[cfg(target_os = "windows")]
fn platform_get_listener_on_port_raw_checked(
    port: u16,
) -> Result<Option<RawListenerEntry>, PlatformError> {
    windows::get_listener_on_port_raw_checked(port)
}

#[cfg(target_os = "windows")]
fn platform_batch_process_info(pids: &[u32]) -> HashMap<u32, RawProcessInfo> {
    windows::batch_process_info(pids)
}

#[cfg(target_os = "windows")]
fn platform_batch_cwd(pids: &[u32]) -> HashMap<u32, PathBuf> {
    windows::batch_cwd(pids)
}

#[cfg(target_os = "windows")]
fn platform_get_all_processes_raw_checked() -> Result<Vec<RawProcessEntry>, PlatformError> {
    windows::get_all_processes_raw_checked()
}

#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
fn platform_get_listening_ports_raw_checked() -> Result<Vec<RawListenerEntry>, PlatformError> {
    Ok(Vec::new())
}

#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
fn platform_get_listener_on_port_raw_checked(
    _port: u16,
) -> Result<Option<RawListenerEntry>, PlatformError> {
    Ok(None)
}

#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
fn platform_batch_process_info(_pids: &[u32]) -> HashMap<u32, RawProcessInfo> {
    HashMap::new()
}

#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
fn platform_batch_cwd(_pids: &[u32]) -> HashMap<u32, PathBuf> {
    HashMap::new()
}

#[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
fn platform_get_all_processes_raw_checked() -> Result<Vec<RawProcessEntry>, PlatformError> {
    Ok(Vec::new())
}
