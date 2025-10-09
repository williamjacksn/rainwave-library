import pathlib
import json

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


def gen_workflow_deploy():
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


def main():
    gen_workflow_deploy()


if __name__ == "__main__":
    main()
