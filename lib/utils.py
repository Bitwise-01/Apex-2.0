import secrets
import subprocess
import lib.settings as settings


def gen_admin_url_prefix() -> str:
    token = secrets.token_hex()[:32]
    return f"{token[:8]}-{token[8:24]}-{token[24:]}"


def create_js_config_file(admin_url_prefix: str) -> None:
    config = {"admin_url_prefix": admin_url_prefix}
    config_path = "static/admin/js/config.js"

    with open(config_path, "wt") as f:
        t = f"const config={config};"
        f.write(t)


def kill_all() -> None:
    procs = []
    for p in settings.ENTER_EXIT_PROC["proc"]:
        procs.append(
            subprocess.Popen(
                f"pkill {p}".split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
        )

    while procs:
        for p in procs:
            if p.poll() != None:
                procs.remove(p)


def manage_service(stop=False):
    state = "stop" if stop else "restart"
    for service in settings.ENTER_EXIT_PROC["services"]:
        subprocess.Popen(
            f"service {service} {state}",
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        ).wait()


def stop_services() -> None:
    manage_service(stop=True)

    subprocess.Popen(
        f"airmon-ng check kill",
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    ).wait()


def restart_services() -> None:
    manage_service(stop=False)
