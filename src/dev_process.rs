pub fn is_developer_process(process_name: &str, command: &str) -> bool {
    let name = process_name.to_ascii_lowercase();
    let command = command.to_ascii_lowercase();

    if SYSTEM_PROCESS_PREFIXES
        .iter()
        .any(|prefix| name.starts_with(prefix))
    {
        return false;
    }

    is_python_process_name(&name)
        || DEV_PROCESS_NAMES.contains(&name.as_str())
        || name.starts_with("com.docke")
        || name == "docker-sandbox"
        || command_has_developer_indicator(&command)
}

pub(crate) fn is_python_process_name(process_name: &str) -> bool {
    let name = process_name.to_ascii_lowercase();
    let name = name.strip_suffix(".exe").unwrap_or(&name);

    if name == "python" {
        return true;
    }

    let Some(version) = name.strip_prefix("python") else {
        return false;
    };
    let (version, free_threaded) = match version.strip_suffix('t') {
        Some(version) => (version, true),
        None => (version, false),
    };
    let mut components = version.split('.');
    let Some(major) = components.next() else {
        return false;
    };

    if major.is_empty() || !major.bytes().all(|byte| byte.is_ascii_digit()) {
        return false;
    }

    match (components.next(), components.next()) {
        (None, None) => !free_threaded,
        (Some(minor), None) => !minor.is_empty() && minor.bytes().all(|byte| byte.is_ascii_digit()),
        _ => false,
    }
}

fn command_has_developer_indicator(command: &str) -> bool {
    if command.is_empty() {
        return false;
    }

    if command.contains("manage.py") || command.contains("ng serve") {
        return true;
    }

    COMMAND_INDICATORS
        .iter()
        .any(|indicator| contains_word(command, indicator))
}

fn contains_word(value: &str, word: &str) -> bool {
    value
        .split(|character: char| !character.is_ascii_alphanumeric() && character != '.')
        .any(|part| part == word)
}

const SYSTEM_PROCESS_PREFIXES: &[&str] = &[
    "spotify",
    "raycast",
    "tableplus",
    "postman",
    "linear",
    "cursor",
    "controlce",
    "rapportd",
    "slack",
    "discord",
    "firefox",
    "chrome",
    "google",
    "safari",
    "figma",
    "notion",
    "zoom",
    "teams",
    "code",
    "iterm2",
    "warp",
    "arc",
    "loginwindow",
    "windowserver",
    "systemuise",
    "kernel_task",
    "launchd",
    "mdworker",
    "mds_stores",
    "cfprefsd",
    "coreaudio",
    "airportd",
    "bluetoothd",
    "sharingd",
    "systemd",
    "snapd",
    "networkmanager",
    "gdm",
    "sshd",
    "cron",
    "dbus-daemon",
    "svchost",
    "csrss",
    "lsass",
    "services",
    "explorer",
];

const DEV_PROCESS_NAMES: &[&str] = &[
    "node",
    "ruby",
    "java",
    "go",
    "cargo",
    "deno",
    "bun",
    "php",
    "uvicorn",
    "gunicorn",
    "flask",
    "rails",
    "npm",
    "npx",
    "yarn",
    "pnpm",
    "tsc",
    "tsx",
    "esbuild",
    "rollup",
    "turbo",
    "nx",
    "jest",
    "vitest",
    "mocha",
    "pytest",
    "cypress",
    "playwright",
    "rustc",
    "dotnet",
    "gradle",
    "mvn",
    "mix",
    "elixir",
    "docker",
];

const COMMAND_INDICATORS: &[&str] = &[
    "node", "next", "vite", "nuxt", "webpack", "remix", "astro", "gulp", "gatsby", "flask",
    "django", "uvicorn", "rails", "cargo",
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identifies_common_developer_processes_by_name() {
        assert!(is_developer_process("node", ""));
        assert!(is_developer_process("python3", ""));
        assert!(is_developer_process("python3.13", ""));
        assert!(is_developer_process("java", ""));
        assert!(is_developer_process("docker", ""));
        assert!(is_developer_process("com.docker.backend", ""));
    }

    #[test]
    fn identifies_supported_python_process_names() {
        for process_name in [
            "python",
            "PYTHON",
            "python2",
            "python3",
            "python2.7",
            "python3.13",
            "python3.13t",
            "python.exe",
            "Python3.EXE",
            "PYTHON3.13.EXE",
            "python3.13T.exe",
        ] {
            assert!(
                is_python_process_name(process_name),
                "expected {process_name:?} to be recognized"
            );
        }
    }

    #[test]
    fn rejects_python_process_name_near_misses() {
        for process_name in [
            "",
            "pythonista",
            "python-server",
            "python.",
            "python3.",
            "python.13",
            "python3t",
            "python3.13m",
            "python3.13.1",
            "python3.13.exe.bak",
            "/usr/bin/python3.13",
        ] {
            assert!(
                !is_python_process_name(process_name),
                "expected {process_name:?} to be rejected"
            );
        }
    }

    #[test]
    fn excludes_common_desktop_and_system_processes() {
        assert!(!is_developer_process("Chrome", ""));
        assert!(!is_developer_process("Slack", ""));
        assert!(!is_developer_process("systemd", ""));
    }

    #[test]
    fn identifies_developer_processes_from_command_indicators() {
        assert!(is_developer_process(
            "bash",
            "/bin/bash -lc npm run vite -- --host 0.0.0.0"
        ));
        assert!(is_developer_process(
            "python",
            "python manage.py runserver 0.0.0.0:8000"
        ));
    }
}
