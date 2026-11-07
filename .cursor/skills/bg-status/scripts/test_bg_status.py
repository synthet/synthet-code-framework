import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bg_status as B  # noqa: E402


def test_exit_marker_and_activity_rules():
    assert B.task_status("measure done\n\n[exited with code 0]\n", 9999) == "exited 0"
    assert B.task_status("boom\n[exited with code -1]", 5) == "exited -1"
    assert B.task_status("pairs 300/855", 60) == "active"
    assert B.task_status("", B.ACTIVE_S + 1) == "quiet"
    assert B.task_status("waiting\n[killed]\n", 99) == "killed"
    assert B.clean_last_line("pairs 3\n[killed]") == "pairs 3"


def test_last_line_strips_ansi_carriage_returns_and_the_exit_marker():
    text = "epoch 1\r\x1b[K  12/100 2.42G 0.92\r\x1b[K  13/100 2.40G 0.90\n[exited with code 0]\n"
    assert B.clean_last_line(text) == "13/100 2.40G 0.90"
    assert B.clean_last_line("") == ""


def test_redaction_hides_flag_and_environment_values():
    out = B.redact("tool --token abc123 --api-key=XYZ run API_TOKEN=s3cr3t MY_SECRET_KEY=q --name keep")
    assert "abc123" not in out and "XYZ" not in out and "s3cr3t" not in out and "=q" not in out
    assert "--name keep" in out


def test_process_buckets():
    assert B.bucket(r"python D:\x\run_jev_mcp.py") == "infrastructure"
    assert B.bucket("llmwiki.exe --root D:/w mcp") == "infrastructure"
    assert B.bucket("python -u -m scripts.neardupe_study.experiments.e8body measure") == "worker"
    assert B.bucket(r'cmd.exe /c "D:\runs\train_bird15.cmd"') == "worker"
    assert B.bucket("python training/train_pose.py --data x") == "worker"
    assert B.bucket("node something.js") == "other"


def test_project_slug_matches_claude_code_folders():
    assert B.project_slug(r"C:\Code\my-app") == "C--Code-my-app"


def test_false_done_needs_a_running_worker_that_names_the_status_file():
    files = [{"path": r"D:\w\e8-worker-20261101-status.txt", "last": "measure done"},
             {"path": r"D:\w\other-run-status.txt", "last": "measure done"},
             {"path": r"D:\w\e9-worker-status.txt", "last": "still measuring"}]
    workers = [{"cmd": r"python -m x measure --out D:\w\e8-worker-20261101\measure"},
               {"cmd": r"python -m x --out D:\w\e9-worker"}]
    assert B.false_done(files, workers) == [r"D:\w\e8-worker-20261101-status.txt"]
    assert B.status_key("status.txt") == ""


def test_age_formatting():
    assert B.age(30) == "30s"
    assert B.age(600) == "10m"
    assert B.age(7200) == "2.0h"
    assert B.age(200000) == "2.3d"


def test_slug_replaces_every_non_alphanumeric_like_claude_code():
    assert B.project_slug(r"C:\Code\my-app\scripts\neardupe_study") == \
        "C--Code-my-app-scripts-neardupe-study"
    assert B.project_slug(r"C:\Code\x\.agent\scratch\wt-a") == "C--Code-x--agent-scratch-wt-a"


def test_task_slugs_follow_the_resolved_path_and_aliases(tmp_path):
    slugs = B.task_slugs(str(tmp_path), ["D--Projects-Other"])
    assert B.project_slug(tmp_path.resolve()).lower() in slugs
    assert "d--projects-other" in slugs


def test_default_ref_prefers_origin_head_then_main_then_master():
    def fake(answers):
        def run(args, timeout=8):
            if "symbolic-ref" in args:
                return answers.get("head")
            return "abc123\n" if args[-1] in answers.get("refs", ()) else None
        return run
    assert B.default_ref("r", fake({"head": "origin/master\n"})) == "origin/master"
    assert B.default_ref("r", fake({"refs": ("origin/main", "origin/master")})) == "origin/main"
    assert B.default_ref("r", fake({"refs": ("origin/master",)})) == "origin/master"
    assert B.default_ref("r", fake({})) is None


def test_unique_repos_drops_a_second_path_to_the_same_checkout(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert B.unique_repos([a, b, tmp_path / "a" / ".." / "a"]) == [a, b]


def test_docker_exec_jobs_are_workers_and_other_docker_calls_are_not():
    job = "docker exec -i image-scoring-gpu-shell python -m scripts.backfill_af --limit 50"
    assert B.DOCKER_JOB.search(job) and B.bucket(job) == "worker"
    assert B.bucket('"C:\\Program Files\\Docker\\docker.exe" run --rm img bash /work/run.sh') == "worker"
    probe = "docker exec image-scoring-postgres psql -Atc select 1"
    assert B.DOCKER_JOB.search(probe) and B.bucket(probe) == "other"
    assert not B.DOCKER_JOB.search("docker ps --format x") and not B.DOCKER_JOB.search("docker compose logs")
