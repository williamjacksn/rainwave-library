import json
import pathlib

ACTIONS_CHECKOUT = {"name": "Check out repository", "uses": "actions/checkout@v5"}
DEFAULT_BRANCH = "main"
THIS_FILE = pathlib.PurePosixPath(
    pathlib.Path(__file__).relative_to(pathlib.Path.cwd())
)


def gen(content: dict, target: str) -> None:
    pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(target).write_text(
        json.dumps(content, indent=2, sort_keys=True), newline="\n"
    )


def gen_dependabot() -> None:
    target = ".github/dependabot.yaml"
    content = {
        "version": 2,
        "updates": [
            {
                "package-ecosystem": e,
                "allow": [{"dependency-type": "all"}],
                "directory": "/",
                "schedule": {"interval": "weekly"},
            }
            for e in ["github-actions", "npm", "uv"]
        ],
    }
    gen(content, target)


def gen_package_json() -> None:
    target = "package.json"
    content = {
        "description": f"This file ({target}) was generated from {THIS_FILE}",
        "name": "rainwave-library",
        "version": "1.0.0",
        "license": "UNLICENSED",
        "private": True,
        "dependencies": {
            "bootstrap": "5.3.8",
            "bootstrap-icons": "1.13.1",
            "htmx.org": "2.0.8",
        },
    }
    gen(content, target)


def gen_workflow_deploy() -> None:
    target = ".github/workflows/deploy.yaml"
    content = {
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}"
        },
        "name": "Deploy",
        "on": {"push": {"branches": [DEFAULT_BRANCH]}},
        "jobs": {
            "deploy": {
                "name": "Deploy",
                "runs-on": "ubuntu-latest",
                "steps": [
                    ACTIONS_CHECKOUT,
                    {
                        "name": "Deploy",
                        "run": "sh ci/ssh-deploy.sh",
                        "env": {
                            "SSH_HOST": "${{ secrets.ssh_host }}",
                            "SSH_PRIVATE_KEY": "${{ secrets.ssh_private_key }}",
                            "SSH_USER": "${{ secrets.ssh_user }}",
                        },
                    },
                ],
            }
        },
    }
    gen(content, target)


def gen_workflow_ruff() -> None:
    target = ".github/workflows/ruff.yaml"
    content = {
        "name": "Ruff",
        "on": {
            "pull_request": {"branches": [DEFAULT_BRANCH]},
            "push": {"branches": [DEFAULT_BRANCH]},
        },
        "permissions": {"contents": "read"},
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}"
        },
        "jobs": {
            "ruff-check": {
                "name": "Run ruff check",
                "runs-on": "ubuntu-latest",
                "steps": [
                    ACTIONS_CHECKOUT,
                    {"name": "Run ruff check", "run": "sh ci/ruff-check.sh"},
                ],
            },
            "ruff-format": {
                "name": "Run ruff format",
                "runs-on": "ubuntu-latest",
                "steps": [
                    ACTIONS_CHECKOUT,
                    {"name": "Run ruff format", "run": "sh ci/ruff-format.sh"},
                ],
            },
        },
    }
    gen(content, target)


def main() -> None:
    gen_dependabot()
    gen_package_json()
    gen_workflow_deploy()
    gen_workflow_ruff()


if __name__ == "__main__":
    main()
