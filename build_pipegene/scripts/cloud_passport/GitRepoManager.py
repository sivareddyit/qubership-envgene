from pathlib import Path

from git import Repo, GitCommandError


class GitRepoManager:
    def __init__(self, repo_path, git_user_email, git_user_name, git_token, server_host, project_path, branch):
        self.repo_path = Path(repo_path)
        self.git_user_email = git_user_email
        self.git_user_name = git_user_name
        self.git_token = git_token
        self.server_host = server_host
        self.project_path = project_path
        self.branch = branch
        self.repo = Repo(self.repo_path)

    def prepare_repo(self):
        with self.repo.config_writer() as cw:
            cw.set_value("user", "email", self.git_user_email)
            cw.set_value("user", "name", self.git_user_name)
            cw.set_value("pull", "rebase", "true")
            cw.release()

        rebase_dir = self.repo_path / ".git/rebase-merge"
        if rebase_dir.exists():
            import shutil
            shutil.rmtree(rebase_dir)

        push_url = f"https://project_32647_bot:{self.git_token}@{self.server_host}/{self.project_path}.git"
        origin = self.repo.remote(name='origin')
        origin.set_url(push_url, push=True)

        self.repo.git.reset('--hard')

        try:
            origin.pull(self.branch)
        except GitCommandError as e:
            raise RuntimeError()



